#!/usr/bin/env python3
"""Local Jogg and smart-slides API fixture used by shell orchestration tests."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class Fixture:
    def __init__(self, avatar_status: str, request_log: Path):
        self.avatar_status = avatar_status
        self.request_log = request_log
        self.requests: list[dict[str, Any]] = []
        self.project: dict[str, Any] = {}
        self.work_snapshot: dict[str, Any] | None = None

    def record(self, method: str, path: str, headers: dict[str, str], body: str = "") -> None:
        self.requests.append(
            {
                "method": method,
                "path": path,
                "has_bearer": headers.get("Authorization") == "Bearer web-token",
                "has_api_key": headers.get("X-Api-Key") == "mock-openapi-key",
                "body": body,
            }
        )
        self.request_log.write_text(json.dumps(self.requests, ensure_ascii=True), encoding="utf-8")

    def response_project(self) -> dict[str, Any]:
        return {"project": self.project}

    def shots(self) -> list[dict[str, Any]]:
        return self.project.get("scene_groups", [{}])[0].get("shots", [])


def build_project() -> dict[str, Any]:
    return {
        "id": "project-1",
        "topic": "",
        "producer_analysis": None,
        "production_requirement_document": None,
        "creative_plan": None,
        "director_document": None,
        "scene_groups": [],
        "workflow_state": {"creative_plan": {"status": "pending"}},
        "editor_state": {"avatar_enabled": True, "selected_broll_by_shot": {}},
        "editor_asset_status": {"html_generation": {"state": "pending"}},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartSlidesFixture/2"

    @property
    def fixture(self) -> Fixture:
        return self.server.fixture  # type: ignore[attr-defined]

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def read_body(self) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length).decode("utf-8", errors="replace") if length else ""

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        self.fixture.record("GET", self.path, dict(self.headers))
        if path == "/health":
            self.send_json({"status": "ok", "service": "smart-slides"})
        elif path == "/openapi_key":
            self.send_json({"code": 0, "data": {"access_key": "mock-openapi-key"}})
        elif path == "/open/v2/voices":
            self.send_json({"code": 0, "data": {"voices": [{"voice_id": "zh-female-1"}]}})
        elif path == "/open/v2/avatars/public":
            self.send_json({"code": 0, "data": {"avatars": [{"id": 7}]}})
        elif path.startswith("/open/v2/avatar_video/"):
            video_id = path.rsplit("/", 1)[-1]
            status = self.fixture.avatar_status
            self.send_json({"code": 0, "data": {"video_id": video_id, "status": status, "video_url": f"http://{self.headers['Host']}/files/{video_id}.mp4" if status == "completed" else ""}})
        elif path.startswith("/files/"):
            body = b"fixture-jogg-mp4-with-audio"
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/v1/video-studio/projects":
            self.send_json({"projects": []})
        elif path == "/api/v1/video-studio/projects/project-1":
            self.send_json(self.fixture.response_project())
        elif path == "/api/v1/video-studio/works/work-1":
            work = {"id": "work-1", "status": "success", "output": {"url": "/data/final/video.mp4"}}
            if self.fixture.work_snapshot is not None:
                work["render_snapshot"] = self.fixture.work_snapshot
            self.send_json({"work": work})
        elif path == "/__requests":
            self.send_json({"requests": self.fixture.requests})
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self.read_body()
        self.fixture.record("POST", self.path, dict(self.headers), body)
        fixture = self.fixture
        if path == "/openapi_key/generate":
            self.send_json({"code": 0, "data": {"access_key": "mock-openapi-key"}})
        elif path == "/open/v2/create_video_from_avatar":
            payload = json.loads(body)
            creates = [item for item in fixture.requests if item["path"] == "/open/v2/create_video_from_avatar"]
            if payload.get("voice", {}).get("type") != "script" or payload.get("caption") is not False:
                self.send_json({"code": 1, "msg": "invalid avatar request"}, 400)
                return
            self.send_json({"code": 0, "data": {"video_id": f"avatar-{len(creates)}", "status": "pending"}})
        elif path == "/api/v1/video-studio/projects":
            payload = json.loads(body)
            fixture.project = build_project()
            fixture.project.update(topic=payload["topic"], target_duration_seconds=payload["target_duration_seconds"])
            self.send_json(fixture.response_project())
        elif path.endswith("/generate-producer-analysis"):
            fixture.project["producer_analysis"] = {"ok": True}
            self.send_json(fixture.response_project())
        elif path.endswith("/generate-requirement-document"):
            fixture.project["production_requirement_document"] = {"ok": True}
            self.send_json(fixture.response_project())
        elif path.endswith("/generate-creative-plan"):
            fixture.project["creative_plan"] = {"script": "script"}
            fixture.project["workflow_state"]["creative_plan"]["status"] = "ready"
            fixture.project["script"] = "script"
            self.send_json(fixture.response_project())
        elif path.endswith("/generate-director-document"):
            fixture.project["director_document"] = {"ok": True}
            self.send_json(fixture.response_project())
        elif path.endswith("/generate-storyboard"):
            fixture.project["scene_groups"] = [{"id": "group-1", "shots": [
                {"id": "shot-01", "title": "Opening", "narration": "opening", "duration_seconds": 6, "broll_options": []},
                {"id": "shot-02", "title": "Middle", "narration": "middle", "duration_seconds": 6, "broll_options": []},
                {"id": "shot-03", "title": "Ending", "narration": "ending", "duration_seconds": 6, "broll_options": []},
            ]}]
            self.send_json(fixture.response_project())
        elif path.endswith("/broll-assets"):
            shot_id = path.split("/shots/", 1)[1].split("/", 1)[0]
            for shot in fixture.shots():
                if shot["id"] == shot_id:
                    shot["broll_options"].append({"id": f"broll-{shot_id}", "asset_url": f"/data/assets/{shot_id}.mp4"})
            self.send_json(fixture.response_project())
        elif path.endswith("/prepare-editor-assets"):
            fixture.project["editor_asset_status"]["html_generation"]["state"] = "ready"
            self.send_json({**fixture.response_project(), "preview_url": "/preview/project-1"})
        elif path.endswith("/composition-preview"):
            fixture.project["composition_preview_url"] = "/preview/project-1"
            self.send_json({**fixture.response_project(), "preview_url": "/preview/project-1"})
        elif path.endswith("/projects/project-1/works"):
            fixture.work_snapshot = deepcopy(fixture.project)
            self.send_json({"work": {"id": "work-1", "status": "rendering"}})
        elif path == "/api/v1/video-studio/works/work-1/resume":
            self.send_json({"work": {"id": "work-1", "status": "rendering"}})
        else:
            self.send_json({"error": "not found"}, 404)

    def do_PATCH(self) -> None:
        body = self.read_body()
        self.fixture.record("PATCH", self.path, dict(self.headers), body)
        if self.path.endswith("/editor-state"):
            self.fixture.project["editor_state"].update(json.loads(body))
            self.send_json(self.fixture.response_project())
        elif self.path.endswith("/planning-state"):
            payload = json.loads(body)
            self.fixture.project.update(payload)
            if self.fixture.project.get("creative_plan") is not None:
                self.fixture.project["workflow_state"]["creative_plan"]["status"] = "ready"
            self.send_json(self.fixture.response_project())
        else:
            self.send_json({"error": "not found"}, 404)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--port-file", type=Path, required=True)
    parser.add_argument("--request-log", type=Path, required=True)
    parser.add_argument("--avatar-status", choices=["completed", "failed", "pending"], default="completed")
    args = parser.parse_args()
    fixture = Fixture(args.avatar_status, args.request_log)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.fixture = fixture  # type: ignore[attr-defined]
    args.port_file.write_text(str(server.server_port), encoding="utf-8")
    server.serve_forever()


if __name__ == "__main__":
    main()
