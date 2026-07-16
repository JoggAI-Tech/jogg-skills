import mimetypes
import os
import re
import threading
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.services import storage
from backend.services import video_studio_bgm
from backend.services import video_studio_broll
from backend.services import video_studio_planner
from backend.services.video_studio_mg_design import normalize_mg_design_doc
from backend.services.video_studio_store import VideoStudioStore, ensure_project_governance
from backend.services.video_studio_works import VideoStudioWorksStore, work_matches_project_snapshot
from render import hyperframes_adapter


router = APIRouter(prefix="/api/v1/video-studio", tags=["video-studio"])
DATA_DIR = os.path.expanduser(os.getenv("SMART_SLIDES_DATA_DIR", "~/.codex/smart-slides/data"))
_IMPORT_LOCK = threading.RLock()


class CreateProjectRequest(BaseModel):
    topic: str = Field(min_length=1)
    format: Literal["short", "long"] = "long"
    production_format: Literal["broll", "broll_html"] = "broll_html"
    target_duration_seconds: int = Field(default=600, ge=60, le=1800)


class FlexiblePatch(BaseModel):
    model_config = ConfigDict(extra="allow")


class ProductionOptionPatch(BaseModel):
    option_id: str
    html_render_strategy: str = ""


class ProductionFormatPatch(BaseModel):
    production_format: Literal["broll", "broll_html"]


class TopicPatch(BaseModel):
    topic: str
    target_duration_seconds: Optional[int] = None


class WorkflowStagePatch(BaseModel):
    stage: str


class BgmTrackPatch(BaseModel):
    track_id: str


class MgDesignDocPatch(BaseModel):
    mg_clip_id: str
    design_doc: Dict[str, Any]


class BrollCandidateDownloadRequest(BaseModel):
    candidate: Dict[str, Any]


class ImportProjectRequest(BaseModel):
    project: Dict[str, Any]


def set_data_dir_for_tests(data_dir: str) -> None:
    global DATA_DIR
    DATA_DIR = data_dir
    storage.set_data_dir_for_tests(data_dir)


def _store() -> VideoStudioStore:
    os.makedirs(DATA_DIR, exist_ok=True)
    return VideoStudioStore(DATA_DIR)


def _works_store() -> VideoStudioWorksStore:
    os.makedirs(DATA_DIR, exist_ok=True)
    return VideoStudioWorksStore(DATA_DIR)


def _project_or_404(project_id: str) -> Dict[str, Any]:
    project = _store().get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _patch_dict(value: BaseModel) -> Dict[str, Any]:
    return value.model_dump(exclude_none=True)


def _workflow_ready(project: Dict[str, Any], key: str, message: str) -> Dict[str, Any]:
    workflow = deepcopy(project.get("workflow_state") if isinstance(project.get("workflow_state"), dict) else {})
    current = workflow.get(key) if isinstance(workflow.get(key), dict) else {}
    workflow[key] = {**current, "status": "ready", "step": "done", "message": message, "error": ""}
    return workflow


def _render_contract(project: Dict[str, Any], scene_groups: list[dict[str, Any]]) -> Dict[str, Any]:
    contract = video_studio_planner.build_render_contract_package(
        topic=str(project.get("topic") or ""),
        production_format=str(project.get("production_format") or "broll_html"),
        script=str(project.get("script") or ""),
        director_document=project.get("director_document") if isinstance(project.get("director_document"), dict) else None,
        scene_groups=scene_groups,
    )
    if str(project.get("production_format") or "broll_html") == "broll_html" and not contract.get("mg_clips"):
        fallback_clips = [
            layer["mg_clip"]
            for group in contract.get("scene_groups") or []
            for layer in group.get("html_layers") or []
            if isinstance(layer, dict) and isinstance(layer.get("mg_clip"), dict) and isinstance(layer["mg_clip"].get("design_doc"), dict)
        ]
        if fallback_clips:
            design_plan = {**(contract.get("design_plan") or {}), "mg_clips": fallback_clips}
            render_manifest = {**(contract.get("render_manifest") or {}), "mg_clips": fallback_clips, "design_plan": design_plan}
            contract.update(mg_clips=fallback_clips, design_plan=design_plan, render_manifest=render_manifest)
    return contract


def _scale_scene_group_durations(scene_groups: list[dict[str, Any]], target_duration_seconds: int) -> list[dict[str, Any]]:
    groups = deepcopy(scene_groups)
    units: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    for group in groups:
        for shot in group.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shots.append(shot)
            units.append({"text": str(shot.get("narration") or shot.get("title") or ""), "duration_seconds": shot.get("duration_seconds")})
    scaled = video_studio_planner.scale_scene_outline_durations(
        [{"voiceover_units": units}],
        target_duration_seconds,
    )
    scaled_units = scaled[0].get("voiceover_units", []) if scaled else []
    for shot, unit in zip(shots, scaled_units):
        shot["duration_seconds"] = int(unit.get("duration_seconds") or 1)
    return groups


def _create_preview(project_id: str, project: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    preview_project = deepcopy(project)
    editor_state = preview_project.get("editor_state") if isinstance(preview_project.get("editor_state"), dict) else {}
    avatar_assets = editor_state.get("avatar_assets_by_shot") if isinstance(editor_state.get("avatar_assets_by_shot"), dict) else {}
    selected_broll = deepcopy(editor_state.get("selected_broll_by_shot") if isinstance(editor_state.get("selected_broll_by_shot"), dict) else {})
    for group in preview_project.get("scene_groups") or []:
        for shot in group.get("shots") or []:
            shot_id = str(shot.get("id") or "")
            avatar = avatar_assets.get(shot_id) if isinstance(avatar_assets.get(shot_id), dict) else None
            if not avatar:
                continue
            option_id = f"avatar-preview:{shot_id}"
            shot["broll_options"] = [
                {
                    "id": option_id,
                    "title": "Jogg 数字人",
                    "asset_url": str(avatar.get("asset_url") or ""),
                    "asset_path": str(avatar.get("path") or avatar.get("asset_path") or ""),
                },
                *[item for item in shot.get("broll_options") or [] if isinstance(item, dict)],
            ]
            selected_broll[shot_id] = option_id
    preview_project["editor_state"] = {**editor_state, "selected_broll_by_shot": selected_broll}
    html_text = video_studio_planner.build_composition_preview_html(preview_project)
    storage.save_bytes(
        f"video_studio_previews/{project_id}/composition_preview.html",
        html_text.encode("utf-8"),
        "text/html; charset=utf-8",
    )
    preview_url = f"/api/v1/video-studio/projects/{project_id}/composition-preview.html"
    updated = _store().update_project(project_id, {"composition_preview_url": preview_url, "stage": "editor"})
    return updated, preview_url


def _find_shot(project: Dict[str, Any], shot_id: str) -> Dict[str, Any]:
    for group in project.get("scene_groups") or []:
        for shot in group.get("shots") or []:
            if isinstance(shot, dict) and str(shot.get("id") or "") == shot_id:
                return shot
    raise HTTPException(status_code=404, detail="Shot not found")


def _replace_shot(project: Dict[str, Any], shot_id: str, replacement: Dict[str, Any]) -> list[dict[str, Any]]:
    groups = []
    found = False
    for group in project.get("scene_groups") or []:
        shots = []
        for shot in group.get("shots") or []:
            if isinstance(shot, dict) and str(shot.get("id") or "") == shot_id:
                shots.append(replacement)
                found = True
            else:
                shots.append(shot)
        groups.append({**group, "shots": shots})
    if not found:
        raise HTTPException(status_code=404, detail="Shot not found")
    return groups


def _compact_query(value: str, limit: int = 72) -> str:
    return " ".join(str(value or "").split())[:limit].strip()


@router.post("/projects")
def create_project(req: CreateProjectRequest) -> Dict[str, object]:
    return {"project": _store().create_project(req.topic.strip(), req.format, req.production_format, req.target_duration_seconds)}


@router.get("/projects")
def list_projects(status: Optional[str] = None) -> Dict[str, object]:
    return {"projects": _store().list_projects(status=status)}


@router.post("/projects/import")
def import_project(req: ImportProjectRequest) -> Dict[str, object]:
    project = ensure_project_governance(req.project)
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        raise HTTPException(status_code=400, detail="Project id is required")
    store = _store()
    with _IMPORT_LOCK:
        data = store._load()
        projects = [item for item in data.get("projects") or [] if not (isinstance(item, dict) and str(item.get("id") or "") == project_id)]
        data["projects"] = [project, *projects]
        store._save(data)
    return {"project": project, "imported": True}


@router.get("/projects/{project_id}")
def get_project(project_id: str) -> Dict[str, object]:
    return {"project": _project_or_404(project_id)}


@router.delete("/projects/{project_id}")
def delete_project(project_id: str) -> Dict[str, object]:
    if not _store().delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True, "project_id": project_id}


@router.post("/projects/{project_id}/generate-script")
def generate_script(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    script = str(project.get("script") or "").strip() or video_studio_planner.fallback_script(str(project.get("topic") or ""))
    updated = _store().update_project(project_id, {"script": script, "stage": "producer"})
    return {"project": updated}


@router.post("/projects/{project_id}/generate-producer-analysis")
def generate_producer_analysis(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    analysis = video_studio_planner.normalize_producer_analysis({}, str(project.get("topic") or ""))
    selected = next((item for item in analysis.get("production_options", []) if item.get("recommended")), analysis["production_options"][-1])
    updated = _store().update_project(project_id, {"producer_analysis": analysis, "selected_production_option": selected, "stage": "producer"})
    return {"project": updated}


@router.patch("/projects/{project_id}/production-option")
def update_production_option(project_id: str, req: ProductionOptionPatch) -> Dict[str, object]:
    project = _project_or_404(project_id)
    analysis = project.get("producer_analysis") if isinstance(project.get("producer_analysis"), dict) else {}
    option = next((item for item in analysis.get("production_options", []) if str(item.get("id") or "") == req.option_id), None)
    if not option:
        raise HTTPException(status_code=404, detail="Production option not found")
    selected = {**option}
    if req.html_render_strategy:
        selected["html_mg_render_strategy"] = req.html_render_strategy
    updated = _store().update_project(project_id, {"selected_production_option": selected, "production_format": selected.get("production_format", "broll_html")})
    return {"project": updated}


@router.post("/projects/{project_id}/generate-requirement-document")
def generate_requirement_document(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    document = video_studio_planner.normalize_requirement_document({}, str(project.get("topic") or ""), str(project.get("production_format") or "broll_html"))
    updated = _store().update_project(project_id, {"production_requirement_document": document, "stage": "requirements"})
    return {"project": updated}


@router.post("/projects/{project_id}/generate-creative-plan")
def generate_creative_plan(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    plan = video_studio_planner.normalize_creative_plan(
        {},
        str(project.get("topic") or ""),
        project.get("production_requirement_document") if isinstance(project.get("production_requirement_document"), dict) else None,
        project.get("selected_production_option") if isinstance(project.get("selected_production_option"), dict) else None,
    )
    plan["scenes"] = video_studio_planner.scale_scene_outline_durations(
        plan.get("scenes") if isinstance(plan.get("scenes"), list) else [],
        int(project.get("target_duration_seconds") or 0),
    )
    plan["generation_source"] = "local_deterministic_fallback"
    workflow = _workflow_ready(project, "creative_plan", "本地创作规划已生成；Codex 可通过 planning-state 覆盖。")
    updated = _store().update_project(project_id, {"creative_plan": plan, "script": plan.get("script", ""), "script_director": plan.get("script_director"), "workflow_state": workflow, "stage": "creative_plan"})
    return {"project": updated}


@router.post("/projects/{project_id}/generate-director-document")
def generate_director_document(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    document = video_studio_planner.fallback_director_document(str(project.get("topic") or ""), str(project.get("production_format") or "broll_html"))
    updated = _store().update_project(project_id, {"director_document": document, "stage": "creative_plan"})
    return {"project": updated}


@router.post("/projects/{project_id}/generate-storyboard")
def generate_storyboard(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    script = str(project.get("script") or "").strip() or video_studio_planner.fallback_script(str(project.get("topic") or ""))
    creative_plan = project.get("creative_plan") if isinstance(project.get("creative_plan"), dict) else None
    if creative_plan and creative_plan.get("generation_source") != "local_deterministic_fallback":
        groups = video_studio_planner.generate_storyboard_from_creative_plan(
            creative_plan,
            str(project.get("production_format") or "broll_html"),
            project.get("director_document") if isinstance(project.get("director_document"), dict) else None,
        )
    else:
        groups = video_studio_planner.fallback_storyboard(
            str(project.get("topic") or ""), script, str(project.get("production_format") or "broll_html"),
            project.get("script_director") if isinstance(project.get("script_director"), dict) else None,
        )
    groups = _scale_scene_group_durations(groups, int(project.get("target_duration_seconds") or 0))
    contract = _render_contract({**project, "script": script}, groups)
    updated = _store().update_project(project_id, {"script": script, "scene_groups": contract.get("scene_groups", groups), **contract, "stage": "storyboard"})
    return {"project": updated}


@router.patch("/projects/{project_id}/planning-state")
def update_planning_state(project_id: str, req: FlexiblePatch) -> Dict[str, object]:
    project = _project_or_404(project_id)
    patch = _patch_dict(req)
    target_duration = int(patch.get("target_duration_seconds") or project.get("target_duration_seconds") or 0)
    if isinstance(patch.get("creative_plan"), dict):
        normalized_plan = video_studio_planner.normalize_creative_plan(
            patch["creative_plan"],
            str(patch.get("topic") or project.get("topic") or ""),
            patch.get("production_requirement_document") if isinstance(patch.get("production_requirement_document"), dict) else project.get("production_requirement_document"),
            patch.get("selected_production_option") if isinstance(patch.get("selected_production_option"), dict) else project.get("selected_production_option"),
        )
        normalized_plan["scenes"] = video_studio_planner.scale_scene_outline_durations(normalized_plan.get("scenes") or [], target_duration)
        patch["creative_plan"] = normalized_plan
        patch.setdefault("script", normalized_plan.get("script", ""))
        patch.setdefault("script_director", normalized_plan.get("script_director"))
    if isinstance(patch.get("scene_groups"), list):
        scaled_groups = _scale_scene_group_durations(patch["scene_groups"], target_duration)
        normalized = video_studio_planner.normalize_scene_groups(scaled_groups, str(patch.get("production_format") or project.get("production_format") or "broll_html"), patch.get("director_document") or project.get("director_document"))
        patch["scene_groups"] = normalized
        patch.update(_render_contract({**project, **patch}, normalized))
    return {"project": _store().update_project(project_id, patch)}


@router.patch("/projects/{project_id}/editor-state")
def update_editor_state(project_id: str, req: FlexiblePatch) -> Dict[str, object]:
    project = _project_or_404(project_id)
    state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    return {"project": _store().update_project(project_id, {"editor_state": {**state, **_patch_dict(req)}, "stage": "editor"})}


@router.patch("/projects/{project_id}/production-format")
def update_production_format(project_id: str, req: ProductionFormatPatch) -> Dict[str, object]:
    return {"project": _store().update_project(project_id, {"production_format": req.production_format})}


@router.patch("/projects/{project_id}/topic")
def update_topic(project_id: str, req: TopicPatch) -> Dict[str, object]:
    patch: Dict[str, Any] = {"topic": req.topic.strip(), "stage": "topic"}
    if req.target_duration_seconds is not None:
        patch["target_duration_seconds"] = max(60, min(1800, req.target_duration_seconds))
    return {"project": _store().update_project(project_id, patch)}


@router.patch("/projects/{project_id}/workflow-stage")
def update_workflow_stage(project_id: str, req: WorkflowStagePatch) -> Dict[str, object]:
    return {"project": _store().update_project(project_id, {"stage": req.stage})}


@router.get("/bgm-tracks")
def list_bgm_tracks() -> Dict[str, object]:
    return {"tracks": video_studio_bgm.list_bgm_tracks()}


@router.post("/bgm-tracks/{track_id}/cache")
def cache_bgm_track(track_id: str) -> Dict[str, object]:
    try:
        return {"track": video_studio_bgm.ensure_bgm_track_cached(track_id)}
    except video_studio_bgm.BgmAssetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/bgm-tracks/{track_id}/asset")
def get_bgm_track_asset(track_id: str):
    try:
        return FileResponse(video_studio_bgm.local_bgm_asset_path(track_id), media_type=video_studio_bgm.mime_for_track(track_id))
    except video_studio_bgm.BgmAssetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/projects/{project_id}/bgm-track")
def select_bgm_track(project_id: str, req: BgmTrackPatch) -> Dict[str, object]:
    project = _project_or_404(project_id)
    track = video_studio_bgm.ensure_bgm_track_cached(req.track_id)
    state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    updated = _store().update_project(project_id, {"editor_state": {**state, "selected_bgm_track_id": req.track_id, "selected_bgm_track": track}, "stage": "editor"})
    return {"project": updated, "track": track}


@router.patch("/projects/{project_id}/mg-design-doc")
def update_mg_design_doc(project_id: str, req: MgDesignDocPatch) -> Dict[str, object]:
    project = _project_or_404(project_id)
    state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    overrides = state.get("mg_design_doc_overrides") if isinstance(state.get("mg_design_doc_overrides"), dict) else {}
    document = normalize_mg_design_doc(req.design_doc)
    updated = _store().update_project(project_id, {"editor_state": {**state, "mg_design_doc_overrides": {**overrides, req.mg_clip_id: document}}, "stage": "editor"})
    return {"project": updated, "mg_clip_id": req.mg_clip_id, "design_doc": document}


@router.post("/projects/{project_id}/mg-clips/{mg_clip_id}/regenerate-html")
def regenerate_mg_clip_html(project_id: str, mg_clip_id: str) -> Dict[str, object]:
    _project_or_404(project_id)
    raise HTTPException(status_code=409, detail="本地插件不调用外部 HTML LLM；请让 Codex 生成 HTML/CSS 后写入 editor-state。")


@router.delete("/projects/{project_id}/mg-clips/{mg_clip_id}")
def delete_mg_clip(project_id: str, mg_clip_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    design = deepcopy(project.get("design_plan") if isinstance(project.get("design_plan"), dict) else {})
    clips = design.get("mg_clips") if isinstance(design.get("mg_clips"), list) else []
    removed = [clip for clip in clips if isinstance(clip, dict) and str(clip.get("id") or "") == mg_clip_id]
    if not removed:
        raise HTTPException(status_code=404, detail="MG clip not found")
    design["mg_clips"] = [clip for clip in clips if clip not in removed]
    updated = _store().update_project(project_id, {"design_plan": design, "stage": "editor"})
    updated, preview_url = _create_preview(project_id, updated)
    bound = [str(item) for clip in removed for item in clip.get("bound_shots", []) if str(item)]
    return {"project": updated, "mg_clip_id": mg_clip_id, "deleted_shot_ids": bound, "preview_url": preview_url}


@router.get("/projects/{project_id}/local-assets")
def list_local_assets(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    return {"assets": project.get("local_asset_library") if isinstance(project.get("local_asset_library"), list) else []}


@router.post("/projects/{project_id}/local-assets")
async def upload_local_asset(project_id: str, file_media: UploadFile = File(...), title: str = Form(""), tags: str = Form(""), duration_seconds: int = Form(6)) -> Dict[str, object]:
    project = _project_or_404(project_id)
    safe_name = os.path.basename(file_media.filename or "upload.bin")
    stored = storage.save_bytes(f"video_studio_assets/local_library/{project_id}_{uuid.uuid4().hex}_{safe_name}", await file_media.read(), file_media.content_type)
    asset = {"id": f"local-{uuid.uuid4().hex[:12]}", "title": title.strip() or safe_name, "tags": [item.strip() for item in tags.split(",") if item.strip()], "duration_seconds": max(1, duration_seconds), "asset_url": stored.url, "asset_path": stored.path, "mime": file_media.content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"}
    library = project.get("local_asset_library") if isinstance(project.get("local_asset_library"), list) else []
    updated = _store().update_project(project_id, {"local_asset_library": [asset, *library]})
    return {"project": updated, "asset": asset}


@router.post("/projects/{project_id}/shots/{shot_id}/materials")
async def upload_shot_material(project_id: str, shot_id: str, title: str = Form(...), duration_seconds: int = Form(...), file_media: UploadFile = File(...)) -> Dict[str, object]:
    project = _project_or_404(project_id)
    safe_name = os.path.basename(file_media.filename or "upload.bin")
    stored = storage.save_bytes(f"video_studio_assets/{project_id}_{shot_id}_{uuid.uuid4().hex}_{safe_name}", await file_media.read(), file_media.content_type)
    option = {"id": f"{shot_id}-upload-{uuid.uuid4().hex[:8]}", "title": title.strip() or safe_name, "description": "本地上传素材", "duration_seconds": max(1, duration_seconds), "visual_style": "本地素材", "asset_url": stored.url, "asset_path": stored.path, "search_query": "", "similar_materials": []}
    shot = _find_shot(project, shot_id)
    groups = _replace_shot(project, shot_id, {**shot, "broll_options": [option, *(shot.get("broll_options") or [])]})
    contract = _render_contract(project, groups)
    updated = _store().update_project(project_id, {"scene_groups": contract.get("scene_groups", groups), **contract, "stage": "editor"})
    return {"project": updated}


@router.get("/projects/{project_id}/shots/{shot_id}/broll-search")
def search_broll(project_id: str, shot_id: str, query: str = Query(""), per_page: int = Query(12, ge=1, le=24), providers: str = Query("pexels,pixabay"), slot_id: str = Query("")) -> Dict[str, object]:
    project = _project_or_404(project_id)
    shot = _find_shot(project, shot_id)
    try:
        candidates = video_studio_broll.search_broll_candidates(shot, query=query.strip(), per_page=per_page, providers=[item.strip() for item in providers.split(",") if item.strip()])
    except video_studio_broll.BrollAssetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    asset_plan = shot.get("asset_search_plan") if isinstance(shot.get("asset_search_plan"), dict) else {}
    queries = [query.strip()] if query.strip() else [_compact_query(str(item)) for item in asset_plan.get("search_queries", []) if _compact_query(str(item))]
    return {"candidates": candidates, "queries": queries[:6]}


@router.post("/projects/{project_id}/shots/{shot_id}/broll-assets/download")
def download_broll(project_id: str, shot_id: str, req: BrollCandidateDownloadRequest) -> Dict[str, object]:
    project = _project_or_404(project_id)
    try:
        option = video_studio_broll.download_broll_candidate(req.candidate, project_id=project_id, shot_id=shot_id)
    except video_studio_broll.BrollAssetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    shot = _find_shot(project, shot_id)
    options = [option, *[item for item in shot.get("broll_options") or [] if str(item.get("id") or "") != str(option.get("id") or "")]]
    groups = _replace_shot(project, shot_id, {**shot, "broll_options": options})
    contract = _render_contract(project, groups)
    state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    selected = state.get("selected_broll_by_shot") if isinstance(state.get("selected_broll_by_shot"), dict) else {}
    updated = _store().update_project(project_id, {"scene_groups": contract.get("scene_groups", groups), **contract, "editor_state": {**state, "selected_broll_by_shot": {**selected, shot_id: option.get("id")}}, "stage": "editor"})
    return {"project": updated, "option": option}


@router.post("/projects/{project_id}/shots/{shot_id}/broll-assets")
def search_and_download_broll(project_id: str, shot_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    shot = _find_shot(project, shot_id)
    try:
        options = video_studio_broll.realize_broll_options(shot, project_id=project_id, per_page=8)
    except video_studio_broll.BrollAssetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    groups = _replace_shot(project, shot_id, {**shot, "broll_options": options})
    contract = _render_contract(project, groups)
    updated = _store().update_project(project_id, {"scene_groups": contract.get("scene_groups", groups), **contract, "stage": "editor"})
    return {"project": updated}


@router.post("/projects/{project_id}/prepare-editor-assets")
def prepare_editor_assets(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    if not project.get("scene_groups"):
        raise HTTPException(status_code=400, detail="请先生成分镜表")
    groups = []
    errors = []
    editor_state = project.get("editor_state") if isinstance(project.get("editor_state"), dict) else {}
    avatar_assets = editor_state.get("avatar_assets_by_shot") if isinstance(editor_state.get("avatar_assets_by_shot"), dict) else {}
    for group in project.get("scene_groups") or []:
        shots = []
        for shot in group.get("shots") or []:
            shot_id = str(shot.get("id") or "")
            if shot_id and avatar_assets.get(shot_id):
                shots.append(shot)
                continue
            options = shot.get("broll_options") if isinstance(shot.get("broll_options"), list) else []
            if any(item.get("asset_url") or item.get("asset_path") for item in options if isinstance(item, dict)):
                shots.append(shot)
                continue
            try:
                shots.append({**shot, "broll_options": video_studio_broll.realize_broll_options(shot, project_id=project_id, per_page=8)})
            except video_studio_broll.BrollAssetError as exc:
                errors.append(f"{shot.get('id')}: {exc}")
                shots.append(shot)
        groups.append({**group, "shots": shots})
    contract = _render_contract(project, groups)
    html_total = sum(1 for group in groups for shot in group.get("shots", []) if (shot.get("html_design") or {}).get("custom_html"))
    status = {"total_shots": sum(len(group.get("shots", [])) for group in groups), "mg_ready_count": html_total, "errors": errors, "html_generation": {"state": "ready" if html_total else "skipped", "message": "HTML/MG 由 Codex 本地生成"}}
    updated = _store().update_project(project_id, {"scene_groups": contract.get("scene_groups", groups), **contract, "editor_asset_status": status, "stage": "editor"})
    updated, preview_url = _create_preview(project_id, updated)
    return {"project": updated, "preview_url": preview_url, "asset_status": status}


@router.post("/projects/{project_id}/composition-preview")
def create_composition_preview(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    if not project.get("scene_groups"):
        raise HTTPException(status_code=400, detail="请先生成分镜表")
    updated, preview_url = _create_preview(project_id, project)
    return {"project": updated, "preview_url": preview_url}


@router.get("/projects/{project_id}/composition-preview.html")
def get_composition_preview(project_id: str):
    _project_or_404(project_id)
    path = storage.path_for_key(f"video_studio_previews/{project_id}/composition_preview.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Preview not found")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@router.post("/projects/{project_id}/final-video")
def generate_final_video(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    html_text = video_studio_planner.build_final_video_html(project)
    storage.save_bytes(f"video_studio_outputs/{project_id}/final_video.html", html_text.encode("utf-8"), "text/html; charset=utf-8")
    url = f"/api/v1/video-studio/projects/{project_id}/final-video.html"
    return {"project": _store().update_project(project_id, {"final_video_url": url, "stage": "editor"}), "final_video_url": url}


@router.get("/projects/{project_id}/final-video.html")
def get_final_video(project_id: str):
    _project_or_404(project_id)
    path = storage.path_for_key(f"video_studio_outputs/{project_id}/final_video.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Final video page not found")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@router.post("/projects/{project_id}/works")
def create_work(project_id: str) -> Dict[str, object]:
    project = _project_or_404(project_id)
    if not project.get("composition_preview_url"):
        project, _ = _create_preview(project_id, project)
    store = _works_store()
    works = store.list_works(project_id=project_id)
    matching_works = [item for item in works if work_matches_project_snapshot(item, project)]
    existing = next((item for item in matching_works if str(item.get("status") or "") in {"queued", "rendering"}), None)
    if not existing:
        existing = next(
            (
                item for item in matching_works
                if str(item.get("status") or "") == "success"
            ),
            None,
        )
    work = existing or store.create_work(project, preview_artifact_url=str(project.get("composition_preview_url") or ""))
    if work.get("status") != "failed":
        hyperframes_adapter.start_render_async(work, store, DATA_DIR)
        work = store.get_work(str(work["id"])) or work
    return {"work": work}


@router.get("/works")
def list_works(project_id: Optional[str] = None) -> Dict[str, object]:
    return {"works": _works_store().list_works(project_id=project_id)}


@router.get("/works/{work_id}")
def get_work(work_id: str) -> Dict[str, object]:
    work = _works_store().get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return {"work": work}


@router.post("/works/{work_id}/resume")
def resume_work(work_id: str) -> Dict[str, object]:
    store = _works_store()
    work = store.get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    if str(work.get("status") or "") in {"queued", "rendering"}:
        hyperframes_adapter.start_render_async(work, store, DATA_DIR)
    return {"work": store.get_work(work_id) or work}
