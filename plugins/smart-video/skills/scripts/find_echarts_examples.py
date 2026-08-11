#!/usr/bin/env python3
"""Search the Smart Video offline Apache ECharts example catalog."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _runtime_root() -> Path:
    configured = os.environ.get("SMARTVIDEO_RUNTIME_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    active = Path(
        os.environ.get("SMARTVIDEO_ACTIVE_FILE")
        or Path.home() / ".codex" / "smartvideo" / "active-runtime.json"
    ).expanduser()
    try:
        install_root = Path(json.loads(active.read_text(encoding="utf-8"))["install_root"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(
            "SmartVideo runtime is not active. Run the Smart Video bootstrap command first."
        ) from exc
    return install_root / "node_modules" / "@jogg-ai" / "smartvideo-runtime" / "runtime"


RUNTIME_ROOT = _runtime_root()
if not (RUNTIME_ROOT / "backend" / "services" / "video_studio_echarts_catalog.py").is_file():
    raise SystemExit(f"SmartVideo ECharts catalog is unavailable: {RUNTIME_ROOT}")
sys.path.insert(0, str(RUNTIME_ROOT))

from backend.services import video_studio_echarts_catalog  # noqa: E402


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _types(args: argparse.Namespace) -> int:
    categories = video_studio_echarts_catalog.catalog_summary()["categories"]
    if args.json:
        _print_json(categories)
        return 0
    print(f"{'TYPE':<16} {'COUNT':>5}  REPRESENTATIVE")
    for item in categories:
        print(f"{item['id']:<16} {item['count']:>5}  {item['representative_id']}")
    return 0


def _search(args: argparse.Namespace) -> int:
    try:
        results = video_studio_echarts_catalog.search_examples(
            " ".join(args.query), category=args.category, limit=args.limit
        )
    except video_studio_echarts_catalog.EchartsCatalogError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        _print_json(results)
        return 0
    if not results:
        print("No matching examples.", file=sys.stderr)
        return 1
    print(f"{'SCORE':>6}  {'READY':<5} {'TYPE':<14} {'ID':<38} TITLE")
    for item in results:
        categories = ",".join(item["categories"])
        ready = "yes" if item["runtime_supported"] else "no"
        print(f"{item['score']:>6.2f}  {ready:<5} {categories:<14.14} {item['id']:<38.38} {item['title']}")
    return 0


def _show(args: argparse.Namespace) -> int:
    try:
        record = video_studio_echarts_catalog.get_example(args.example_id)
    except video_studio_echarts_catalog.EchartsCatalogError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        _print_json(record)
        return 0
    for key in ("id", "title", "categories", "runtime_supported", "runtime_reason", "local_templates"):
        value = record[key]
        print(f"{key}: {', '.join(value) if isinstance(value, list) else value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    types = commands.add_parser("types")
    types.add_argument("--json", action="store_true")
    types.set_defaults(handler=_types)
    search = commands.add_parser("search")
    search.add_argument("query", nargs="+")
    search.add_argument("--type", dest="category")
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--json", action="store_true")
    search.set_defaults(handler=_search)
    show = commands.add_parser("show")
    show.add_argument("example_id")
    show.add_argument("--json", action="store_true")
    show.set_defaults(handler=_show)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
