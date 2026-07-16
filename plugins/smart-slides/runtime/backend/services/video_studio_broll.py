import os
import re
import math
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import httpx

from backend.services import storage


class BrollAssetError(RuntimeError):
    pass


MAX_BROLL_DOWNLOAD_BYTES = 300 * 1024 * 1024
ALLOWED_PROVIDER_HOSTS = {
    "pexels": ("pexels.com",),
    "pixabay": ("pixabay.com",),
}


_NEGATIVE_TERMS = {
    "underwater",
    "fish",
    "coral",
    "reef",
    "aquarium",
    "cartoon",
    "animation",
    "illustration",
}


def _compact_query(value: Any, *, max_length: int = 72, max_terms: int = 9) -> str:
    query = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n,，;；、")
    query = re.split(r"[。！？!?；;\n]", query, maxsplit=1)[0].strip(" \t\r\n,，;；、")
    if len(query) <= max_length:
        compacted = query
    else:
        compacted = query[:max_length].rsplit(" ", 1)[0].strip(" \t\r\n,，;；、") or query[:max_length].strip()
    tokens = compacted.split()
    if len(tokens) > max_terms:
        compacted = " ".join(tokens[:max_terms])
    return compacted


def broll_asset_key(candidate: Dict[str, Any]) -> tuple[str, str]:
    """Return a stable project-wide identity for a B-roll source."""
    provider = str(candidate.get("provider") or "local").strip().lower()
    identity = str(
        candidate.get("provider_id")
        or candidate.get("source_url")
        or candidate.get("download_url")
        or candidate.get("asset_path")
        or candidate.get("asset_url")
        or candidate.get("id")
        or ""
    ).strip()
    return provider, identity


def candidate_covers_duration(candidate: Dict[str, Any], target_duration_seconds: float) -> bool:
    """Require a source clip that can cover its shot without video looping."""
    try:
        available = float(candidate.get("duration_seconds") or 0)
    except (TypeError, ValueError):
        return False
    return available + 0.25 >= max(0.1, float(target_duration_seconds or 0))


def _append_query(queries: List[str], seen: set[str], value: Any) -> None:
    for part in re.split(r"(?:[、，]+|以及|和)", str(value or "")):
        query = _compact_query(part)
        if not query:
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)


def _split_prompt_queries(prompt: str) -> List[str]:
    parts = re.split(r"[;；\n]+", prompt)
    split_parts: List[str] = []
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        split_parts.append(stripped)
        if "、" in stripped:
            split_parts.extend(piece.strip() for piece in stripped.split("、") if piece.strip())
    return split_parts


def _semantic_fallback_queries(shot: Dict[str, Any]) -> List[str]:
    asset_plan = shot.get("asset_search_plan") if isinstance(shot.get("asset_search_plan"), dict) else {}
    search_queries = asset_plan.get("search_queries") if isinstance(asset_plan.get("search_queries"), list) else []
    named_entities = asset_plan.get("named_entities") if isinstance(asset_plan.get("named_entities"), list) else []
    material_types = asset_plan.get("material_types") if isinstance(asset_plan.get("material_types"), list) else []
    text = " ".join(
        str(value or "")
        for value in [
            shot.get("title"),
            shot.get("broll_prompt"),
            asset_plan.get("summary"),
            " ".join(str(item or "") for item in search_queries),
            " ".join(str(item or "") for item in named_entities),
            " ".join(str(item or "") for item in material_types),
        ]
    ).lower()
    fallbacks: List[str] = []
    if any(term in text for term in ("spacex", "starlink", "falcon", "rocket", "mars", "satellite", "火箭", "星链", "火星", "航天")):
        fallbacks.extend([
            "rocket launch space",
            "satellite orbit earth",
            "space technology control room",
            "night sky satellite dish",
        ])
    if any(term in text for term in ("ipo", "stock", "market", "valuation", "cash", "financial", "invest", "venture", "capital", "估值", "股市", "金融", "风投", "资金")):
        fallbacks.extend([
            "stock market trading screen",
            "financial chart office",
            "business investors meeting",
            "corporate finance meeting",
        ])
    if any(term in text for term in ("chart", "data", "infographic", "metric", "数据", "图表", "增长")):
        fallbacks.extend([
            "data analytics dashboard",
            "financial data screen",
            "business report laptop",
        ])
    if any(term in text for term in ("logo", "fidelity", "sequoia", "baillie", "机构", "logo")):
        fallbacks.extend([
            "venture capital office meeting",
            "business handshake office",
            "investment documents table",
        ])
    if not fallbacks:
        fallbacks.extend([
            "documentary business office",
            "technology business meeting",
            "city night business district",
        ])
    return fallbacks


def _candidate_queries(shot: Dict[str, Any]) -> List[str]:
    queries: List[str] = []
    seen: set[str] = set()
    prompt = str(shot.get("broll_prompt") or "").strip()

    asset_plan = shot.get("asset_search_plan") if isinstance(shot.get("asset_search_plan"), dict) else {}
    search_queries = asset_plan.get("search_queries") if isinstance(asset_plan.get("search_queries"), list) else []
    for query in search_queries:
        _append_query(queries, seen, query)
    for query in _split_prompt_queries(prompt):
        _append_query(queries, seen, query)
    _append_query(queries, seen, prompt)
    _append_query(queries, seen, asset_plan.get("summary"))
    for query in _semantic_fallback_queries(shot):
        _append_query(queries, seen, query)
    return queries


def _api_key(name: str) -> str:
    return os.getenv(name, "").strip() or _env_file_value(name)


def _env_file_value(name: str) -> str:
    candidates: List[Path] = [Path.home() / ".codex" / "smart-slides" / ".env"]
    backend_dir = Path(__file__).resolve().parents[1]
    project_root = backend_dir.parent
    candidates.extend([project_root / ".env", backend_dir / ".env"])

    seen: set[Path] = set()
    prefix = f"{name}="
    export_prefix = f"export {name}="
    for path in candidates:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="latin-1").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(export_prefix):
                value = line[len(export_prefix):].strip()
            elif line.startswith(prefix):
                value = line[len(prefix):].strip()
            else:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value.strip()
    return ""


def _target_orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _variant_score(item: Dict[str, Any], *, target_orientation: str, target_height: int) -> tuple[int, int, int]:
    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    orientation = _target_orientation(width, height)
    orientation_penalty = 0 if orientation == target_orientation or target_orientation == "square" else 1
    height_penalty = abs(max(1, height) - target_height)
    return (orientation_penalty, height_penalty, width * height)


def _best_pexels_file(files: List[Dict[str, Any]], *, target_orientation: str, target_height: int) -> Dict[str, Any]:
    candidates = [
        item
        for item in files
        if isinstance(item, dict)
        and item.get("link")
        and str(item.get("file_type") or "video/mp4").lower().endswith("mp4")
    ]
    if not candidates:
        candidates = [item for item in files if isinstance(item, dict) and item.get("link")]
    if not candidates:
        return {}
    candidates.sort(key=lambda item: _variant_score(item, target_orientation=target_orientation, target_height=target_height))
    return candidates[0]


def _best_pixabay_video(videos: Dict[str, Any], *, target_orientation: str, target_height: int) -> Dict[str, Any]:
    candidates = []
    for key in ("tiny", "small", "medium", "large"):
        item = videos.get(key)
        if isinstance(item, dict) and item.get("url"):
            copied = dict(item)
            copied["quality_key"] = key
            candidates.append(copied)
    if not candidates:
        return {}
    candidates.sort(key=lambda item: _variant_score(item, target_orientation=target_orientation, target_height=target_height))
    return candidates[0]


def _looks_relevant(candidate: Dict[str, Any], query: str) -> bool:
    text = " ".join(
        str(value or "")
        for value in (
            query,
            candidate.get("provider"),
            candidate.get("provider_id"),
            candidate.get("title"),
            candidate.get("description"),
            candidate.get("author"),
            candidate.get("source_url"),
            candidate.get("download_url"),
        )
    ).lower()
    if any(term in text for term in _NEGATIVE_TERMS):
        allowed = {"japan", "japanese", "tokyo", "osaka", "kyoto", "business", "office"}
        return bool(allowed & set(re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", text)))
    return True


def _search_pexels(query: str, per_page: int, orientation: str) -> List[Dict[str, Any]]:
    key = _api_key("PEXELS_API_KEY")
    if not key:
        return []
    params: Dict[str, Any] = {"query": query, "per_page": per_page}
    if orientation:
        params["orientation"] = orientation
    with httpx.Client(timeout=25) as client:
        response = client.get(
            "https://api.pexels.com/v1/videos/search",
            params=params,
            headers={"Authorization": key},
        )
        response.raise_for_status()
        body = response.json()
    videos = body.get("videos")
    return videos if isinstance(videos, list) else []


def _search_pixabay(query: str, per_page: int) -> List[Dict[str, Any]]:
    key = _api_key("PIXABAY_API_KEY")
    if not key:
        return []
    with httpx.Client(timeout=25) as client:
        response = client.get(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": query, "per_page": per_page, "safesearch": "true"},
        )
        response.raise_for_status()
        body = response.json()
    hits = body.get("hits")
    return hits if isinstance(hits, list) else []


def _normalize_pexels(shot_id: str, query: str, item: Dict[str, Any], *, target_orientation: str, target_height: int) -> Dict[str, Any] | None:
    files = item.get("video_files") if isinstance(item.get("video_files"), list) else []
    best = _best_pexels_file(files, target_orientation=target_orientation, target_height=target_height)
    if not best:
        return None
    width = int(best.get("width") or item.get("width") or 0)
    height = int(best.get("height") or item.get("height") or 0)
    orientation = _target_orientation(width, height)
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    provider_id = str(item.get("id") or "")
    return {
        "id": f"{shot_id}-pexels-{provider_id}",
        "provider": "pexels",
        "provider_id": provider_id,
        "title": f"Pexels · {str(user.get('name') or provider_id)}",
        "description": f"{query}；Pexels 免费视频素材",
        "duration_seconds": int(item.get("duration") or 0),
        "visual_style": "真实免费素材",
        "color": "from-cyan-500/50 via-slate-700 to-slate-950",
        "download_url": str(best.get("link") or ""),
        "thumbnail_url": str(item.get("image") or ""),
        "source_url": str(item.get("url") or ""),
        "license": "Pexels License",
        "search_query": query,
        "author": str(user.get("name") or ""),
        "width": width,
        "height": height,
        "aspect_ratio": "16:9" if orientation == "landscape" else "",
        "orientation": orientation,
        "preview_ready": orientation == "landscape",
        "render_ready": orientation == "landscape" and height >= 720,
        "needs_transcode": False,
        "needs_crop": orientation != "landscape",
        "readiness_warnings": [] if orientation == "landscape" else ["素材不是横屏，不能进入当前 16:9 渲染链路"],
    }


def _normalize_pixabay(shot_id: str, query: str, item: Dict[str, Any], *, target_orientation: str, target_height: int) -> Dict[str, Any] | None:
    videos = item.get("videos") if isinstance(item.get("videos"), dict) else {}
    best = _best_pixabay_video(videos, target_orientation=target_orientation, target_height=target_height)
    if not best:
        return None
    width = int(best.get("width") or 0)
    height = int(best.get("height") or 0)
    orientation = _target_orientation(width, height)
    provider_id = str(item.get("id") or "")
    return {
        "id": f"{shot_id}-pixabay-{provider_id}",
        "provider": "pixabay",
        "provider_id": provider_id,
        "title": f"Pixabay · {str(item.get('user') or provider_id)}",
        "description": f"{query}；Pixabay 免费视频素材",
        "duration_seconds": int(item.get("duration") or 0),
        "visual_style": "真实免费素材",
        "color": "from-emerald-500/45 via-teal-900 to-slate-950",
        "download_url": str(best.get("url") or ""),
        "thumbnail_url": str(item.get("picture_id") or ""),
        "source_url": str(item.get("pageURL") or ""),
        "license": "Pixabay Content License",
        "search_query": query,
        "author": str(item.get("user") or ""),
        "width": width,
        "height": height,
        "aspect_ratio": "16:9" if orientation == "landscape" else "",
        "orientation": orientation,
        "preview_ready": orientation == "landscape",
        "render_ready": orientation == "landscape" and height >= 720,
        "needs_transcode": False,
        "needs_crop": orientation != "landscape",
        "readiness_warnings": [] if orientation == "landscape" else ["素材不是横屏，不能进入当前 16:9 渲染链路"],
    }


def _candidate_extension(url: str, content_type: str) -> str:
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 6:
        return ext
    if "image/" in content_type:
        subtype = content_type.split("/", 1)[1].split(";", 1)[0]
        return f".{subtype or 'jpg'}"
    return ".mp4"


def _download_candidate(candidate: Dict[str, Any], *, project_id: str, shot_id: str) -> Dict[str, Any]:
    download_url = str(candidate.get("download_url") or "")
    if not download_url:
        raise BrollAssetError("素材候选缺少下载地址")
    provider = str(candidate.get("provider") or "").lower()
    with httpx.Client(timeout=25, follow_redirects=False) as client:
        response = _download_with_validated_redirects(client, provider, download_url)
    content_length = int(response.headers.get("content-length") or len(response.content))
    if content_length > MAX_BROLL_DOWNLOAD_BYTES or len(response.content) > MAX_BROLL_DOWNLOAD_BYTES:
        raise BrollAssetError("B-roll 素材超过本地下载大小限制")
    content_type = response.headers.get("content-type") or "video/mp4"
    ext = _candidate_extension(download_url, content_type)
    safe_provider = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(candidate.get("provider") or "provider"))
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(candidate.get("provider_id") or candidate.get("id") or "asset"))
    stored = storage.save_bytes(
        f"video_studio_assets/{project_id}/{shot_id}/{safe_provider}_{safe_id}{ext}",
        response.content,
        content_type,
    )
    duration = int(candidate.get("duration_seconds") or 0)
    return {
        **candidate,
        "duration_seconds": max(1, duration),
        "asset_url": stored.url,
        "asset_path": stored.path,
        "similar_materials": [],
    }


def _download_with_validated_redirects(client: httpx.Client, provider: str, download_url: str) -> httpx.Response:
    current_url = download_url
    for _ in range(6):
        _validate_provider_url(provider, current_url)
        response = client.get(current_url, follow_redirects=False)
        if response.status_code not in {301, 302, 303, 307, 308}:
            response.raise_for_status()
            return response
        location = response.headers.get("location")
        if not location:
            raise BrollAssetError("B-roll 重定向缺少目标地址")
        current_url = urljoin(current_url, location)
        _validate_provider_url(provider, current_url)
    raise BrollAssetError("B-roll 下载重定向次数过多")


def _validate_provider_url(provider: str, value: str) -> None:
    allowed = ALLOWED_PROVIDER_HOSTS.get(provider)
    parsed = urlparse(value)
    hostname = str(parsed.hostname or "").lower()
    if not allowed or parsed.scheme != "https" or not any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed):
        raise BrollAssetError("B-roll 下载地址不属于已允许的 Pexels/Pixabay 域名")


def search_broll_candidates(
    shot: Dict[str, Any],
    *,
    query: str = "",
    per_page: int = 8,
    providers: List[str] | None = None,
    excluded_asset_keys: set[tuple[str, str]] | None = None,
    minimum_duration_seconds: float = 0,
) -> List[Dict[str, Any]]:
    if not _api_key("PEXELS_API_KEY") and not _api_key("PIXABAY_API_KEY"):
        raise BrollAssetError("未配置免费素材 API Key：请配置 PEXELS_API_KEY 或 PIXABAY_API_KEY")

    shot_id = str(shot.get("id") or "")
    base_query = _compact_query(query) or str(shot.get("broll_prompt") or "").strip()
    if not shot_id:
        raise BrollAssetError("分镜缺少 shot id")
    if not base_query:
        raise BrollAssetError("分镜缺少 B-roll 检索描述")

    target_orientation = "landscape"
    target_height = 720
    candidates: List[Dict[str, Any]] = []
    errors: List[str] = []
    enabled_providers = {str(provider).lower() for provider in (providers or ["pexels", "pixabay"])}
    can_use_pexels = "pexels" in enabled_providers and bool(_api_key("PEXELS_API_KEY"))
    can_use_pixabay = "pixabay" in enabled_providers and bool(_api_key("PIXABAY_API_KEY"))
    provider_count = int(can_use_pexels) + int(can_use_pixabay)
    if provider_count <= 0:
        raise BrollAssetError("当前选择的素材供应商未配置 API Key")
    provider_quota = max(1, per_page if provider_count <= 1 else math.ceil(per_page / provider_count))
    candidate_queries = [base_query] if query else _candidate_queries({**shot, "broll_prompt": base_query})
    for candidate_query in candidate_queries:
        if len(candidates) >= per_page * 4:
            break
        if can_use_pexels:
            try:
                for item in _search_pexels(candidate_query, provider_quota, target_orientation):
                    normalized = _normalize_pexels(
                        shot_id,
                        candidate_query,
                        item,
                        target_orientation=target_orientation,
                        target_height=target_height,
                    )
                    if normalized and _looks_relevant(normalized, candidate_query):
                        candidates.append(normalized)
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(f"Pexels 检索失败({candidate_query})：{str(exc).splitlines()[0]}")
        if can_use_pixabay:
            try:
                for item in _search_pixabay(candidate_query, provider_quota):
                    normalized = _normalize_pixabay(
                        shot_id,
                        candidate_query,
                        item,
                        target_orientation=target_orientation,
                        target_height=target_height,
                    )
                    if normalized and _looks_relevant(normalized, candidate_query):
                        candidates.append(normalized)
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(f"Pixabay 检索失败({candidate_query})：{str(exc).splitlines()[0]}")

    excluded = excluded_asset_keys or set()
    deduped = []
    seen = set()
    for candidate in candidates:
        key = broll_asset_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        if key in excluded:
            continue
        if minimum_duration_seconds and not candidate_covers_duration(candidate, minimum_duration_seconds):
            continue
        deduped.append(candidate)
        if len(deduped) >= per_page:
            break

    if not deduped:
        suffix = f"；{'；'.join(errors)}" if errors else ""
        if minimum_duration_seconds or excluded:
            raise BrollAssetError(
                f"没有检索到不重复且可覆盖 {minimum_duration_seconds:.1f} 秒镜头的免费 B-roll 素材：{base_query}{suffix}"
            )
        raise BrollAssetError(f"没有检索到可下载的免费 B-roll 素材：{base_query}{suffix}")

    return deduped


def download_broll_candidate(candidate: Dict[str, Any], *, project_id: str, shot_id: str) -> Dict[str, Any]:
    if str(candidate.get("provider") or "") == "local_library" and (candidate.get("asset_url") or candidate.get("asset_path")):
        local_path = storage.ensure_local_file(str(candidate.get("asset_path") or candidate.get("asset_url") or ""))
        data_root = os.path.realpath(storage.DATA_DIR)
        resolved_path = os.path.realpath(local_path)
        if not os.path.isfile(resolved_path) or not (resolved_path == data_root or resolved_path.startswith(data_root + os.sep)):
            raise BrollAssetError("本地素材必须位于 Smart Slides 数据目录")
        return {
            **candidate,
            "asset_path": resolved_path,
            "id": str(candidate.get("id") or f"{shot_id}-local-{candidate.get('provider_id') or 'asset'}"),
            "description": str(candidate.get("description") or "本地素材库复用素材"),
            "visual_style": str(candidate.get("visual_style") or "本地素材库匹配"),
            "color": str(candidate.get("color") or "from-emerald-500/45 via-teal-900 to-slate-950"),
            "similar_materials": candidate.get("similar_materials") if isinstance(candidate.get("similar_materials"), list) else [],
        }
    return _download_candidate(candidate, project_id=project_id, shot_id=shot_id)


def realize_broll_options(
    shot: Dict[str, Any],
    *,
    project_id: str,
    per_page: int = 8,
    excluded_asset_keys: set[tuple[str, str]] | None = None,
) -> List[Dict[str, Any]]:
    target_duration = max(0.1, float(shot.get("duration_seconds") or 0))
    candidates = search_broll_candidates(
        shot,
        per_page=per_page,
        excluded_asset_keys=excluded_asset_keys,
        minimum_duration_seconds=target_duration,
    )

    realized = []
    errors: List[str] = []
    shot_id = str(shot.get("id") or "")
    excluded = excluded_asset_keys or set()
    for candidate in candidates:
        if broll_asset_key(candidate) in excluded:
            continue
        if not candidate_covers_duration(candidate, target_duration):
            continue
        try:
            realized.append(_download_candidate(candidate, project_id=project_id, shot_id=shot_id))
            break
        except (httpx.HTTPError, BrollAssetError) as exc:
            errors.append(f"{candidate.get('provider')} 下载失败：{str(exc).splitlines()[0]}")
    if not realized:
        raise BrollAssetError(f"免费 B-roll 素材检索到了候选，但下载失败：{'；'.join(errors)}")
    realized_ids = {str(item.get("id") or "") for item in realized}
    remaining_candidates = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and str(candidate.get("id") or "") not in realized_ids
    ]
    return [*realized, *remaining_candidates]
