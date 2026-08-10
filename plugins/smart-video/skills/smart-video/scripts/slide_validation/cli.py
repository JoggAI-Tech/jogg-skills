"""CLI phase orchestration for deterministic Slide validation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .contracts import (
    ValidationError, fail, load_artifact_bytes, load_json,
    validate_manifest, validate_request,
)
from .echarts_data import validate_echarts, validate_echarts_actions
from .html_css import validate_html
from .render import validate_artifact_file, validate_render_report
from .runtime_readiness import attest_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("runtime-readiness", "pre-adapter", "pre-render", "post-render"))
    parser.add_argument("--request", type=Path)
    parser.add_argument("--visual-system", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--author", type=Path)
    parser.add_argument("--adapter-html", type=Path)
    parser.add_argument("--render-report", type=Path)
    parser.add_argument("--runtime-origin")
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    if args.phase == "runtime-readiness":
        if any((args.request, args.visual_system, args.manifest, args.author, args.adapter_html, args.render_report)):
            fail("runtime-readiness accepts only --runtime-origin")
        if args.runtime_origin is None:
            fail("unsupported_render_runtime: verified author routes and trusted runtime identity are unavailable")
        try:
            attest_runtime(args.runtime_origin)
        except ValidationError as exc:
            fail(f"unsupported_render_runtime: {exc}")
        return
    if args.runtime_origin is not None:
        fail("runtime origin is accepted only in runtime-readiness")
    if args.request is None or args.visual_system is None or args.manifest is None or args.author is None:
        fail(f"{args.phase} requires --request, --visual-system, --manifest, and --author")
    if args.phase == "pre-adapter" and (args.adapter_html is not None or args.render_report is not None):
        fail("pre-adapter does not accept adapter or render evidence")
    if args.phase in {"pre-render", "post-render"} and args.adapter_html is None:
        fail(f"{args.phase} requires --adapter-html")
    if args.phase == "post-render" and args.render_report is None:
        fail("post-render requires --render-report")
    if args.phase != "post-render" and args.render_report is not None:
        fail("render evidence is accepted only in post-render")
    visual_system_bytes = load_artifact_bytes(
        args.visual_system, "locked Visual System artifact"
    )
    request = validate_request(
        load_json(args.request, "request"),
        visual_system_artifact_bytes=visual_system_bytes,
    )
    manifest = validate_manifest(load_json(args.manifest, "manifest"), request, args.phase)
    author_artifact = manifest["artifacts"]["author"]
    validate_artifact_file(author_artifact, args.manifest, args.author, "author artifact")
    expected_author_media = "text/html" if request["render_mode"] == "html_svg" else "application/json"
    if author_artifact["media_type"] != expected_author_media:
        fail("author artifact media_type does not match render_mode")
    author_spec = None
    if request["render_mode"] == "html_svg":
        validate_html(args.author, request, manifest, adapter=False)
    else:
        author_spec = validate_echarts(load_json(args.author, "ECharts author artifact"), request)
        validate_echarts_actions(author_spec, manifest)
    if args.phase in {"pre-render", "post-render"}:
        adapter_artifact = manifest["artifacts"]["adapter"]
        if adapter_artifact["media_type"] != "text/html":
            fail("adapter artifact must be HTML")
        validate_artifact_file(adapter_artifact, args.manifest, args.adapter_html, "adapter artifact")
        validate_html(args.adapter_html, request, manifest, adapter=True, author_spec=author_spec)
    if args.phase == "post-render":
        validate_render_report(load_json(args.render_report, "render report"), args.render_report, request, manifest)


def main() -> int:
    try:
        run(parse_args())
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID")
    return 0
