#!/usr/bin/env python3
from __future__ import annotations

import json
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from backend.api import settings as smart_slides_settings
from backend.api import video_studio
from backend.main import app
from backend.services import video_studio_broll, video_studio_captions, video_studio_planner, video_studio_works
from backend import main as smart_slides_main
from render import animated_overlay, ffmpeg_adapter


class LocalApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="smart-slides-api-")
        video_studio.set_data_dir_for_tests(self.temp_dir)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _ready_project(self, topic: str) -> dict:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": topic, "format": "long", "production_format": "broll_html", "target_duration_seconds": 60},
        ).json()["project"]
        for endpoint in (
            "generate-producer-analysis", "generate-requirement-document", "generate-creative-plan",
            "generate-director-document", "generate-storyboard", "composition-preview",
        ):
            response = self.client.post(f"/api/v1/video-studio/projects/{project['id']}/{endpoint}")
            self.assertEqual(response.status_code, 200, response.text)
        return self.client.get(f"/api/v1/video-studio/projects/{project['id']}").json()["project"]

    def test_runtime_env_loader_preserves_explicit_environment(self) -> None:
        env_file = Path(self.temp_dir) / "runtime.env"
        env_file.write_text("SMART_SLIDES_ENV_TEST=from-file\nSMART_SLIDES_ALREADY_SET=from-file\n", encoding="utf-8")
        old_test = os.environ.pop("SMART_SLIDES_ENV_TEST", None)
        old_set = os.environ.get("SMART_SLIDES_ALREADY_SET")
        os.environ["SMART_SLIDES_ALREADY_SET"] = "from-process"
        try:
            smart_slides_main._load_env_file(env_file)
            self.assertEqual(os.environ["SMART_SLIDES_ENV_TEST"], "from-file")
            self.assertEqual(os.environ["SMART_SLIDES_ALREADY_SET"], "from-process")
        finally:
            if old_test is None:
                os.environ.pop("SMART_SLIDES_ENV_TEST", None)
            else:
                os.environ["SMART_SLIDES_ENV_TEST"] = old_test
            if old_set is None:
                os.environ.pop("SMART_SLIDES_ALREADY_SET", None)
            else:
                os.environ["SMART_SLIDES_ALREADY_SET"] = old_set

    def test_settings_api_saves_private_env_without_returning_secret(self) -> None:
        old_home = os.environ.get("SMART_SLIDES_HOME")
        old_jogg = os.environ.pop("JOGG_API_KEY", None)
        old_pexels = os.environ.pop("PEXELS_API_KEY", None)
        os.environ["SMART_SLIDES_HOME"] = self.temp_dir
        try:
            with patch.object(smart_slides_settings, "_validate_jogg", return_value=(True, "Jogg API key 已验证。")), patch.object(
                smart_slides_settings, "_validate_pexels", return_value=(True, "Pexels API key 已验证。")
            ):
                response = self.client.put(
                    "/api/v1/settings",
                    json={"jogg_api_key": "jogg-secret", "pexels_api_key": "pexels-secret"},
                )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("jogg-secret", response.text)
            self.assertNotIn("pexels-secret", response.text)
            env_path = Path(self.temp_dir) / ".env"
            self.assertEqual(env_path.stat().st_mode & 0o777, 0o600)
            self.assertIn("JOGG_API_KEY=jogg-secret", env_path.read_text(encoding="utf-8"))
            status = self.client.get("/api/v1/settings")
            self.assertTrue(status.json()["jogg_api_key_configured"])
            self.assertEqual(set(status.json()), {"jogg_api_key_configured", "pexels_api_key_configured"})
            self.assertNotIn("jogg-secret", status.text)
            with patch.object(smart_slides_settings, "_validate_jogg", return_value=(True, "ok")):
                removed = self.client.put("/api/v1/settings", json={"clear_pexels_api_key": True})
            self.assertEqual(removed.status_code, 200, removed.text)
            self.assertNotIn("PEXELS_API_KEY", env_path.read_text(encoding="utf-8"))
        finally:
            if old_home is None:
                os.environ.pop("SMART_SLIDES_HOME", None)
            else:
                os.environ["SMART_SLIDES_HOME"] = old_home
            if old_jogg is not None:
                os.environ["JOGG_API_KEY"] = old_jogg
            if old_pexels is not None:
                os.environ["PEXELS_API_KEY"] = old_pexels

    def test_jogg_settings_validation_uses_whoami_with_api_key_header(self) -> None:
        response = httpx.Response(200, json={"code": 0, "data": {"id": "local-user"}})
        with patch.object(smart_slides_settings.httpx, "get", return_value=response) as request:
            valid, _message = smart_slides_settings._validate_jogg("test-jogg-key")
        self.assertTrue(valid)
        self.assertEqual(request.call_args.args[0], "https://api.jogg.ai/v2/user/whoami")
        self.assertEqual(request.call_args.kwargs["headers"], {"X-Api-Key": "test-jogg-key"})

    def test_jogg_settings_does_not_accept_ambiguous_success_or_overwrite_a_key(self) -> None:
        ambiguous = httpx.Response(200, json={"data": {"id": "missing-code"}})
        with patch.object(smart_slides_settings.httpx, "get", return_value=ambiguous):
            valid, _message = smart_slides_settings._validate_jogg("not-a-key")
        self.assertFalse(valid)

        old_home = os.environ.get("SMART_SLIDES_HOME")
        old_jogg = os.environ.pop("JOGG_API_KEY", None)
        os.environ["SMART_SLIDES_HOME"] = self.temp_dir
        env_path = Path(self.temp_dir) / ".env"
        env_path.write_text("JOGG_API_KEY=known-good-key\n", encoding="utf-8")
        try:
            with patch.object(smart_slides_settings, "_validate_jogg", return_value=(False, "Jogg 未接受此 API key。")):
                response = self.client.put("/api/v1/settings", json={"jogg_api_key": "not-a-key"})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(env_path.read_text(encoding="utf-8"), "JOGG_API_KEY=known-good-key\n")
        finally:
            if old_home is None:
                os.environ.pop("SMART_SLIDES_HOME", None)
            else:
                os.environ["SMART_SLIDES_HOME"] = old_home
            if old_jogg is not None:
                os.environ["JOGG_API_KEY"] = old_jogg

    def test_settings_page_only_exposes_managed_configuration_status(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "runtime" / "frontend" / "src" / "SettingsApp.tsx").read_text(encoding="utf-8")
        self.assertIn("JOGG_API_KEY", source)
        self.assertIn("PEXELS_API_KEY", source)
        self.assertNotIn("PIXABAY_API_KEY", source)
        self.assertIn("docs.jogg.ai/api-reference/v2/QuickStart/GettingStarted", source)
        self.assertIn("www.pexels.com/api/", source)

    def test_render_env_finds_macos_local_binaries_with_launchd_path(self) -> None:
        old_path = os.environ.get("PATH")
        old_tool_dir = os.environ.get("SMART_SLIDES_TOOL_DIR")
        tool_dir = Path(self.temp_dir) / "managed-tools"
        tool_dir.mkdir()
        try:
            os.environ["PATH"] = "/usr/bin:/bin"
            os.environ["SMART_SLIDES_TOOL_DIR"] = str(tool_dir)
            render_path = ffmpeg_adapter._render_env()["PATH"].split(os.pathsep)
            self.assertEqual(render_path[0], str(tool_dir))
            self.assertIn("/usr/local/bin", render_path)
            self.assertLess(render_path.index("/usr/local/bin"), render_path.index("/usr/bin"))
        finally:
            if old_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = old_path
            if old_tool_dir is None:
                os.environ.pop("SMART_SLIDES_TOOL_DIR", None)
            else:
                os.environ["SMART_SLIDES_TOOL_DIR"] = old_tool_dir

    def test_project_contract_and_planning_fallbacks(self) -> None:
        response = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "本地项目", "format": "long", "production_format": "broll_html", "target_duration_seconds": 600},
        )
        self.assertEqual(response.status_code, 200)
        project = response.json()["project"]
        self.assertEqual(project["project_schema_version"], "video_studio_project_v2")
        self.assertEqual(project["target_duration_seconds"], 600)
        project_id = project["id"]
        for endpoint in (
            "generate-producer-analysis",
            "generate-requirement-document",
            "generate-creative-plan",
            "generate-director-document",
            "generate-storyboard",
        ):
            result = self.client.post(f"/api/v1/video-studio/projects/{project_id}/{endpoint}")
            self.assertEqual(result.status_code, 200, result.text)
        project = result.json()["project"]
        self.assertTrue(project["scene_groups"])
        shots = [shot for group in project["scene_groups"] for shot in group["shots"]]
        self.assertEqual(sum(shot["duration_seconds"] for shot in shots), 600)
        self.assertEqual(project["render_manifest"]["version"], "video_studio_render_manifest_v1")
        self.assertEqual(video_studio_works.validate_project_for_work(project)["status"], "passed")

        avatar_url = "/data/video_studio_assets/avatar-opening.mp4"
        voice_url = "/data/video_studio_assets/voice-opening.m4a"
        patched = self.client.patch(
            f"/api/v1/video-studio/projects/{project_id}/editor-state",
            json={
                "avatar_enabled": False,
                "avatar_assets_by_shot": {shots[0]["id"]: {"asset_url": avatar_url, "muted": True}},
                "voice_assets_by_shot": {shots[0]["id"]: {"asset_url": voice_url}},
            },
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        preview = self.client.post(f"/api/v1/video-studio/projects/{project_id}/composition-preview")
        self.assertEqual(preview.status_code, 200, preview.text)
        document = self.client.get(f"/api/v1/video-studio/projects/{project_id}/composition-preview.html").text
        self.assertIn(f'<video src="{avatar_url}"', document)
        self.assertIn(f'<audio class="voice-audio" data-shot-id="{shots[0]["id"]}" src="{voice_url}"', document)
        self.assertIn("function activeVoice()", document)

    def test_planning_state_scales_codex_contracts_to_project_duration(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "Codex 规划", "format": "long", "production_format": "broll", "target_duration_seconds": 600},
        ).json()["project"]
        project_id = project["id"]
        payload = {
            "creative_plan": {
                "script": "第一段。第二段。",
                "scenes": [{
                    "id": "scene-1", "title": "规划场景",
                    "voiceover_units": [
                        {"id": "u1", "text": "第一段。", "duration_seconds": 5},
                        {"id": "u2", "text": "第二段。", "duration_seconds": 15},
                    ],
                }],
            },
            "scene_groups": [{
                "id": "group-1", "title": "分镜组", "shots": [
                    {"id": "shot-1", "title": "第一段", "narration": "第一段。", "duration_seconds": 5, "broll_prompt": "第一段真实画面"},
                    {"id": "shot-2", "title": "第二段", "narration": "第二段。", "duration_seconds": 15, "broll_prompt": "第二段真实画面"},
                ],
            }],
        }
        response = self.client.patch(f"/api/v1/video-studio/projects/{project_id}/planning-state", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()["project"]
        creative_units = [unit for scene in updated["creative_plan"]["scenes"] for unit in scene["voiceover_units"]]
        shots = [shot for group in updated["scene_groups"] for shot in group["shots"]]
        self.assertEqual(sum(unit["duration_seconds"] for unit in creative_units), 600)
        self.assertEqual(sum(shot["duration_seconds"] for shot in shots), 600)

    def test_sync_voice_timing_makes_jogg_audio_the_timeline_authority(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "语音对齐", "format": "long", "production_format": "broll", "target_duration_seconds": 60},
        ).json()["project"]
        groups = [{
            "id": "voice-group",
            "title": "语音镜头",
            "shots": [
                {
                    "id": "shot-voice-01", "title": "第一段", "narration": "第一段。", "duration_seconds": 15,
                    "broll_prompt": "factory automation", "scene_role": "full_broll", "visual_role": "broll_primary",
                    "broll_options": [{"id": "broll-01", "provider": "pexels", "provider_id": "one", "duration_seconds": 15, "asset_path": "/tmp/one.mp4"}],
                },
                {
                    "id": "shot-voice-02", "title": "第二段", "narration": "第二段。", "duration_seconds": 15,
                    "broll_prompt": "robot arm closeup", "scene_role": "full_broll", "visual_role": "broll_primary",
                    "broll_options": [{"id": "broll-02", "provider": "pixabay", "provider_id": "two", "duration_seconds": 15, "asset_path": "/tmp/two.mp4"}],
                },
            ],
        }]
        video_studio._store().update_project(
            project["id"],
            {
                "scene_groups": groups,
                "editor_state": {
                    "voice_assets_by_shot": {"shot-voice-01": {"path": "/tmp/one.m4a"}, "shot-voice-02": {"path": "/tmp/two.m4a"}},
                    "avatar_assets_by_shot": {"shot-voice-01": {"path": "/tmp/one-avatar.mp4", "muted": True}},
                    "selected_broll_by_shot": {"shot-voice-01": "broll-01", "shot-voice-02": "broll-02"},
                },
            },
        )

        response = self.client.post(
            f"/api/v1/video-studio/projects/{project['id']}/sync-voice-timing",
            json={"voice_durations_by_shot": {"shot-voice-01": 8.554, "shot-voice-02": 4.25}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()["project"]
        shots = {shot["id"]: shot for group in updated["scene_groups"] for shot in group["shots"]}
        self.assertAlmostEqual(shots["shot-voice-01"]["duration_seconds"], 8.554, places=3)
        self.assertAlmostEqual(shots["shot-voice-02"]["start_seconds"], 8.554, places=3)
        self.assertAlmostEqual(shots["shot-voice-02"]["end_seconds"], 12.804, places=3)
        self.assertEqual(shots["shot-voice-01"]["timing_source"], "jogg_voice_audio")
        self.assertEqual(shots["shot-voice-01"]["broll_options"][0]["id"], "broll-01")
        self.assertEqual(updated["editor_state"]["selected_broll_by_shot"]["shot-voice-02"], "broll-02")
        self.assertIn("shot-voice-01", updated["editor_state"]["voice_assets_by_shot"])
        self.assertIn("shot-voice-01", updated["editor_state"]["avatar_assets_by_shot"])
        self.assertAlmostEqual(updated["voice_timing"]["actual_duration_seconds"], 12.804, places=3)
        self.assertAlmostEqual(updated["render_manifest"]["scenes"][1]["start"], 8.554, places=3)
        self.assertAlmostEqual(updated["scene_plan_v2"][1]["timing"]["end_s"], 12.804, places=3)

        with patch.object(video_studio_broll, "search_broll_candidates", return_value=[]) as search:
            searched = self.client.get(f"/api/v1/video-studio/projects/{project['id']}/shots/shot-voice-01/broll-search")
        self.assertEqual(searched.status_code, 200, searched.text)
        self.assertAlmostEqual(search.call_args.kwargs["minimum_duration_seconds"], 8.554, places=3)

    def test_planning_state_preserves_and_validates_codex_bespoke_html(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "AI 科技热点", "format": "long", "production_format": "broll_html", "target_duration_seconds": 60},
        ).json()["project"]
        payload = {
            "scene_groups": [{
                "title": "资本流向",
                "shots": [{
                    "title": "基础设施重估",
                    "narration": "资本正在从应用层流向芯片和云计算基础设施。",
                    "duration_seconds": 8,
                    "broll_prompt": "AI data center infrastructure",
                    "scene_role": "broll_backdrop_overlay",
                    "mg_director": {
                        "version": "mg_director_v1",
                        "enabled": True,
                        "render_strategy": "llm_bespoke_html",
                        "visual_system": "causal",
                        "story_goal": "说明资本从应用层转向基础设施。",
                        "one_learning_point": "资本正在向算力基础设施集中。",
                        "main_visual_metaphor": "资本沿芯片和云计算路径向核心收紧。",
                        "visual_recipe": {
                            "composition_id": "causal_spine",
                            "hero_device_id": "semantic_icon_cluster",
                            "material_id": "luminous_data",
                            "motion_id": "directional_build_lock",
                            "originality_note": "把资本传导原创为向核心收紧的折返路径。",
                        },
                        "composition": {
                            "animation_type": "self_contained_html",
                            "layout": "directional_path",
                            "hero_frame": {"kind": "资本路径", "x": 100, "y": 150, "w": 1320, "h": 620},
                            "typography": {"headline_scale": "display", "headline_min_px": 72, "supporting_min_px": 30},
                            "visual_primitives": ["path", "node", "icon"],
                            "icon_semantics": ["云计算", "芯片", "资金"],
                            "motion_choreography": "路径先出现，节点依次点亮，最后锁定基础设施。",
                        },
                        "screen_slots": [
                            {"role": "headline", "text": "资本流向"},
                            {"role": "takeaway", "text": "基础设施成为重心"},
                        ],
                    },
                    "html_design": {
                        "custom_html": (
                            '<main class="ai-mg-layer" data-ai-generated-html="true"><svg viewBox="0 0 1920 1080">'
                            '<path data-ai-edit-block="capital-path" data-ai-edit-kind="visual" d="M180 520 L880 280 L1440 620" stroke="var(--mg-highlight)" stroke-width="28" fill="none"/>'
                            '<g data-ai-edit-block="icon-chip" data-ai-edit-kind="visual"><rect x="700" y="180" width="180" height="180" fill="var(--mg-primary)"/></g>'
                            '<g data-ai-edit-block="icon-cloud" data-ai-edit-kind="visual"><circle cx="1360" cy="620" r="90" fill="var(--mg-highlight)"/></g>'
                            '<text class="title" x="140" y="120" font-size="72">资本流向</text>'
                            '<text x="140" y="780" font-size="36">基础设施成为重心</text></svg></main>'
                        ),
                        "custom_css": ".ai-mg-layer{position:absolute;inset:0;color:var(--mg-ink)}.title{font-family:var(--mg-font-display);font-size:64px}",
                        "edit_schema": {"editable_text_selectors": [".title"]},
                    },
                }],
                "html_layers": [{"title": "资本流向", "shot_indexes": [1]}],
            }],
        }
        response = self.client.patch(f"/api/v1/video-studio/projects/{project['id']}/planning-state", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        shot = response.json()["project"]["scene_groups"][0]["shots"][0]
        self.assertEqual(shot["html_design"]["ai_html_generation"]["source"], "codex_local_bespoke_html")
        self.assertIn("position:absolute!important", shot["html_design"]["custom_css"])
        preview = self.client.post(f"/api/v1/video-studio/projects/{project['id']}/composition-preview")
        self.assertEqual(preview.status_code, 200, preview.text)
        document = self.client.get(f"/api/v1/video-studio/projects/{project['id']}/composition-preview.html").text
        self.assertIn("custom-html-frame", document)
        self.assertNotIn("MG视觉系统", document)

    def test_mg_html_patch_preserves_existing_broll(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "MG 局部刷新", "format": "long", "production_format": "broll_html", "target_duration_seconds": 60},
        ).json()["project"]
        shot = {
            "id": "shot-mg", "title": "局部刷新", "narration": "展示局部刷新。", "duration_seconds": 8.554,
            "scene_role": "broll_backdrop_overlay",
            "information_layer": {"enabled": True, "type": "metric", "keyword": "局部刷新"},
            "html_render_strategy": "llm_bespoke_html",
            "broll_options": [{"id": "stock", "provider": "pexels", "provider_id": "stock-1", "asset_path": "/tmp/stock.mp4"}],
        }
        video_studio._store().update_project(
            project["id"],
            {"scene_groups": [{"title": "MG", "shots": [shot]}], "voice_timing": {"source": "jogg_voice_audio"}},
        )
        response = self.client.patch(
            f"/api/v1/video-studio/projects/{project['id']}/mg-html",
            json={"html_design_by_shot": {"shot-mg": {
                "custom_html": (
                    '<main class="ai-mg-layer" data-ai-generated-html="true"><svg viewBox="0 0 1920 1080">'
                    '<path data-ai-edit-block="flow" data-ai-edit-kind="visual" d="M180 520H1500" stroke="#2dd4bf" stroke-width="64"/>'
                    '<circle data-ai-edit-block="node-a" data-ai-edit-kind="visual" cx="480" cy="520" r="120" fill="#f4c95d"/>'
                    '<circle data-ai-edit-block="node-b" data-ai-edit-kind="visual" cx="1320" cy="520" r="120" fill="#e7f0f7"/>'
                    '<text class="title" x="160" y="220" font-size="72">局部刷新</text></svg></main>'
                ),
                "custom_css": ".ai-mg-layer{position:absolute;inset:0}.title{fill:#fff}",
                "edit_schema": {"editable_text_selectors": [".title"]},
            }}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()["project"]["scene_groups"][0]["shots"][0]
        self.assertEqual(updated["broll_options"][0]["id"], "stock")
        self.assertIn("data-ai-generated-html", updated["html_design"]["custom_html"])
        self.assertAlmostEqual(updated["end_seconds"], 8.554, places=3)
        self.assertEqual(response.json()["updated_shot_ids"], ["shot-mg"])

    def test_prepare_editor_assets_excludes_already_selected_broll(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "素材去重", "format": "long", "production_format": "broll", "target_duration_seconds": 60},
        ).json()["project"]
        groups = [{"title": "素材", "shots": [
            {"id": "shot-1", "title": "一", "narration": "一。", "duration_seconds": 8, "broll_prompt": "factory exterior"},
            {"id": "shot-2", "title": "二", "narration": "二。", "duration_seconds": 8, "broll_prompt": "factory worker closeup"},
        ]}]
        video_studio._store().update_project(project["id"], {"scene_groups": groups})
        calls: list[tuple[str, set[tuple[str, str]]]] = []

        def fake_realize(shot: dict, **kwargs: object) -> list[dict]:
            calls.append((str(shot["id"]), set(kwargs.get("excluded_asset_keys") or set())))
            provider_id = "asset-1" if shot["id"] == "shot-1" else "asset-2"
            return [{
                "id": f"{shot['id']}-{provider_id}", "provider": "pexels", "provider_id": provider_id,
                "duration_seconds": 12, "asset_url": f"/data/{provider_id}.mp4", "asset_path": f"/tmp/{provider_id}.mp4",
            }]

        with patch.object(video_studio_broll, "realize_broll_options", side_effect=fake_realize):
            response = self.client.post(f"/api/v1/video-studio/projects/{project['id']}/prepare-editor-assets")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(calls[0][1], set())
        self.assertIn(("pexels", "asset-1"), calls[1][1])
        selected = response.json()["project"]["editor_state"]["selected_broll_by_shot"]
        self.assertEqual(selected, {"shot-1": "shot-1-asset-1", "shot-2": "shot-2-asset-2"})

    def test_refresh_broll_preserves_avatar_voice_and_local_uploads(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "素材刷新", "format": "long", "production_format": "broll", "target_duration_seconds": 60},
        ).json()["project"]
        project_id = project["id"]
        groups = [{"title": "素材", "shots": [
            {"id": "shot-avatar", "title": "开场", "narration": "开场。", "duration_seconds": 8, "broll_options": [{"id": "avatar", "asset_path": "/tmp/avatar.mp4"}]},
            {"id": "shot-stock", "title": "库存", "narration": "库存。", "duration_seconds": 8, "broll_options": [{"id": "stock", "provider": "pexels", "provider_id": "1", "asset_path": "/tmp/stock.mp4"}]},
            {"id": "shot-local", "title": "上传", "narration": "上传。", "duration_seconds": 8, "broll_options": [{"id": "local", "asset_path": "/tmp/local.mp4"}]},
        ]}]
        video_studio._store().update_project(project_id, {
            "scene_groups": groups,
            "editor_state": {
                "avatar_assets_by_shot": {"shot-avatar": {"asset_path": "/tmp/avatar.mp4"}},
                "voice_assets_by_shot": {"shot-avatar": {"asset_path": "/tmp/avatar.wav"}},
                "selected_broll_by_shot": {"shot-avatar": "avatar", "shot-stock": "stock", "shot-local": "local"},
            },
        })

        response = self.client.post(f"/api/v1/video-studio/projects/{project_id}/refresh-broll")
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()["project"]
        shots = {shot["id"]: shot for group in updated["scene_groups"] for shot in group["shots"]}
        self.assertEqual(response.json()["refreshed_shot_ids"], ["shot-stock"])
        self.assertEqual(shots["shot-avatar"]["broll_options"][0]["id"], "avatar")
        self.assertEqual(shots["shot-stock"]["broll_options"], [])
        self.assertEqual(shots["shot-local"]["broll_options"][0]["id"], "local")
        state = updated["editor_state"]
        self.assertIn("shot-avatar", state["avatar_assets_by_shot"])
        self.assertIn("shot-avatar", state["voice_assets_by_shot"])
        self.assertNotIn("shot-stock", state["selected_broll_by_shot"])
        self.assertEqual(state["selected_broll_by_shot"]["shot-local"], "local")

    def test_completed_work_is_reused_after_project_output_update(self) -> None:
        project = self._ready_project("Work 复用")
        project_id = project["id"]
        store = video_studio._works_store()
        work = store.create_work(project, preview_artifact_url=str(project.get("composition_preview_url") or ""))
        output = {"url": f"/data/video_studio_outputs/{project_id}/{work['id']}.mp4", "duration_seconds": 60}
        ffmpeg_adapter._update_project_output(project_id, work["id"], output, self.temp_dir)
        store.update_work(work["id"], {"status": "success", "output": output})
        resumed = self.client.post(f"/api/v1/video-studio/projects/{project_id}/works")
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["work"]["id"], work["id"])

    def test_stale_queued_work_is_not_reused_after_editor_change(self) -> None:
        project = self._ready_project("Queued work snapshot")
        project_id = project["id"]
        store = video_studio._works_store()
        stale = store.create_work(project, preview_artifact_url=str(project.get("composition_preview_url") or ""))
        response = self.client.patch(
            f"/api/v1/video-studio/projects/{project_id}/editor-state",
            json={"bgm_enabled": True, "bgm_volume": 0.42},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with patch.object(ffmpeg_adapter, "start_render_async"):
            created = self.client.post(f"/api/v1/video-studio/projects/{project_id}/works")
        self.assertEqual(created.status_code, 200, created.text)
        current = created.json()["work"]
        self.assertNotEqual(current["id"], stale["id"])
        self.assertTrue(current["render_snapshot"]["editor_state"]["bgm_enabled"])

    def test_stale_successful_work_is_not_reused_after_editor_change(self) -> None:
        project = self._ready_project("Successful work snapshot")
        project_id = project["id"]
        store = video_studio._works_store()
        stale = store.create_work(project, preview_artifact_url=str(project.get("composition_preview_url") or ""))
        response = self.client.patch(
            f"/api/v1/video-studio/projects/{project_id}/editor-state",
            json={"bgm_enabled": True, "bgm_volume": 0.42},
        )
        self.assertEqual(response.status_code, 200, response.text)
        store.update_work(stale["id"], {"status": "success", "output": {"url": "/data/stale.mp4"}})
        with patch.object(ffmpeg_adapter, "start_render_async"):
            created = self.client.post(f"/api/v1/video-studio/projects/{project_id}/works")
        self.assertEqual(created.status_code, 200, created.text)
        current = created.json()["work"]
        self.assertNotEqual(current["id"], stale["id"])
        self.assertTrue(current["render_snapshot"]["editor_state"]["bgm_enabled"])

    def test_work_snapshot_preserves_multi_shot_mg_clip(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "连续 MG", "format": "long", "production_format": "broll_html", "target_duration_seconds": 60},
        ).json()["project"]
        shots = [
            {
                "id": "shot-1", "title": "前半", "duration_seconds": 4.25, "start_seconds": 0.0, "end_seconds": 4.25,
                "scene_role": "broll_backdrop_overlay", "information_layer": {"enabled": True},
                "mg_director": {"version": "mg_director_v1", "enabled": True, "visual_system": "reveal"},
                "html_design": {"asset_id": "html:continuous", "custom_html": "<div class='ai-mg-layer'>连续动画</div>", "custom_css": ".ai-mg-layer{animation:move 10s linear}"},
            },
            {
                "id": "shot-2", "title": "后半", "duration_seconds": 5.75, "start_seconds": 4.25, "end_seconds": 10.0,
                "scene_role": "broll_backdrop_overlay", "information_layer": {"enabled": True}, "html_design": {},
                "mg_director": {"version": "mg_director_v1", "enabled": True, "visual_system": "reveal"},
            },
        ]
        clip = {
            "version": "mg_clip_v1", "id": "mg:continuous", "scene_id": "shot-1",
            "bound_shots": ["shot-1", "shot-2"], "html_asset_id": "html:continuous",
            "design_doc": {"version": "mg_design_doc_v1"},
        }
        updated = video_studio._store().update_project(
            project["id"],
            {
                "scene_groups": [{"id": "group-1", "shots": shots}],
                "design_plan": {"version": "video_studio_design_plan_v1", "mg_clips": [clip], "scenes": []},
                "render_manifest": {"version": "video_studio_render_manifest_v1", "mg_clips": [clip], "scenes": []},
            },
        )
        snapshot = video_studio_works.build_render_snapshot(updated)
        self.assertEqual(len(snapshot["mg_layer"]["mg_clips"]), 1)
        current = snapshot["mg_layer"]["mg_clips"][0]
        self.assertEqual(current["bound_shots"], ["shot-1", "shot-2"])
        self.assertEqual(current["shot_offsets"], {"shot-1": 0.0, "shot-2": 4.25})
        self.assertEqual(current["duration"], 10.0)
        self.assertEqual(snapshot["mg_layer"]["html_assets"][0]["bound_shots"], ["shot-1", "shot-2"])
        snapshot_shots = snapshot["scene_groups"][0]["shots"]
        self.assertEqual([shot["mg_clip_id"] for shot in snapshot_shots], ["mg:continuous", "mg:continuous"])
        self.assertEqual([shot["mg_clip_offset_seconds"] for shot in snapshot_shots], [0.0, 4.25])
        preview = video_studio_planner.build_composition_preview_html(snapshot)
        self.assertIn('data-shot-id="shot-2" data-mg-clip-offset="4.250"', preview)
        self.assertIn('sandbox="allow-same-origin"', preview)
        self.assertIn("seekMgScene(scene, 0, active && playing)", preview)

    def test_mg_clip_edit_schema_stores_only_allowed_sparse_overrides(self) -> None:
        project = self.client.post(
            "/api/v1/video-studio/projects",
            json={"topic": "语义编辑", "format": "long", "production_format": "broll_html", "target_duration_seconds": 60},
        ).json()["project"]
        shot = {
            "id": "shot-edit", "title": "语义层", "duration_seconds": 6,
            "scene_role": "broll_backdrop_overlay", "information_layer": {"enabled": True},
            "mg_director": {"version": "mg_director_v1", "enabled": True, "render_strategy": "llm_bespoke_html", "visual_system": "reveal"},
            "html_design": {
                "custom_html": "<div class='hero'>主体</div>", "custom_css": ".hero{color:#fff}",
                "edit_schema": {"editable_blocks": [{"id": "hero", "name": "主体", "kind": "text", "selector": ".hero", "allowed": ["text", "x", "color"]}]},
            },
        }
        clip = {"version": "mg_clip_v1", "id": "mg:edit", "scene_id": "shot-edit", "bound_shots": ["shot-edit"], "design_doc": {"version": "mg_design_doc_v1"}}
        video_studio._store().update_project(
            project["id"],
            {"scene_groups": [{"id": "group-edit", "shots": [shot]}], "design_plan": {"mg_clips": [clip], "scenes": []}, "render_manifest": {"mg_clips": [clip], "scenes": []}},
        )
        response = self.client.patch(
            f"/api/v1/video-studio/projects/{project['id']}/mg-clips/mg:edit/edit-schema",
            json={"overrides": {"hero": {"x": 22}}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["overrides"], {"hero": {"x": 22}})
        state = response.json()["project"]["editor_state"]
        self.assertEqual(state["html_block_overrides_by_clip"]["mg:edit"], {"hero": {"x": 22}})
        preview = self.client.get(f"/api/v1/video-studio/projects/{project['id']}/composition-preview.html")
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertIn("--smart-slides-edit-x:22px", preview.text)
        color = self.client.patch(
            f"/api/v1/video-studio/projects/{project['id']}/mg-clips/mg:edit/edit-schema",
            json={"overrides": {"hero": {"color": "#E85D3F"}}},
        )
        self.assertEqual(color.status_code, 200, color.text)
        self.assertEqual(color.json()["overrides"]["hero"]["color"], "var(--mg-primary)")
        invalid_color = self.client.patch(
            f"/api/v1/video-studio/projects/{project['id']}/mg-clips/mg:edit/edit-schema",
            json={"overrides": {"hero": {"color": "#22D3EE"}}},
        )
        self.assertEqual(invalid_color.status_code, 422, invalid_color.text)
        invalid = self.client.patch(
            f"/api/v1/video-studio/projects/{project['id']}/mg-clips/mg:edit/edit-schema",
            json={"overrides": {"hero": {"opacity": 0.5}}},
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)

    def test_existing_project_json_imports_without_id_or_schema_migration(self) -> None:
        fixture = {
            "id": "existing-project-id",
            "project_schema_version": "video_studio_project_v2",
            "topic": "已有项目",
            "format": "long",
            "production_format": "broll_html",
            "target_duration_seconds": 600,
            "stage": "editor",
            "scene_groups": [],
            "editor_state": {"selected_broll_by_shot": {}, "html_design_overrides": {}},
            "custom_source_field": {"keep": True},
        }
        response = self.client.post("/api/v1/video-studio/projects/import", json={"project": fixture})
        self.assertEqual(response.status_code, 200, response.text)
        project = response.json()["project"]
        self.assertEqual(project["id"], fixture["id"])
        self.assertEqual(project["project_schema_version"], fixture["project_schema_version"])
        self.assertEqual(project["custom_source_field"], fixture["custom_source_field"])
        fetched = self.client.get(f"/api/v1/video-studio/projects/{fixture['id']}").json()["project"]
        self.assertEqual(fetched["id"], fixture["id"])


class LocalFfmpegAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="smart-slides-render-"))
        self.data_dir = self.temp_dir / "data"
        self.work_dir = self.temp_dir / "work"
        self.data_dir.mkdir()
        self.work_dir.mkdir()
        self.audio = self.data_dir / "voice.wav"
        self.video = self.data_dir / "visual.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:a", "pcm_s16le", str(self.audio)],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x253238:s=320x180:r=24:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.video)],
            check=True,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_long_chinese_captions_are_split_into_timed_two_line_cues(self) -> None:
        text = (
            "人工智能正在从单点工具升级为能够规划任务、调用软件并检查结果的智能体，"
            "这会改变研发、客服和内容生产的工作方式。"
            "但模型幻觉、数据权限和推理成本仍然决定它能否真正进入核心业务流程。"
        )
        cues = video_studio_captions.build_caption_cues(text, 12.0)

        self.assertGreater(len(cues), 1)
        self.assertEqual(cues[0]["start_seconds"], 0.0)
        self.assertEqual(cues[-1]["end_seconds"], 12.0)
        self.assertEqual(
            video_studio_captions.normalize_caption_text("".join(cue["text"].replace("\n", "") for cue in cues)),
            video_studio_captions.normalize_caption_text(text),
        )
        for previous, cue in zip(cues, cues[1:]):
            self.assertEqual(previous["end_seconds"], cue["start_seconds"])
        for cue in cues:
            lines = cue["text"].splitlines()
            self.assertLessEqual(len(lines), 2)
            self.assertTrue(all(video_studio_captions.caption_display_width(line) <= 36 for line in lines))
            self.assertFalse(any(line.startswith(tuple("，。！？；、：,.!?;:")) for line in lines))

    def test_unpunctuated_caption_is_hard_split_without_overflow(self) -> None:
        text = "超长无标点字幕内容" * 18
        cues = video_studio_captions.build_caption_cues(text, 18.0)

        self.assertGreater(len(cues), 2)
        self.assertEqual("".join(cue["text"].replace("\n", "") for cue in cues), text)
        self.assertTrue(
            all(
                video_studio_captions.caption_display_width(line) <= 36
                for cue in cues
                for line in cue["text"].splitlines()
            )
        )

    def test_srt_writer_uses_multiple_cues_and_safe_1080p_style(self) -> None:
        text = "第一句先说明今天的核心变化，第二句解释这项变化为什么重要，第三句给出普通人可以立刻采取的行动。"
        output = self.work_dir / "captions.srt"
        ffmpeg_adapter._write_captions(
            [{"id": "shot-1", "narration": text}],
            [9.0],
            {},
            output,
        )

        srt = output.read_text(encoding="utf-8")
        self.assertGreater(srt.count(" --> "), 1)
        self.assertIn("00:00:09,000", srt)
        caption_filter = ffmpeg_adapter._caption_filter(output)
        self.assertIn("original_size=1920x1080", caption_filter)
        self.assertIn("FontSize=18", caption_filter)
        self.assertIn("MarginL=29", caption_filter)
        self.assertIn("MarginR=29", caption_filter)
        self.assertIn("MarginV=19", caption_filter)

    def test_composition_preview_uses_the_same_timed_caption_cues(self) -> None:
        text = "第一段字幕介绍核心事实，第二段字幕解释原因，第三段字幕给出结论和行动建议。"
        preview = video_studio_planner.build_composition_preview_html(
            {
                "topic": "字幕预览",
                "scene_groups": [{"shots": [{"id": "shot-1", "title": "正文", "narration": text, "duration_seconds": 8}]}],
                "editor_state": {"shot_scripts": {}, "voice_assets_by_shot": {}},
            }
        )

        self.assertIn("data-caption-cues=", preview)
        self.assertIn("function syncCaption(scene, localSeconds)", preview)
        self.assertIn("syncCaption(scenes[current], progress)", preview)
        self.assertIn("white-space: pre-line", preview)

    def test_renders_podcastor_snapshot_with_audio_for_all_and_avatar_for_one(self) -> None:
        snapshot = {
            "scene_groups": [{"shots": [
                {"id": "shot-1", "title": "开场", "narration": "开场介绍。", "duration_seconds": 1, "html_design": {"custom_html": "<h2>开场</h2>", "custom_css": "h2{color:#fff}"}, "broll_options": []},
                {"id": "shot-2", "title": "正文", "narration": "正文信息。", "duration_seconds": 1, "html_design": {}, "broll_options": [{"id": "b2", "asset_path": str(self.video)}]},
            ]}],
            "editor_state": {
                "voice_assets_by_shot": {"shot-1": {"path": str(self.audio)}, "shot-2": {"path": str(self.audio)}},
                "avatar_assets_by_shot": {"shot-1": {"path": str(self.video), "muted": True}},
                "selected_broll_by_shot": {"shot-2": "b2"},
                "html_design_overrides": {},
                "shot_scripts": {"shot-2": "编辑后的正文口播。"},
                "bgm_enabled": False,
            },
        }
        output = self.temp_dir / "result.mp4"
        old_skip = os.environ.get("SMART_SLIDES_SKIP_BROWSER_RASTERIZER")
        os.environ["SMART_SLIDES_SKIP_BROWSER_RASTERIZER"] = "1"
        try:
            manifest = ffmpeg_adapter.render_snapshot(snapshot, str(self.work_dir), str(self.data_dir), str(output))
        finally:
            if old_skip is None:
                os.environ.pop("SMART_SLIDES_SKIP_BROWSER_RASTERIZER", None)
            else:
                os.environ["SMART_SLIDES_SKIP_BROWSER_RASTERIZER"] = old_skip
        self.assertEqual([item["avatar_visual"] for item in manifest["shots"]], [True, False])
        self.assertTrue((self.work_dir / "narration.m4a").is_file())
        captions = (self.work_dir / "captions.srt").read_text(encoding="utf-8")
        self.assertIn("编辑后的正文口播", captions)
        self.assertNotIn("正文信息", captions)
        self.assertEqual(manifest["backend"], "local_ffmpeg")
        self.assertTrue(output.is_file())
        self.assertTrue((self.work_dir / "visuals.txt").is_file())
        self.assertFalse((self.work_dir / "visuals.mp4").exists())
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.work_dir / "narration.m4a"), "-f", "null", "-"], check=True)

    def test_local_ffmpeg_render_has_video_and_audio_without_external_composer(self) -> None:
        snapshot = {
            "scene_groups": [{"shots": [{
                "id": "shot-1", "title": "开场", "narration": "本地渲染。", "duration_seconds": 1,
                "html_design": {"custom_html": "<h2>本地渲染</h2>", "custom_css": "h2{color:#fff}"}, "broll_options": [],
            }]}],
            "editor_state": {
                "voice_assets_by_shot": {"shot-1": {"path": str(self.audio)}},
                "avatar_assets_by_shot": {"shot-1": {"path": str(self.video), "muted": True}},
                "selected_broll_by_shot": {}, "html_design_overrides": {}, "bgm_enabled": False,
            },
        }
        output = self.temp_dir / "ffmpeg-result.mp4"
        old_skip = os.environ.get("SMART_SLIDES_SKIP_BROWSER_RASTERIZER")
        os.environ["SMART_SLIDES_SKIP_BROWSER_RASTERIZER"] = "1"
        try:
            ffmpeg_adapter.render_snapshot(snapshot, str(self.work_dir), str(self.data_dir), str(output))
        finally:
            if old_skip is None:
                os.environ.pop("SMART_SLIDES_SKIP_BROWSER_RASTERIZER", None)
            else:
                os.environ["SMART_SLIDES_SKIP_BROWSER_RASTERIZER"] = old_skip
        self.assertGreater(output.stat().st_size, 1000)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(output)],
            check=True, capture_output=True, text=True, env=ffmpeg_adapter._render_env(),
        )
        stream_types = {item["codec_type"] for item in json.loads(probe.stdout)["streams"]}
        self.assertEqual(stream_types, {"audio", "video"})

    def test_blocks_render_when_jogg_voice_would_leave_a_silent_tail(self) -> None:
        snapshot = {
            "scene_groups": [{"shots": [{
                "id": "shot-short-voice", "title": "短旁白", "narration": "短旁白。", "duration_seconds": 3,
                "broll_options": [{"id": "broll", "asset_path": str(self.video)}],
            }]}],
            "editor_state": {
                "voice_assets_by_shot": {"shot-short-voice": {"path": str(self.audio)}},
                "selected_broll_by_shot": {"shot-short-voice": "broll"},
                "bgm_enabled": False,
            },
        }
        with self.assertRaisesRegex(RuntimeError, "sync the project to measured Jogg voice timing"):
            ffmpeg_adapter.render_snapshot(snapshot, str(self.work_dir), str(self.data_dir), str(self.temp_dir / "blocked.mp4"))

    def test_audio_renderer_never_pads_a_voice_track(self) -> None:
        with patch.object(ffmpeg_adapter.subprocess, "run") as run:
            ffmpeg_adapter._render_audio("/tmp/voice.m4a", 8.554, self.work_dir / "voice.m4a")
        command = run.call_args.args[0]
        self.assertNotIn("apad", command[command.index("-af") + 1])

    def test_alpha_renderer_freezes_animation_time(self) -> None:
        page = self.work_dir / "animated.html"
        page.write_text("<main style='animation:fade 1s linear'>MG</main>", encoding="utf-8")
        output = self.work_dir / "animated.webm"
        frame_times: list[float] = []
        sessions: list[object] = []
        commands: list[list[str]] = []

        class FakeSession:
            def __init__(self, **_: object) -> None:
                self.closed = False
                self.page_uri = ""
                sessions.append(self)

            def navigate(self, page_uri: str) -> None:
                self.page_uri = page_uri

            def evaluate(self, expression: str) -> object:
                marker = "const __SMART_SLIDES_FRAME_TIME_MS__ = "
                if marker in expression:
                    value = expression.split(marker, 1)[1].split(";", 1)[0]
                    frame_times.append(float(value))
                return None

            def screenshot_png(self) -> bytes:
                return b"fake-png-frame"

            def close(self) -> None:
                self.closed = True

        class FakeProcess:
            def __init__(self, command: list[str], **_: object) -> None:
                commands.append(command)
                self.stdin = io.BytesIO()
                self.stderr = io.BytesIO()
                self.returncode: int | None = None

            def wait(self, timeout: float | None = None) -> int:
                del timeout
                output.write_bytes(b"fake-alpha-webm")
                self.returncode = 0
                return 0

            def kill(self) -> None:
                self.returncode = -9

        animated_overlay.render_alpha_webm(
            page,
            duration=1,
            output_path=output,
            start_at_seconds=4.25,
            frame_rate=2,
            chrome_binary="/tmp/fake-chrome",
            session_factory=FakeSession,
            process_factory=FakeProcess,
        )

        self.assertEqual(animated_overlay._frame_times_ms(1, 2), [0.0, 500.0, 1000.0])
        self.assertEqual(frame_times, [4250.0, 4750.0, 5250.0])
        self.assertEqual(len(commands), 1)
        self.assertIn("libvpx-vp9", commands[0])
        self.assertIn("yuva420p", commands[0])
        self.assertIn("alpha_mode=1", commands[0])
        self.assertTrue(sessions[0].page_uri.startswith("file:"))
        self.assertTrue(sessions[0].closed)

    def test_chrome_capture_frame_times_include_cross_shot_offset(self) -> None:
        try:
            node = animated_overlay._node_binary(ffmpeg_adapter._render_env())
        except RuntimeError as exc:
            self.skipTest(str(exc))
        helper_uri = animated_overlay._CAPTURE_HELPER.resolve().as_uri()
        script = (
            f'import {{ frameTimes }} from {json.dumps(helper_uri)}; '
            'process.stdout.write(JSON.stringify(frameTimes(1, 2, 4250)));'
        )
        result = subprocess.run(
            [node, "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            env=ffmpeg_adapter._render_env(),
        )
        self.assertEqual(json.loads(result.stdout), [4250, 4750, 5250])

    def test_alpha_renderer_passes_start_offset_to_node_capture(self) -> None:
        page = self.work_dir / "node-offset.html"
        page.write_text("<main>MG</main>", encoding="utf-8")
        output = self.work_dir / "node-offset.webm"
        capture_commands: list[list[str]] = []

        class FakeEncoder:
            def __init__(self, _command: list[str], **_: object) -> None:
                self.stdin = io.BytesIO()
                self.stderr = io.BytesIO()
                self.returncode: int | None = None

            def wait(self, timeout: float | None = None) -> int:
                del timeout
                output.write_bytes(b"fake-alpha-webm")
                self.returncode = 0
                return 0

            def kill(self) -> None:
                self.returncode = -9

        class FakeCapture:
            def __init__(self, command: list[str], **_: object) -> None:
                capture_commands.append(command)
                self.stderr = io.BytesIO()
                self.returncode = 0

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                del timeout
                return b"", b""

            def poll(self) -> int:
                return self.returncode

        with patch.object(animated_overlay, "_node_binary", return_value="/tmp/node"):
            with patch.object(animated_overlay.subprocess, "Popen", side_effect=FakeCapture):
                animated_overlay.render_alpha_webm(
                    page,
                    duration=1,
                    output_path=output,
                    start_at_seconds=4.25,
                    frame_rate=2,
                    chrome_binary="/tmp/chrome",
                    process_factory=FakeEncoder,
                )
        self.assertEqual(len(capture_commands), 1)
        command = capture_commands[0]
        self.assertEqual(command[command.index("--start-ms") + 1], "4250.000000")

    def test_ffmpeg_overlay_passes_cross_shot_offset_to_alpha_renderer(self) -> None:
        shot = {
            "id": "shot-offset",
            "duration_seconds": 1,
            "scene_role": "broll_backdrop_overlay",
            "mg_clip_offset_seconds": 4.25,
            "html_design": {"custom_html": "<main>MG</main>", "custom_css": ""},
        }
        page = self.work_dir / "offset.html"
        page.write_text("<main>MG</main>", encoding="utf-8")
        output = self.work_dir / "offset.webm"
        with patch.object(ffmpeg_adapter, "_write_overlay_page", return_value=page):
            with patch.object(ffmpeg_adapter, "_chrome_binary", return_value="/tmp/chrome"):
                with patch.object(ffmpeg_adapter, "_binary", return_value="/tmp/ffmpeg"):
                    with patch.object(ffmpeg_adapter, "render_alpha_webm", return_value=str(output)) as render:
                        result = ffmpeg_adapter._render_overlay_webm({}, shot, self.work_dir, 1)
        self.assertEqual(result, str(output))
        self.assertEqual(render.call_args.kwargs["start_at_seconds"], 4.25)

    def test_rasterizes_animated_podcastor_mg_preview_in_local_chrome(self) -> None:
        shot = {
            "id": "shot-mg", "title": "核心指标", "narration": "核心指标正在上升。", "duration_seconds": 1,
            "scene_role": "broll_backdrop_overlay",
            "mg_clip_offset_seconds": 0.25,
            "information_layer": {"enabled": True, "overlay_type": "metric_callout", "keyword": "核心指标", "primary_fact": "增长 42%", "takeaway": "基础设施成为重心"},
            "mg_director": {"version": "mg_director_v1", "enabled": True, "visual_system": "metric", "main_visual_metaphor": "核心数字放大"},
            "html_design": {
                "custom_html": "<main class=\"ai-mg-layer\"><strong>42%</strong></main>",
                "custom_css": (
                    ".ai-mg-layer{position:absolute;inset:0;display:grid;place-items:center;background:transparent;"
                    "font-size:180px;color:#fff;animation:slide-in 1s linear both}"
                    "@keyframes slide-in{from{transform:translateX(-320px);opacity:0}to{transform:translateX(0);opacity:1}}"
                ),
            },
        }
        snapshot = {"topic": "编辑器叠层", "scene_groups": [{"shots": [shot]}], "editor_state": {"html_design_overrides": {}}}
        overlay = ffmpeg_adapter._render_overlay(snapshot, shot, self.work_dir, 1)
        self.assertTrue(overlay)
        self.assertEqual(Path(overlay).suffix, ".webm")
        self.assertGreater(Path(overlay).stat().st_size, 1000)
        page = (self.work_dir / "overlays" / "shot-mg.html").read_text(encoding="utf-8")
        self.assertNotIn("animation:none!important", page)
        self.assertIn('data-shot-id="shot-mg" data-mg-clip-offset="0.250"', page)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", overlay, "-f", "null", "-"],
            check=True,
            env=ffmpeg_adapter._render_env(),
        )

    def test_broll_video_is_not_looped_to_fill_a_scene(self) -> None:
        output = self.work_dir / "scene.mp4"
        with patch.object(ffmpeg_adapter.subprocess, "run") as run:
            ffmpeg_adapter._render_scene("/tmp/source-broll.mp4", "", 8, output)
        command = run.call_args.args[0]
        self.assertNotIn("-stream_loop", command)
        self.assertIn("tpad=stop_mode=clone:stop_duration=8.000", " ".join(command))


class NetworkBoundaryTest(unittest.TestCase):
    def test_broll_realization_rejects_used_and_short_candidates(self) -> None:
        candidates = [
            {"id": "reused", "provider": "pexels", "provider_id": "asset-1", "duration_seconds": 12},
            {"id": "short", "provider": "pexels", "provider_id": "asset-2", "duration_seconds": 4},
            {"id": "fresh", "provider": "pixabay", "provider_id": "asset-3", "duration_seconds": 12},
        ]
        downloaded: list[str] = []

        def fake_download(candidate: dict, **_: object) -> dict:
            downloaded.append(str(candidate["provider_id"]))
            return {**candidate, "asset_path": "/tmp/asset-3.mp4"}

        with patch.object(video_studio_broll, "search_broll_candidates", return_value=candidates):
            with patch.object(video_studio_broll, "_download_candidate", side_effect=fake_download):
                options = video_studio_broll.realize_broll_options(
                    {"id": "shot-3", "duration_seconds": 8, "broll_prompt": "factory worker"},
                    project_id="project",
                    excluded_asset_keys={("pexels", "asset-1")},
                )
        self.assertEqual(downloaded, ["asset-3"])
        self.assertEqual(options[0]["provider_id"], "asset-3")

    def test_broll_rejects_unapproved_provider_before_request(self) -> None:
        with self.assertRaises(video_studio_broll.BrollAssetError):
            video_studio_broll.download_broll_candidate(
                {"provider": "other", "provider_id": "1", "download_url": "https://example.com/video.mp4"},
                project_id="project",
                shot_id="shot",
            )

    def test_broll_rejects_unapproved_redirect_before_contacting_it(self) -> None:
        requested_hosts: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested_hosts.append(str(request.url.host))
            if request.url.host == "videos.pexels.com":
                return httpx.Response(302, headers={"location": "https://example.com/intermediate.mp4"})
            return httpx.Response(200, content=b"unexpected")

        with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
            with self.assertRaises(video_studio_broll.BrollAssetError):
                video_studio_broll._download_with_validated_redirects(
                    client,
                    "pexels",
                    "https://videos.pexels.com/video.mp4",
                )
        self.assertEqual(requested_hosts, ["videos.pexels.com"])

    def test_html_sanitizer_removes_remote_and_embedded_runtime_content(self) -> None:
        cleaned = ffmpeg_adapter._safe_html(
            '<script src="//cdn.example/x.js"></script><iframe src=https://example.com></iframe>'
            '<img src="//example.com/a.png" onload=fetch("//example.com")><div style="background:url(//example.com/x)">safe</div>'
        )
        self.assertNotIn("//example.com", cleaned)
        self.assertNotIn("<script", cleaned)
        self.assertNotIn("<iframe", cleaned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
