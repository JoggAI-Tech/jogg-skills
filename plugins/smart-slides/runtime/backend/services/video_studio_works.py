import hashlib
import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import video_studio_bespoke_html


WORK_SCHEMA_VERSION = "video_studio_work_v1"
_WORKS_LOCK = threading.RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_project_for_work(project: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    if not project.get("scene_groups"):
        errors.append("请先生成分镜表")
    render_manifest = project.get("render_manifest") if isinstance(project.get("render_manifest"), dict) else {}
    if not render_manifest:
        errors.append("缺少渲染清单，请重新生成分镜表")
    design_plan = project.get("design_plan") if isinstance(project.get("design_plan"), dict) else {}
    mg_clips = design_plan.get("mg_clips") if isinstance(design_plan.get("mg_clips"), list) else []
    if str(project.get("production_format") or "") == "broll_html":
        if not mg_clips:
            errors.append("缺少 HTML/MG 设计文档")
        elif not all(isinstance(clip, dict) and isinstance(clip.get("design_doc"), dict) for clip in mg_clips):
            errors.append("HTML/MG 设计文档不完整")
    return {
        "version": "video_studio_work_validation_v1",
        "status": "failed" if errors else "passed",
        "errors": errors,
        "checked_at": _now_iso(),
    }


def _scene_groups(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = project.get("scene_groups") if isinstance(project.get("scene_groups"), list) else []
    return [group for group in groups if isinstance(group, dict)]


def _shot_html_design(shot: Dict[str, Any]) -> Dict[str, Any]:
    html_design = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
    custom_html = str(html_design.get("custom_html") or "").strip()
    custom_css = str(html_design.get("custom_css") or "").strip()
    if not custom_html and not custom_css:
        return {}
    return html_design


def _shot_timeline(project: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    timeline: Dict[str, Dict[str, float]] = {}
    cursor = 0.0
    for group in _scene_groups(project):
        for shot in [item for item in group.get("shots") or [] if isinstance(item, dict)]:
            shot_id = str(shot.get("id") or "").strip()
            duration = max(0.1, float(shot.get("duration_seconds") or 0.1))
            start = float(shot.get("start_seconds")) if isinstance(shot.get("start_seconds"), (int, float)) else cursor
            end = float(shot.get("end_seconds")) if isinstance(shot.get("end_seconds"), (int, float)) else start + duration
            if shot_id:
                timeline[shot_id] = {"start": round(start, 3), "end": round(max(start + 0.1, end), 3)}
            cursor = max(cursor, end)
    return timeline


def _declared_mg_clips(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Any] = []
    existing = project.get("mg_layer") if isinstance(project.get("mg_layer"), dict) else {}
    candidates.extend(existing.get("mg_clips") if isinstance(existing.get("mg_clips"), list) else [])
    candidates.extend(project.get("mg_clips") if isinstance(project.get("mg_clips"), list) else [])
    design_plan = project.get("design_plan") if isinstance(project.get("design_plan"), dict) else {}
    candidates.extend(design_plan.get("mg_clips") if isinstance(design_plan.get("mg_clips"), list) else [])
    manifest = project.get("render_manifest") if isinstance(project.get("render_manifest"), dict) else {}
    candidates.extend(manifest.get("mg_clips") if isinstance(manifest.get("mg_clips"), list) else [])
    clips: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        clip_id = str(candidate.get("id") or "").strip()
        if not clip_id or clip_id in seen:
            continue
        seen.add(clip_id)
        clips.append(deepcopy(candidate))
    return clips


def _html_asset_for_clip(
    clip: Dict[str, Any],
    shots_by_id: Dict[str, Dict[str, Any]],
    existing_assets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    asset_id = str(clip.get("html_asset_id") or "").strip()
    existing = next((item for item in existing_assets if str(item.get("id") or "") == asset_id), None) if asset_id else None
    bound_shots = [str(item) for item in clip.get("bound_shots") or [] if str(item) in shots_by_id]
    scene_id = str(clip.get("scene_id") or "")
    if not bound_shots and scene_id in shots_by_id:
        bound_shots = [scene_id]
    base_shot = shots_by_id.get(scene_id) or next((shots_by_id[item] for item in bound_shots if item in shots_by_id), {})
    html_design = _shot_html_design(base_shot)
    if existing:
        asset = deepcopy(existing)
    elif html_design:
        asset = {
            "version": "video_studio_html_asset_v1",
            "id": asset_id or str(html_design.get("asset_id") or f"html:{clip.get('id') or scene_id}"),
            "render_strategy": str(html_design.get("render_strategy") or base_shot.get("html_render_strategy") or "llm_bespoke_html"),
            "visual_system": str(html_design.get("visual_system") or (base_shot.get("mg_director") or {}).get("visual_system") or ""),
            "custom_html": str(html_design.get("custom_html") or ""),
            "custom_css": str(html_design.get("custom_css") or ""),
            "layout_summary": str(html_design.get("layout_summary") or ""),
            "edit_schema": deepcopy(html_design.get("edit_schema") if isinstance(html_design.get("edit_schema"), dict) else {}),
            "validation": deepcopy(html_design.get("validation") if isinstance(html_design.get("validation"), dict) else {}),
            "preview_ready": True,
            "render_ready": True,
        }
    else:
        return {}
    asset.update({"scene_id": scene_id or (bound_shots[0] if bound_shots else ""), "shot_id": scene_id or (bound_shots[0] if bound_shots else ""), "bound_shots": bound_shots})
    return asset


def _derived_mg_layer(project: Dict[str, Any]) -> Dict[str, Any]:
    existing = deepcopy(project.get("mg_layer") if isinstance(project.get("mg_layer"), dict) else {})
    existing_assets = [deepcopy(item) for item in existing.get("html_assets") or [] if isinstance(item, dict)]
    html_assets: List[Dict[str, Any]] = []
    mg_clips: List[Dict[str, Any]] = []
    shots_by_id = {
        str(shot.get("id") or ""): shot
        for group in _scene_groups(project)
        for shot in group.get("shots") or []
        if isinstance(shot, dict) and str(shot.get("id") or "")
    }
    timeline = _shot_timeline(project)
    covered_shots: set[str] = set()
    for declared in _declared_mg_clips(project):
        bound_shots = [str(item) for item in declared.get("bound_shots") or [] if str(item) in shots_by_id]
        scene_id = str(declared.get("scene_id") or "")
        if not bound_shots and scene_id in shots_by_id:
            bound_shots = [scene_id]
        if not bound_shots:
            continue
        start = min(timeline[item]["start"] for item in bound_shots)
        end = max(timeline[item]["end"] for item in bound_shots)
        asset = _html_asset_for_clip({**declared, "bound_shots": bound_shots}, shots_by_id, existing_assets)
        if not asset:
            continue
        clip = {
            **declared,
            "version": str(declared.get("version") or "mg_clip_v1"),
            "scene_id": scene_id or bound_shots[0],
            "bound_shots": bound_shots,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "html_asset_id": str(asset.get("id") or ""),
            "shot_offsets": {item: round(timeline[item]["start"] - start, 3) for item in bound_shots},
            "status": str(declared.get("status") or "ready"),
        }
        mg_clips.append(clip)
        html_assets.append(asset)
        covered_shots.update(bound_shots)

    derived_assets: List[Dict[str, Any]] = []
    derived_clips: List[Dict[str, Any]] = []
    for group in _scene_groups(project):
        for shot in [item for item in group.get("shots") or [] if isinstance(item, dict)]:
            shot_id = str(shot.get("id") or "").strip()
            html_design = _shot_html_design(shot)
            if not shot_id or not html_design or shot_id in covered_shots:
                continue
            mg_director = shot.get("mg_director") if isinstance(shot.get("mg_director"), dict) else {}
            asset = {
                "version": "video_studio_html_asset_v1",
                "id": str(html_design.get("asset_id") or f"html:{shot_id}"),
                "shot_id": shot_id,
                "scene_id": shot_id,
                "bound_shots": [shot_id],
                "render_strategy": str(html_design.get("render_strategy") or shot.get("html_render_strategy") or "llm_bespoke_html"),
                "visual_system": str(html_design.get("visual_system") or mg_director.get("visual_system") or ""),
                "custom_html": str(html_design.get("custom_html") or ""),
                "custom_css": str(html_design.get("custom_css") or ""),
                "layout_summary": str(html_design.get("layout_summary") or ""),
                "edit_schema": deepcopy(html_design.get("edit_schema") if isinstance(html_design.get("edit_schema"), dict) else {}),
                "validation": deepcopy(html_design.get("validation") if isinstance(html_design.get("validation"), dict) else {}),
                "preview_ready": True,
                "render_ready": True,
            }
            derived_assets.append(asset)
            derived_clips.append(
                {
                    "version": "mg_clip_v1",
                    "id": str(html_design.get("clip_id") or f"mg:{shot_id}"),
                    "scene_id": shot_id,
                    "bound_shots": [shot_id],
                    "start": timeline.get(shot_id, {}).get("start", 0.0),
                    "end": timeline.get(shot_id, {}).get("end", float(shot.get("duration_seconds") or 0.1)),
                    "duration": round(timeline.get(shot_id, {}).get("end", 0.1) - timeline.get(shot_id, {}).get("start", 0.0), 3),
                    "shot_offsets": {shot_id: 0.0},
                    "render_strategy": asset["render_strategy"],
                    "visual_system": asset["visual_system"],
                    "html_asset_id": asset["id"],
                    "status": "ready",
                }
            )
    known_asset_ids = {str(item.get("id") or "") for item in html_assets if isinstance(item, dict)}
    html_assets.extend(item for item in derived_assets if item["id"] not in known_asset_ids)
    known_clip_ids = {str(item.get("id") or "") for item in mg_clips if isinstance(item, dict)}
    mg_clips.extend(item for item in derived_clips if item["id"] not in known_clip_ids)
    editor_state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    clip_overrides = editor_state.get("html_block_overrides_by_clip") if isinstance(editor_state.get("html_block_overrides_by_clip"), dict) else {}
    assets_by_id = {str(item.get("id") or ""): item for item in html_assets if isinstance(item, dict) and str(item.get("id") or "")}
    for clip in mg_clips:
        if not isinstance(clip, dict):
            continue
        clip_id = str(clip.get("id") or "")
        overrides = clip_overrides.get(clip_id) if isinstance(clip_overrides.get(clip_id), dict) else {}
        asset = assets_by_id.get(str(clip.get("html_asset_id") or ""))
        if not overrides or not isinstance(asset, dict):
            continue
        schema = asset.get("edit_schema") if isinstance(asset.get("edit_schema"), dict) else {}
        asset["custom_html"] = video_studio_bespoke_html.apply_edit_text_overrides(str(asset.get("custom_html") or ""), schema, overrides)
        override_css = video_studio_bespoke_html.build_edit_override_css(schema, overrides)
        if override_css:
            asset["custom_css"] = f"{str(asset.get('custom_css') or '').rstrip()}\n\n{override_css}".strip()
    existing.update(
        {
            "version": str(existing.get("version") or "video_studio_mg_layer_v1"),
            "canvas_profile_id": str(existing.get("canvas_profile_id") or (project.get("canvas_profile") or {}).get("id") or "landscape_16_9"),
            "mg_clips": mg_clips,
            "html_assets": html_assets,
            "readiness_summary": {
                "preview_ready": len(html_assets),
                "render_ready": len(html_assets),
                "blocked": 0,
            },
        }
    )
    return existing


def apply_mg_assets_to_scene_groups(scene_groups: List[Dict[str, Any]], mg_layer: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = deepcopy(scene_groups)
    assets = mg_layer.get("html_assets") if isinstance(mg_layer.get("html_assets"), list) else []
    clips = mg_layer.get("mg_clips") if isinstance(mg_layer.get("mg_clips"), list) else []
    assets_by_id = {str(item.get("id") or ""): item for item in assets if isinstance(item, dict) and str(item.get("id") or "")}
    asset_by_shot: Dict[str, Dict[str, Any]] = {}
    clip_by_shot: Dict[str, Dict[str, Any]] = {}
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        asset = assets_by_id.get(str(clip.get("html_asset_id") or ""))
        if not asset:
            continue
        for shot_id in [str(item) for item in clip.get("bound_shots") or [] if str(item)]:
            asset_by_shot.setdefault(shot_id, asset)
            clip_by_shot.setdefault(shot_id, clip)
    for group in groups:
        for shot in group.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shot_id = str(shot.get("id") or "")
            asset = asset_by_shot.get(shot_id)
            clip = clip_by_shot.get(shot_id)
            shot.pop("mg_clip_id", None)
            shot.pop("mg_clip_offset_seconds", None)
            if not asset or not clip:
                continue
            offsets = clip.get("shot_offsets") if isinstance(clip.get("shot_offsets"), dict) else {}
            try:
                clip_offset = max(0.0, float(offsets.get(shot_id) or 0.0))
            except (TypeError, ValueError):
                clip_offset = 0.0
            base = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
            shot["html_design"] = {
                **base,
                "asset_id": str(asset.get("id") or ""),
                "clip_id": str(clip.get("id") or ""),
                "custom_html": str(asset.get("custom_html") or ""),
                "custom_css": str(asset.get("custom_css") or ""),
                "edit_schema": deepcopy(asset.get("edit_schema") if isinstance(asset.get("edit_schema"), dict) else {}),
                "render_strategy": str(asset.get("render_strategy") or clip.get("render_strategy") or "llm_bespoke_html"),
            }
            shot["mg_clip_id"] = str(clip.get("id") or "")
            shot["mg_clip_offset_seconds"] = round(clip_offset, 3)
    return groups


def _design_plan_with_shot_html(project: Dict[str, Any]) -> Dict[str, Any]:
    design_plan = deepcopy(project.get("design_plan") if isinstance(project.get("design_plan"), dict) else {})
    scenes = design_plan.get("scenes") if isinstance(design_plan.get("scenes"), list) else []
    scene_by_id = {
        str(scene.get("scene_id") or scene.get("id") or ""): scene
        for scene in scenes
        if isinstance(scene, dict)
    }
    for group in _scene_groups(project):
        for shot in [item for item in group.get("shots") or [] if isinstance(item, dict)]:
            shot_id = str(shot.get("id") or "").strip()
            html_design = _shot_html_design(shot)
            if not shot_id or not html_design:
                continue
            scene = scene_by_id.get(shot_id)
            if not scene:
                scene = {"scene_id": shot_id, "title": str(shot.get("title") or shot_id)}
                scenes.append(scene)
                scene_by_id[shot_id] = scene
            spec = scene.get("scene_design_spec") if isinstance(scene.get("scene_design_spec"), dict) else {}
            spec.update(
                {
                    "custom_html": str(html_design.get("custom_html") or spec.get("custom_html") or ""),
                    "custom_css": str(html_design.get("custom_css") or spec.get("custom_css") or ""),
                    "html_overlay_asset": {
                        "version": "video_studio_html_asset_v1",
                        "source": "video_studio_ai_html",
                        "render_strategy": str(html_design.get("render_strategy") or shot.get("html_render_strategy") or "llm_bespoke_html"),
                        "custom_html": str(html_design.get("custom_html") or ""),
                        "custom_css": str(html_design.get("custom_css") or ""),
                        "layout_summary": str(html_design.get("layout_summary") or ""),
                        "edit_schema": deepcopy(html_design.get("edit_schema") if isinstance(html_design.get("edit_schema"), dict) else {}),
                    },
                }
            )
            scene["scene_design_spec"] = spec
    if scenes:
        design_plan["scenes"] = scenes
    return design_plan


def build_render_snapshot(project: Dict[str, Any]) -> Dict[str, Any]:
    design_plan = _design_plan_with_shot_html(project)
    mg_layer = _derived_mg_layer(project)
    scene_groups = apply_mg_assets_to_scene_groups(project.get("scene_groups") or [], mg_layer)
    return {
        "version": "video_studio_render_snapshot_v1",
        "project_id": str(project.get("id") or ""),
        "project_schema_version": str(project.get("project_schema_version") or ""),
        "topic": str(project.get("topic") or ""),
        "canvas_profile": deepcopy(project.get("canvas_profile") or {}),
        "production_format": str(project.get("production_format") or ""),
        "scene_groups": scene_groups,
        "director_timeline": deepcopy(project.get("director_timeline") or []),
        "information_layer": deepcopy(project.get("information_layer") or []),
        "render_manifest": deepcopy(project.get("render_manifest") or {}),
        "design_plan": design_plan,
        "asset_layer": deepcopy(project.get("asset_layer") or {}),
        "mg_layer": mg_layer,
        "editor_state": deepcopy(project.get("editor_state") or {}),
        "created_at": _now_iso(),
    }


def render_snapshot_fingerprint(snapshot: Dict[str, Any]) -> str:
    payload = deepcopy(snapshot)
    payload.pop("created_at", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def work_matches_project_snapshot(work: Dict[str, Any], project: Dict[str, Any]) -> bool:
    snapshot = work.get("render_snapshot") if isinstance(work.get("render_snapshot"), dict) else None
    if snapshot is None:
        return False
    return render_snapshot_fingerprint(snapshot) == render_snapshot_fingerprint(build_render_snapshot(project))


class VideoStudioWorksStore:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.works_file = os.path.join(data_dir, "video_studio_works.json")

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.works_file):
            return {"works": []}
        try:
            with open(self.works_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("works"), list):
                return data
        except Exception:
            pass
        return {"works": []}

    def _save(self, data: Dict[str, Any]) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self.works_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.works_file)

    def create_work(self, project: Dict[str, Any], *, preview_artifact_url: str = "") -> Dict[str, Any]:
        validation = validate_project_for_work(project)
        status = "failed" if validation["status"] == "failed" else "queued"
        now = _now_iso()
        work = {
            "version": WORK_SCHEMA_VERSION,
            "id": str(uuid.uuid4()),
            "project_id": str(project.get("id") or ""),
            "project_title": str(project.get("topic") or ""),
            "status": status,
            "validation": validation,
            "render_snapshot": build_render_snapshot(project),
            "preview_artifact_url": str(preview_artifact_url or project.get("composition_preview_url") or ""),
            "output": None,
            "progress": {"phase": "queued", "percent": 0},
            "error": "; ".join(validation["errors"]) if validation["errors"] else "",
            "logs": [
                {
                    "at": now,
                    "level": "error" if status == "failed" else "info",
                    "message": (
                        "作品验证失败，未进入渲染队列。"
                        if status == "failed"
                        else "作品已创建，等待本机 Podcastor 编辑器合同和 FFmpeg 渲染。"
                    ),
                }
            ],
            "created_at": now,
            "updated_at": now,
        }
        with _WORKS_LOCK:
            data = self._load()
            data["works"] = [work, *(data.get("works") or [])]
            self._save(data)
        return work

    def list_works(self, *, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        works = [work for work in self._load().get("works") or [] if isinstance(work, dict)]
        if project_id:
            works = [work for work in works if str(work.get("project_id") or "") == project_id]
        return works

    def get_work(self, work_id: str) -> Optional[Dict[str, Any]]:
        for work in self.list_works():
            if str(work.get("id") or "") == work_id:
                return work
        return None

    def update_work(
        self,
        work_id: str,
        patch: Dict[str, Any],
        *,
        log_level: str = "info",
        log_message: str = "",
    ) -> Dict[str, Any]:
        with _WORKS_LOCK:
            data = self._load()
            works = data.get("works") or []
            now = _now_iso()
            for index, work in enumerate(works):
                if not isinstance(work, dict) or str(work.get("id") or "") != work_id:
                    continue
                next_work = {**work, **patch, "updated_at": now}
                if log_message:
                    logs = next_work.get("logs") if isinstance(next_work.get("logs"), list) else []
                    next_work["logs"] = [
                        *logs,
                        {"at": now, "level": log_level, "message": log_message},
                    ]
                works[index] = next_work
                data["works"] = works
                self._save(data)
                return next_work
        raise KeyError("Work not found")
