#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from backend.api import video_studio
from backend.main import app
from backend.services import video_studio_broll, video_studio_works
from render import ffmpeg_adapter


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
        patched = self.client.patch(
            f"/api/v1/video-studio/projects/{project_id}/editor-state",
            json={"avatar_enabled": False, "avatar_assets_by_shot": {shots[0]["id"]: {"asset_url": avatar_url, "muted": True}}},
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        preview = self.client.post(f"/api/v1/video-studio/projects/{project_id}/composition-preview")
        self.assertEqual(preview.status_code, 200, preview.text)
        document = self.client.get(f"/api/v1/video-studio/projects/{project_id}/composition-preview.html").text
        self.assertIn(f'<video src="{avatar_url}"', document)

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

    def test_rasterizes_original_podcastor_mg_preview_in_local_chrome(self) -> None:
        shot = {
            "id": "shot-mg", "title": "核心指标", "narration": "核心指标正在上升。", "duration_seconds": 1,
            "scene_role": "broll_backdrop_overlay",
            "information_layer": {"enabled": True, "overlay_type": "metric_callout", "keyword": "核心指标", "primary_fact": "增长 42%", "takeaway": "基础设施成为重心"},
            "mg_director": {"enabled": True, "visual_system": "metric", "main_visual_metaphor": "核心数字放大"},
            "html_design": {"custom_html": "<main class=\"ai-mg-layer\"><strong>42%</strong></main>", "custom_css": ".ai-mg-layer{position:absolute;inset:0;display:grid;place-items:center;background:rgba(4,18,38,.75);font-size:180px;color:#fff}"},
        }
        snapshot = {"topic": "编辑器叠层", "scene_groups": [{"shots": [shot]}], "editor_state": {"html_design_overrides": {}}}
        overlay = ffmpeg_adapter._render_overlay_png(snapshot, shot, self.work_dir)
        self.assertTrue(overlay)
        self.assertGreater(Path(overlay).stat().st_size, 1000)
        subprocess.run(["ffmpeg", "-v", "error", "-i", overlay, "-f", "null", "-"], check=True, env=ffmpeg_adapter._render_env())


class NetworkBoundaryTest(unittest.TestCase):
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
