import hashlib
import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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


def _derived_mg_layer(project: Dict[str, Any]) -> Dict[str, Any]:
    existing = deepcopy(project.get("mg_layer") if isinstance(project.get("mg_layer"), dict) else {})
    html_assets = existing.get("html_assets") if isinstance(existing.get("html_assets"), list) else []
    mg_clips = existing.get("mg_clips") if isinstance(existing.get("mg_clips"), list) else []
    derived_assets: List[Dict[str, Any]] = []
    derived_clips: List[Dict[str, Any]] = []
    for group in _scene_groups(project):
        for shot in [item for item in group.get("shots") or [] if isinstance(item, dict)]:
            shot_id = str(shot.get("id") or "").strip()
            html_design = _shot_html_design(shot)
            if not shot_id or not html_design:
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
                    "render_strategy": asset["render_strategy"],
                    "visual_system": asset["visual_system"],
                    "html_asset_id": asset["id"],
                    "status": "ready",
                }
            )
    if derived_assets:
        known_asset_ids = {str(item.get("id") or "") for item in html_assets if isinstance(item, dict)}
        html_assets = [*html_assets, *[item for item in derived_assets if item["id"] not in known_asset_ids]]
        known_clip_ids = {str(item.get("id") or "") for item in mg_clips if isinstance(item, dict)}
        mg_clips = [*mg_clips, *[item for item in derived_clips if item["id"] not in known_clip_ids]]
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
    scene_groups = deepcopy(project.get("scene_groups") or [])
    design_plan = _design_plan_with_shot_html(project)
    mg_layer = _derived_mg_layer(project)
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
