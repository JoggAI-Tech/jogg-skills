#!/usr/bin/env python3
"""Extract the deterministic Video Studio planner closure from Podcastor."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


ROOT_SYMBOLS = {
    "normalize_script_director",
    "normalize_director_document",
    "normalize_producer_analysis",
    "normalize_requirement_document",
    "normalize_creative_plan",
    "normalize_scene_groups",
    "build_render_contract_package",
    "build_composition_preview_html",
    "build_final_video_html",
    "is_current_bespoke_html_design",
    "is_current_bespoke_html_asset",
    # Keep the source project's local bespoke-HTML contract intact. The
    # standalone plugin supplies the HTML through Codex rather than making the
    # source project's external LLM call, but validation and application stay
    # source-derived.
    "_html_overlay_contract_for_clip",
    "_bespoke_html_asset_prompt",
    "_minify_custom_html_fragment",
    "_minify_custom_css",
    "_normalize_bespoke_html_font_sizes",
    "_validate_bespoke_html_asset",
    "_bespoke_html_canvas_guard_css",
    "_apply_bespoke_html_assets_to_scene_groups",
    "_sanitize_custom_html_fragment",
    "_sanitize_custom_css",
    "scale_scene_outline_durations",
    "fallback_script",
    "fallback_script_director",
    "fallback_director_document",
    "fallback_storyboard",
    "generate_storyboard_from_creative_plan",
}


def declared_names(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return [target.id for target in targets if isinstance(target, ast.Name)]
    return []


def apply_local_preview_adapters(output: str) -> str:
    """Reapply plugin-only preview behavior after source symbol extraction.

    This is the committed Smart Slides narration-preview adapter from
    47814a3. It is intentionally kept here rather than hand-editing the
    generated planner so source synchronization remains deterministic.
    """
    replacements = [
        (
            '    scripts = editor_state.get("shot_scripts") if isinstance(editor_state.get("shot_scripts"), dict) else {}\n'
            '    html_design_overrides = editor_state.get("html_design_overrides") if isinstance(editor_state.get("html_design_overrides"), dict) else {}\n',
            '    scripts = editor_state.get("shot_scripts") if isinstance(editor_state.get("shot_scripts"), dict) else {}\n'
            '    voice_assets = editor_state.get("voice_assets_by_shot") if isinstance(editor_state.get("voice_assets_by_shot"), dict) else {}\n'
            '    html_design_overrides = editor_state.get("html_design_overrides") if isinstance(editor_state.get("html_design_overrides"), dict) else {}\n',
        ),
        (
            '        media_markup = _player_media_markup(asset_url, str(option.get("title") or title))\n'
            '        fallback_markup = ""\n',
            '        media_markup = _player_media_markup(asset_url, str(option.get("title") or title))\n'
            '        voice_asset = voice_assets.get(shot_id) if isinstance(voice_assets.get(shot_id), dict) else {}\n'
            '        voice_url = str(voice_asset.get("asset_url") or voice_asset.get("url") or "")\n'
            '        voice_markup = (\n'
            '            f\'<audio class="voice-audio" data-shot-id="{html.escape(shot_id, quote=True)}" \'\n'
            '            f\'src="{html.escape(voice_url, quote=True)}" preload="auto"></audio>\'\n'
            '            if voice_url\n'
            '            else ""\n'
            '        )\n'
            '        fallback_markup = ""\n',
        ),
        (
            '              <div class="media">{media_markup}{fallback_markup}</div>\n'
            '              <div class="grade"></div>\n',
            '              <div class="media">{media_markup}{fallback_markup}</div>\n'
            '              {voice_markup}\n'
            '              <div class="grade"></div>\n',
        ),
        (
            '    function activeVideo() {{ return scenes[current]?.querySelector(\'video\'); }}\n'
            '    function syncVideos() {{\n'
            '      scenes.forEach((scene, index) => {{\n'
            '        const video = scene.querySelector(\'video\');\n'
            '        if (!video) return;\n'
            '        if (index !== current || !playing) video.pause();\n'
            '      }});\n'
            '      const video = activeVideo();\n'
            '      if (video && playing) video.play().catch(() => {{}});\n'
            '    }}\n',
            '    function activeVideo() {{ return scenes[current]?.querySelector(\'video\'); }}\n'
            '    function activeVoice() {{ return scenes[current]?.querySelector(\'audio.voice-audio\'); }}\n'
            '    function syncVideos() {{\n'
            '      scenes.forEach((scene, index) => {{\n'
            '        const video = scene.querySelector(\'video\');\n'
            '        const voice = scene.querySelector(\'audio.voice-audio\');\n'
            '        if (video && (index !== current || !playing)) video.pause();\n'
            '        if (voice && (index !== current || !playing)) {{\n'
            '          voice.pause();\n'
            '          voice.currentTime = 0;\n'
            '        }}\n'
            '      }});\n'
            '      const video = activeVideo();\n'
            '      if (video && playing) video.play().catch(() => {{}});\n'
            '      const voice = activeVoice();\n'
            '      if (voice && playing) voice.play().catch(() => {{}});\n'
            '    }}\n',
        ),
    ]
    for expected, replacement in replacements:
        if expected not in output:
            raise SystemExit("planner extraction no longer matches the local narration-preview adapter")
        output = output.replace(expected, replacement, 1)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    source_text = args.source.read_text(encoding="utf-8")
    source_lines = source_text.splitlines(keepends=True)
    tree = ast.parse(source_text)

    nodes: dict[str, ast.AST] = {}
    imports: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(node)
        for name in declared_names(node):
            nodes[name] = node

    missing = sorted(ROOT_SYMBOLS - nodes.keys())
    if missing:
        raise SystemExit(f"planner symbols missing from source: {', '.join(missing)}")

    selected: set[ast.AST] = set()
    pending = list(ROOT_SYMBOLS)
    visited: set[str] = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        node = nodes.get(name)
        if node is None:
            continue
        selected.add(node)
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load) and child.id in nodes:
                pending.append(child.id)

    used_names = {
        child.id
        for node in selected
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }
    selected_imports = []
    for node in imports:
        aliases = node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else []
        exposed = {alias.asname or alias.name.split(".")[0] for alias in aliases}
        if exposed & used_names:
            selected_imports.append(node)

    chunks = [
        '"""Extracted deterministic Video Studio planner code. Do not edit directly.\n\n'
        f"Source: {args.source}\n"
        'Generated by scripts/extract-planner.py.\n"""\n\n',
        "from __future__ import annotations\n\n",
    ]
    for node in sorted(selected_imports, key=lambda item: item.lineno):
        chunks.append("".join(source_lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n")
    chunks.append("\n")
    for node in sorted(selected, key=lambda item: item.lineno):
        chunks.append("".join(source_lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n\n\n")

    output = "".join(chunks).rstrip() + "\n"
    # The source names its historical cloud/HyperFrames composition fields.
    # The standalone plugin executes the same editor contract with local
    # Chrome rasterization and FFmpeg, so preserve the contract shape while
    # giving the local renderer an accurate identifier.
    output = (
        output
        .replace("HyperFrames 模板", "Podcastor 编辑器模板")
        .replace("hyperframes_overlay_v1", "podcastor_editor_overlay_v1")
        .replace("hyperframes_template_fallback", "podcastor_editor_template_fallback")
        .replace("hyperframes_template_primary", "podcastor_editor_template_primary")
    )
    output = apply_local_preview_adapters(output)
    forbidden = ("call_video_studio_llm", "api.siliconflow", "api.deepseek", "VIDEO_STUDIO_HTML_LLM")
    leaked = [token for token in forbidden if token in output]
    if leaked:
        raise SystemExit(f"extracted planner retained forbidden LLM symbols: {', '.join(leaked)}")

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
