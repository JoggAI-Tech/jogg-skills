from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "smart-video"


def _managed_install_root() -> Path:
    configured = os.environ.get("SMARTVIDEO_INSTALL_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    active_file = Path(
        os.environ.get("SMARTVIDEO_ACTIVE_FILE")
        or Path.home() / ".codex" / "smartvideo" / "active-runtime.json"
    ).expanduser()
    try:
        payload = json.loads(active_file.read_text(encoding="utf-8"))
        install_root = Path(payload["install_root"]).expanduser().resolve()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "SmartVideo managed runtime is unavailable. Run the plugin bootstrap command first."
        ) from exc
    return install_root


INSTALL_ROOT = _managed_install_root()
PACKAGE_ROOT = INSTALL_ROOT / "node_modules" / "@joggai"
AGGREGATE_PACKAGE_ROOT = PACKAGE_ROOT / "smartvideo"
RUNTIME_PACKAGE_ROOT = PACKAGE_ROOT / "smartvideo-runtime"
RUNTIME_ROOT = RUNTIME_PACKAGE_ROOT / "runtime"

if not (RUNTIME_ROOT / "backend" / "main.py").is_file():
    raise RuntimeError(
        f"SmartVideo managed runtime package is incomplete: {RUNTIME_PACKAGE_ROOT}"
    )

os.environ.setdefault("SMARTVIDEO_PLUGIN_ROOT", str(PLUGIN_ROOT))
os.environ.setdefault("SMARTVIDEO_SKILL_ROOT", str(PLUGIN_ROOT / "skills" / "smart-video"))
os.environ.setdefault("SMARTVIDEO_ASSETS_ROOT", str(PLUGIN_ROOT / "assets"))
sys.path.insert(0, str(RUNTIME_ROOT))
