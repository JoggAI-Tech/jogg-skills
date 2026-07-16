import json
import os
from typing import Any, Dict, List

from backend.services import storage


class BgmAssetError(RuntimeError):
    pass


ASSET_DIR = os.path.expanduser(
    os.getenv("SMART_SLIDES_BGM_ASSET_DIR", "")
    or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "assets", "video_studio_bgm")
)
MANIFEST_PATH = os.path.join(ASSET_DIR, "manifest.json")


def _load_manifest() -> List[Dict[str, Any]]:
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except OSError as exc:
        raise BgmAssetError("BGM manifest not found") from exc
    tracks = payload.get("tracks") if isinstance(payload, dict) else None
    if not isinstance(tracks, list) or not tracks:
        raise BgmAssetError("BGM manifest is empty")
    return [track for track in tracks if isinstance(track, dict) and track.get("id")]


def _public_track(track: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(track.get("id") or ""),
        "title": str(track.get("title") or ""),
        "mood": str(track.get("mood") or ""),
        "bpm": int(track.get("bpm") or 0),
        "duration_seconds": int(track.get("duration_seconds") or 0),
        "provider": str(track.get("provider") or "Open music library"),
        "license": str(track.get("license") or ""),
        "usage_rule": str(track.get("usage_rule") or "可用于项目预览和渲染；视频长于音频时循环播放。"),
        "attribution": str(track.get("attribution") or ""),
        "source_url": str(track.get("source_url") or ""),
    }


def list_bgm_tracks() -> List[Dict[str, Any]]:
    return [_public_track(track) for track in _load_manifest()]


def get_bgm_track(track_id: str) -> Dict[str, Any]:
    for track in _load_manifest():
        if str(track.get("id")) == track_id:
            return {**track, **_public_track(track)}
    raise BgmAssetError("BGM track not found")


def ensure_bgm_track_cached(track_id: str) -> Dict[str, Any]:
    track = get_bgm_track(track_id)
    extension = _track_extension(track)
    local_source = _local_source_path(track)
    if local_source:
        return _cached_track(
            track,
            f"bundled://video_studio_bgm/{track_id}{extension}",
            local_source,
            f"/api/v1/video-studio/bgm-tracks/{track_id}/asset",
            extension,
        )

    key = f"video_studio_bgm/{track_id}{extension}"
    local_path = storage.path_for_key(key)
    if os.path.exists(local_path):
        return _cached_track(track, key, local_path, f"/data/{key}", extension)
    raise BgmAssetError("BGM track is not bundled; remote BGM downloads are disabled")


def _cached_track(
    track: Dict[str, Any],
    key: str,
    path: str,
    url: str,
    extension: str,
    mime: str | None = None,
) -> Dict[str, Any]:
    return {
        **_public_track(track),
        "asset_url": url,
        "asset_path": path,
        "storage_key": key,
        "cached": True,
        "mime": mime or _mime_for_extension(extension),
    }


def _local_source_path(track: Dict[str, Any]) -> str:
    filename = str(track.get("local_filename") or "").strip()
    if not filename:
        return ""
    source = os.path.abspath(os.path.join(ASSET_DIR, "tracks", filename))
    tracks_dir = os.path.abspath(os.path.join(ASSET_DIR, "tracks"))
    if not source.startswith(tracks_dir + os.sep):
        raise BgmAssetError("Invalid BGM local filename")
    return source if os.path.exists(source) else ""


def local_bgm_asset_path(track_id: str) -> str:
    track = get_bgm_track(track_id)
    local_source = _local_source_path(track)
    if not local_source:
        raise BgmAssetError("BGM local file not found")
    return local_source


def mime_for_track(track_id: str) -> str:
    return _mime_for_extension(_track_extension(get_bgm_track(track_id)))


def _track_extension(track: Dict[str, Any]) -> str:
    filename = str(track.get("local_filename") or "")
    suffix = os.path.splitext(filename)[1].lower()
    if suffix in {".mp3", ".wav", ".ogg", ".m4a"}:
        return suffix
    return ".mp3"


def _mime_for_extension(extension: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }.get(extension.lower(), "audio/mpeg")
