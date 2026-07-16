import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


PROJECT_SCHEMA_VERSION = "video_studio_project_v2"
DATA_GOVERNANCE_VERSION = "video_studio_data_governance_v1"
ASSET_LAYER_VERSION = "video_studio_asset_layer_v1"
MG_LAYER_VERSION = "video_studio_mg_layer_v1"
CANVAS_PROFILE = {
    "id": "landscape_16_9",
    "aspect_ratio": "16:9",
    "width": 1920,
    "height": 1080,
    "safe_area": {"left": 96, "right": 96, "top": 72, "bottom": 72},
}

WORKFLOW_KEYS = [
    "producer",
    "requirements",
    "creative_plan",
    "script",
    "director",
    "storyboard",
    "assets",
    "mg",
    "preview",
    "render",
]

WORKFLOW_DEPENDENCIES = {
    "producer": ["topic"],
    "requirements": ["producer"],
    "creative_plan": ["requirements"],
    "script": ["topic"],
    "director": ["script"],
    "storyboard": ["director"],
    "assets": ["storyboard"],
    "mg": ["storyboard"],
    "preview": ["assets", "mg"],
    "render": ["preview"],
}
_STORE_LOCK = threading.RLock()

STAGE_TO_WORKFLOW_KEY = {
    "producer": "producer",
    "requirements": "requirements",
    "creative_plan": "creative_plan",
    "script": "script",
    "director_doc": "director",
    "storyboard": "storyboard",
    "editor": "preview",
}


def _workflow_item(status: str = "pending", *, updated_at: Optional[str] = None, error: str = "") -> Dict[str, Any]:
    return {"status": status, "updated_at": updated_at or _now_iso(), "error": error, "depends_on": []}


def _default_workflow_state(now: str) -> Dict[str, Any]:
    return {
        key: {
            "status": "pending",
            "updated_at": now,
            "error": "",
            "depends_on": WORKFLOW_DEPENDENCIES.get(key, []),
        }
        for key in WORKFLOW_KEYS
    }


def _default_data_governance(now: str) -> Dict[str, Any]:
    return {
        "version": DATA_GOVERNANCE_VERSION,
        "schema_versions": {
            "project": PROJECT_SCHEMA_VERSION,
            "director_document": "video_studio_director_document_v1",
            "storyboard": "video_studio_storyboard_v1",
            "asset_manifest": "video_studio_asset_manifest_v1",
            "mg_plan": "video_studio_mg_layer_v1",
            "render_manifest": "video_studio_render_manifest_v1",
        },
        "created_at": now,
        "updated_at": now,
    }


def _default_asset_layer() -> Dict[str, Any]:
    return {
        "version": ASSET_LAYER_VERSION,
        "canvas_profile_id": CANVAS_PROFILE["id"],
        "assets": [],
        "selected_asset_ids_by_shot": {},
        "readiness_summary": {"preview_ready": 0, "render_ready": 0, "blocked": 0},
    }


def _default_mg_layer() -> Dict[str, Any]:
    return {
        "version": MG_LAYER_VERSION,
        "canvas_profile_id": CANVAS_PROFILE["id"],
        "mg_clips": [],
        "html_assets": [],
        "readiness_summary": {"preview_ready": 0, "render_ready": 0, "blocked": 0},
    }


def _default_editor_layer() -> Dict[str, Any]:
    return {"version": "video_studio_editor_layer_v1", "autosave_enabled": True, "last_autosaved_at": ""}


def _default_render_layer() -> Dict[str, Any]:
    return {
        "version": "video_studio_render_layer_v1",
        "canvas_profile_id": CANVAS_PROFILE["id"],
        "jobs": [],
        "latest_output": None,
    }


def _orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _aspect_ratio_label(width: int, height: int) -> str:
    if not width or not height:
        return ""
    ratio = width / height
    if abs(ratio - (16 / 9)) < 0.08:
        return "16:9"
    if abs(ratio - (9 / 16)) < 0.08:
        return "9:16"
    return f"{width}:{height}"


def _sync_asset_layer_from_scene_groups(project: Dict[str, Any]) -> None:
    assets: list[Dict[str, Any]] = []
    selected: Dict[str, str] = {}
    editor_state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    selected_broll = editor_state.get("selected_broll_by_shot") if isinstance(editor_state.get("selected_broll_by_shot"), dict) else {}
    for group in project.get("scene_groups") or []:
        if not isinstance(group, dict):
            continue
        for shot in group.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shot_id = str(shot.get("id") or "")
            options = shot.get("broll_options") if isinstance(shot.get("broll_options"), list) else []
            for option in options:
                if not isinstance(option, dict) or not (option.get("asset_url") or option.get("asset_path")):
                    continue
                width = int(option.get("width") or 0)
                height = int(option.get("height") or 0)
                orientation = str(option.get("orientation") or _orientation(width, height) or "landscape")
                aspect_ratio = str(option.get("aspect_ratio") or _aspect_ratio_label(width, height) or "16:9")
                asset_id = str(option.get("id") or f"{shot_id}-asset-{len(assets) + 1}")
                preview_ready = bool(option.get("preview_ready", True))
                render_ready = bool(option.get("render_ready", orientation == "landscape" and aspect_ratio == "16:9"))
                assets.append(
                    {
                        "asset_id": asset_id,
                        "shot_id": shot_id,
                        "provider": str(option.get("provider") or "manual"),
                        "provider_id": str(option.get("provider_id") or asset_id),
                        "title": str(option.get("title") or ""),
                        "source_url": str(option.get("source_url") or ""),
                        "asset_url": str(option.get("asset_url") or ""),
                        "asset_path": str(option.get("asset_path") or ""),
                        "width": width,
                        "height": height,
                        "duration_seconds": int(option.get("duration_seconds") or 0),
                        "aspect_ratio": aspect_ratio,
                        "orientation": orientation,
                        "preview_ready": preview_ready,
                        "render_ready": render_ready,
                        "needs_transcode": bool(option.get("needs_transcode", False)),
                        "needs_crop": bool(option.get("needs_crop", orientation != "landscape" or aspect_ratio != "16:9")),
                        "license": str(option.get("license") or ""),
                        "selected": str(selected_broll.get(shot_id) or "") == asset_id,
                        "readiness_warnings": option.get("readiness_warnings") if isinstance(option.get("readiness_warnings"), list) else [],
                    }
                )
            if shot_id and selected_broll.get(shot_id):
                selected[shot_id] = str(selected_broll.get(shot_id))
    project["asset_layer"] = {
        "version": ASSET_LAYER_VERSION,
        "canvas_profile_id": CANVAS_PROFILE["id"],
        "assets": assets,
        "selected_asset_ids_by_shot": selected,
        "readiness_summary": {
            "preview_ready": sum(1 for asset in assets if asset.get("preview_ready")),
            "render_ready": sum(1 for asset in assets if asset.get("render_ready")),
            "blocked": sum(1 for asset in assets if not asset.get("preview_ready")),
        },
    }


def _append_audit(project: Dict[str, Any], action: str, *, source: str = "system", details: Optional[Dict[str, Any]] = None) -> None:
    audit_log = project.get("audit_log") if isinstance(project.get("audit_log"), list) else []
    audit_log.append(
        {
            "at": _now_iso(),
            "action": action,
            "source": source,
            "details": details or {},
        }
    )
    project["audit_log"] = audit_log[-120:]


WORKFLOW_PROGRESS_FIELDS = ("message", "step", "completed", "total", "job_id", "started_at", "finished_at")


def _mark_status(project: Dict[str, Any], key: str, status: str, *, error: str = "") -> None:
    if key not in WORKFLOW_KEYS:
        return
    workflow_state = project.setdefault("workflow_state", _default_workflow_state(_now_iso()))
    current = workflow_state.get(key) if isinstance(workflow_state.get(key), dict) else {}
    next_item = {
        "status": status,
        "updated_at": _now_iso(),
        "error": error,
        "depends_on": current.get("depends_on") or WORKFLOW_DEPENDENCIES.get(key, []),
    }
    for field in WORKFLOW_PROGRESS_FIELDS:
        if field in current:
            next_item[field] = current[field]
    workflow_state[key] = next_item


def _mark_stale(project: Dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        _mark_status(project, key, "stale")


def ensure_project_governance(project: Dict[str, Any]) -> Dict[str, Any]:
    now = str(project.get("created_at") or _now_iso())
    normalized = deepcopy(project)
    normalized["project_schema_version"] = PROJECT_SCHEMA_VERSION
    normalized["canvas_profile"] = deepcopy(CANVAS_PROFILE)
    normalized.setdefault("data_governance", _default_data_governance(now))
    normalized["data_governance"]["version"] = DATA_GOVERNANCE_VERSION
    normalized["data_governance"].setdefault("schema_versions", _default_data_governance(now)["schema_versions"])
    normalized["data_governance"]["schema_versions"]["project"] = PROJECT_SCHEMA_VERSION
    normalized["data_governance"]["schema_versions"]["asset_manifest"] = "video_studio_asset_manifest_v1"
    normalized["data_governance"]["updated_at"] = str(normalized.get("updated_at") or _now_iso())
    normalized["target_duration_seconds"] = max(60, min(1800, int(normalized.get("target_duration_seconds") or 180)))

    workflow_state = normalized.get("workflow_state") if isinstance(normalized.get("workflow_state"), dict) else {}
    defaults = _default_workflow_state(now)
    for key, default_value in defaults.items():
        item = workflow_state.get(key) if isinstance(workflow_state.get(key), dict) else {}
        next_item = {
            "status": str(item.get("status") or default_value["status"]),
            "updated_at": str(item.get("updated_at") or default_value["updated_at"]),
            "error": str(item.get("error") or ""),
            "depends_on": item.get("depends_on") if isinstance(item.get("depends_on"), list) else default_value["depends_on"],
        }
        for field in WORKFLOW_PROGRESS_FIELDS:
            if field in item:
                next_item[field] = item[field]
        workflow_state[key] = next_item
    normalized["workflow_state"] = workflow_state

    normalized.setdefault("asset_layer", _default_asset_layer())
    normalized["asset_layer"]["version"] = ASSET_LAYER_VERSION
    normalized["asset_layer"]["canvas_profile_id"] = CANVAS_PROFILE["id"]
    normalized["asset_layer"].setdefault("assets", [])
    normalized["asset_layer"].setdefault("selected_asset_ids_by_shot", {})
    normalized["asset_layer"].setdefault("readiness_summary", {"preview_ready": 0, "render_ready": 0, "blocked": 0})

    normalized.setdefault("mg_layer", _default_mg_layer())
    normalized["mg_layer"]["version"] = MG_LAYER_VERSION
    normalized["mg_layer"]["canvas_profile_id"] = CANVAS_PROFILE["id"]
    normalized["mg_layer"].setdefault("mg_clips", [])
    normalized["mg_layer"].setdefault("html_assets", [])
    normalized["mg_layer"].setdefault("readiness_summary", {"preview_ready": 0, "render_ready": 0, "blocked": 0})

    normalized.setdefault("editor_layer", _default_editor_layer())
    editor_state = normalized.get("editor_state") if isinstance(normalized.get("editor_state"), dict) else {}
    editor_state.setdefault("mg_design_doc_overrides", {})
    editor_state.setdefault("selected_bgm_track_id", "")
    editor_state.setdefault("selected_bgm_track", None)
    editor_state.setdefault("bgm_volume", 0.35)
    normalized["editor_state"] = editor_state
    normalized.setdefault("render_layer", _default_render_layer())
    normalized["render_layer"]["canvas_profile_id"] = CANVAS_PROFILE["id"]
    if not isinstance(normalized.get("audit_log"), list):
        normalized["audit_log"] = []
    return normalized


def _apply_governance_transition(project: Dict[str, Any], patch: Dict[str, Any]) -> None:
    stage = str(patch.get("stage") or "")
    ready_key = STAGE_TO_WORKFLOW_KEY.get(stage)
    if ready_key:
        _mark_status(project, ready_key, "ready")

    if "producer_analysis" in patch:
        _mark_status(project, "producer", "ready")
    if "production_requirement_document" in patch:
        _mark_status(project, "requirements", "ready")
    if "creative_plan" in patch:
        _mark_status(project, "creative_plan", "ready")
    if "script" in patch or "script_director" in patch:
        _mark_status(project, "script", "ready")
    if "director_document" in patch:
        _mark_status(project, "director", "ready")
    if "scene_groups" in patch:
        _mark_status(project, "storyboard", "ready")
        _sync_asset_layer_from_scene_groups(project)
    if "editor_asset_status" in patch:
        asset_status = patch.get("editor_asset_status") if isinstance(patch.get("editor_asset_status"), dict) else {}
        total_shots = int(asset_status.get("total_shots") or 0)
        broll_ready_count = int(asset_status.get("broll_ready_count") or 0)
        has_asset_errors = bool(asset_status.get("errors"))
        asset_workflow_status = "ready" if total_shots > 0 and broll_ready_count >= total_shots and not has_asset_errors else "partial"
        _mark_status(project, "assets", asset_workflow_status, error="；".join(str(item) for item in (asset_status.get("errors") or [])[:3]))
        _mark_status(project, "mg", "ready")
    if "composition_preview_url" in patch:
        _mark_status(project, "preview", "ready")
    if "final_video_url" in patch:
        _mark_status(project, "render", "ready")

    if "topic" in patch:
        _mark_stale(project, ["script", "director", "storyboard", "assets", "mg", "preview", "render"])
        project.pop("creative_plan_draft", None)
        project.pop("html_generation_draft", None)
        _append_audit(project, "topic_updated", source="user", details={"stage": stage or "topic"})
    elif "editor_state" in patch:
        editor_patch = patch.get("editor_state") if isinstance(patch.get("editor_state"), dict) else {}
        changed_script = bool(editor_patch.get("shot_scripts"))
        changed_selection = bool(editor_patch.get("selected_broll_by_shot") or editor_patch.get("html_design_overrides"))
        if changed_script:
            _mark_stale(project, ["storyboard", "preview", "render"])
        elif changed_selection:
            _mark_stale(project, ["preview", "render"])
        project.setdefault("editor_layer", _default_editor_layer())["last_autosaved_at"] = _now_iso()
        _append_audit(project, "editor_state_updated", source="user")
    elif "production_format" in patch and stage == "format":
        _mark_stale(project, ["requirements", "creative_plan", "director", "storyboard", "assets", "mg", "preview", "render"])
        project.pop("creative_plan_draft", None)
        project.pop("html_generation_draft", None)
        _append_audit(project, "production_format_updated", source="user")
    elif stage:
        _append_audit(project, f"stage_{stage}", source="system")


class VideoStudioStore:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.projects_file = os.path.join(data_dir, "video_studio_projects.json")

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.projects_file):
            return {"projects": []}
        try:
            with open(self.projects_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("projects"), list):
                return data
        except Exception:
            pass
        return {"projects": []}

    def _save(self, data: Dict[str, Any]) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self.projects_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.projects_file)

    def create_project(self, topic: str, format: str, production_format: str, target_duration_seconds: int = 180) -> Dict[str, Any]:
        now = _now_iso()
        safe_duration = max(60, min(1800, int(target_duration_seconds or 180)))
        project = {
            "id": str(uuid.uuid4()),
            "project_schema_version": PROJECT_SCHEMA_VERSION,
            "topic": topic,
            "format": format,
            "production_format": production_format,
            "target_duration_seconds": safe_duration,
            "stage": "topic",
            "canvas_profile": deepcopy(CANVAS_PROFILE),
            "data_governance": _default_data_governance(now),
            "workflow_state": _default_workflow_state(now),
            "producer_analysis": None,
            "selected_production_option": None,
            "production_requirement_document": None,
            "creative_plan": None,
            "script": "",
            "script_director": None,
            "director_document": None,
            "scene_groups": [],
            "information_layer": [],
            "director_timeline": [],
            "design_plan": {"version": "video_studio_design_plan_v1", "scenes": []},
            "scene_plan_v2": [],
            "asset_layer": _default_asset_layer(),
            "mg_layer": _default_mg_layer(),
            "editor_layer": _default_editor_layer(),
            "render_layer": _default_render_layer(),
            "render_manifest": None,
            "editor_state": {
                "selected_shot_id": "",
                "shot_scripts": {},
                "selected_broll_by_shot": {},
                "html_design_overrides": {},
                "mg_design_doc_overrides": {},
                "avatar_enabled": True,
                "bgm_enabled": True,
                "bgm_volume": 0.35,
                "selected_bgm_track_id": "",
                "selected_bgm_track": None,
            },
            "created_at": now,
            "updated_at": now,
            "audit_log": [],
        }
        _append_audit(project, "project_created", source="system", details={"format": format, "production_format": production_format})
        with _STORE_LOCK:
            data = self._load()
            data["projects"] = [project, *(data.get("projects") or [])]
            self._save(data)
        return project

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        for project in self._load().get("projects") or []:
            if project.get("id") == project_id:
                return ensure_project_governance(project)
        return None

    def list_projects(self, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
        projects = [
            ensure_project_governance(project)
            for project in self._load().get("projects") or []
            if isinstance(project, dict)
        ]
        if status == "unfinished":
            projects = [project for project in projects if not project.get("final_video_url")]
        return sorted(projects, key=lambda project: str(project.get("updated_at") or ""), reverse=True)

    def delete_project(self, project_id: str) -> bool:
        with _STORE_LOCK:
            data = self._load()
            projects = data.get("projects") or []
            next_projects = [project for project in projects if not (isinstance(project, dict) and project.get("id") == project_id)]
            if len(next_projects) == len(projects):
                return False
            data["projects"] = next_projects
            self._save(data)
            return True

    def update_project(self, project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        with _STORE_LOCK:
            data = self._load()
            projects = data.get("projects") or []
            for index, project in enumerate(projects):
                if project.get("id") == project_id:
                    current = ensure_project_governance(project)
                    merged = ensure_project_governance({**current, **patch, "updated_at": _now_iso()})
                    _apply_governance_transition(merged, patch)
                    merged["data_governance"]["updated_at"] = str(merged.get("updated_at") or _now_iso())
                    projects[index] = merged
                    data["projects"] = projects
                    self._save(data)
                    return merged
        raise KeyError("Project not found")
