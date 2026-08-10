from __future__ import annotations

import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "smart-video"
DEFAULT_NPM_ROOT = REPOSITORY_ROOT.parent / "golang" / "jogg-npm"
NPM_ROOT = Path(os.environ.get("JOGG_NPM_ROOT", DEFAULT_NPM_ROOT)).expanduser().resolve()
RUNTIME_ROOT = NPM_ROOT / "packages" / "smartvideo-runtime" / "runtime"

if not (RUNTIME_ROOT / "backend" / "main.py").is_file():
    raise RuntimeError(
        "SmartVideo runtime source is unavailable. Set JOGG_NPM_ROOT to the jogg-npm checkout."
    )

os.environ.setdefault("SMARTVIDEO_PLUGIN_ROOT", str(PLUGIN_ROOT))
os.environ.setdefault("SMARTVIDEO_SKILL_ROOT", str(PLUGIN_ROOT / "skills" / "smart-video"))
os.environ.setdefault("SMARTVIDEO_ASSETS_ROOT", str(PLUGIN_ROOT / "assets"))
sys.path.insert(0, str(RUNTIME_ROOT))
