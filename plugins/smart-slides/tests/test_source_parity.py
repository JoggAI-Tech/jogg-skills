#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((PLUGIN_ROOT / "extraction-manifest.json").read_text(encoding="utf-8"))
SOURCE_ROOTS = {
    "podcastor": Path(os.getenv("PODCASTOR_SOURCE_REPO", MANIFEST["sources"]["podcastor"]["repository"])),
    "jogg": Path(os.getenv("JOGG_SOURCE_REPO", MANIFEST["sources"]["jogg"]["repository"])),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


for record in MANIFEST["files"]:
    source = SOURCE_ROOTS[record.get("source_repository", "podcastor")] / record["source"]
    expected = record.get("source_sha256")
    if expected and digest(source) != expected:
        raise SystemExit(f"source drift: {record['source']}")
    destination = PLUGIN_ROOT / record["destination"]
    destination_expected = record.get("destination_sha256")
    if destination_expected and digest(destination) != destination_expected:
        raise SystemExit(f"plugin adaptation drift: {record['destination']}")
    if record["mode"] == "snapshot":
        if source.read_bytes() != destination.read_bytes():
            raise SystemExit(f"snapshot parity failed: {record['destination']}")

with tempfile.NamedTemporaryFile(suffix=".py") as generated:
    subprocess.run(
        ["python3", str(PLUGIN_ROOT / "scripts/extract-planner.py"), str(SOURCE_ROOTS["podcastor"] / "backend/services/video_studio_planner.py"), generated.name],
        check=True,
    )
    if Path(generated.name).read_bytes() != (PLUGIN_ROOT / "runtime/backend/services/video_studio_planner.py").read_bytes():
        raise SystemExit("planner symbol extraction drift")

print("smart-slides source parity test passed")
