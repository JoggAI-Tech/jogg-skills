#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1] / "assets" / "semantic-mg-references"
MAPPING_PATH = ROOT / "scene-template-map.json"
CATALOG_VERSION = "semantic_scene_catalog"


def load_mapping() -> dict[str, Any]:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    if mapping.get("version") != CATALOG_VERSION:
        raise SystemExit(f"invalid MG reference mapping: {MAPPING_PATH}")
    return mapping


def emit(value: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                print("\t".join(str(item.get(key) or "") for key in ("scene_id", "category_id", "template_id", "presentation_form_id", "layout", "motion_profile")))
            else:
                print(item)
        return
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect bundled semantic scene hints")
    parser.add_argument("command", choices=("summary", "scenes", "candidates", "get"))
    parser.add_argument("value", nargs="?")
    parser.add_argument("--category")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    mapping = load_mapping()
    scenes = [item for item in mapping.get("mappings", []) if isinstance(item, dict)]

    if args.command == "summary":
        emit({
            "version": mapping.get("version"),
            "mode": mapping.get("mode"),
            "scene_count": mapping.get("scene_count"),
            "template_count": mapping.get("template_count"),
            "categories": sorted({str(item.get("category_id") or "") for item in scenes}),
        }, as_json=True)
        return 0

    if args.command == "scenes":
        selected = [
            {"scene_id": item.get("scene_id"), "category_id": item.get("category_id")}
            for item in scenes
            if not args.category or str(item.get("category_id") or "") == args.category
        ]
        emit(selected, as_json=args.json)
        return 0

    if not args.value:
        parser.error(f"{args.command} requires a scene_id or template_id")
    if args.command == "candidates":
        scene = next((item for item in scenes if str(item.get("scene_id") or "") == args.value), None)
        if scene is None:
            raise SystemExit(f"unknown scene_id: {args.value}")
        selected = [
            {"scene_id": scene["scene_id"], "category_id": scene["category_id"], **candidate}
            for candidate in scene.get("candidates", [])
            if isinstance(candidate, dict)
        ]
        emit(selected, as_json=args.json)
        return 0

    for scene in scenes:
        candidate = next(
            (item for item in scene.get("candidates", []) if isinstance(item, dict) and str(item.get("template_id") or "") == args.value),
            None,
        )
        if candidate is not None:
            emit({"scene_id": scene["scene_id"], "category_id": scene["category_id"], **candidate}, as_json=True)
            return 0
    raise SystemExit(f"unknown template_id: {args.value}")


if __name__ == "__main__":
    raise SystemExit(main())
