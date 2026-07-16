"""Local adapter for Podcastor's extracted bespoke HTML contract.

Podcastor's source implementation obtains HTML from its remote generation
step. Smart Slides receives the same HTML from the Codex-authored planning
file, then applies the source sanitizer, geometry guard, and validator before
the renderer sees it.
"""

from __future__ import annotations

import html
from copy import deepcopy
from typing import Any

from backend.services import video_studio_planner as planner


class BespokeHtmlContractError(ValueError):
    """A planning file did not provide a renderable director HTML layer."""


def restore_bespoke_html_from_planning_input(
    source_scene_groups: list[dict[str, Any]], normalized_scene_groups: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Restore authored HTML after Podcastor normalizes storyboard fields.

    The source planner generates bespoke HTML after normalization, so its
    normalizer intentionally does not retain a pre-existing `html_design`.
    Smart Slides receives that HTML in its planning file before normalization.
    When scaling splits an authored shot into multiple source-sized shots, the
    same director HTML is deliberately attached to each segment rather than
    replacing it with a generic template.
    """
    source_shots = [
        shot
        for group in source_scene_groups
        if isinstance(group, dict)
        for shot in group.get("shots") or []
        if isinstance(shot, dict)
    ]
    normalized_shots = [
        shot
        for group in normalized_scene_groups
        if isinstance(group, dict)
        for shot in group.get("shots") or []
        if isinstance(shot, dict)
    ]
    restored = deepcopy(normalized_scene_groups)
    restored_shots = [
        shot
        for group in restored
        for shot in group.get("shots") or []
        if isinstance(shot, dict)
    ]
    if not source_shots:
        return restored

    source_boundaries: list[float] = []
    elapsed = 0.0
    for source in source_shots:
        elapsed += max(0.5, float(source.get("duration_seconds") or 0.5))
        source_boundaries.append(elapsed)

    elapsed = 0.0
    source_index = 0
    for target in restored_shots:
        while source_index < len(source_boundaries) - 1 and elapsed >= source_boundaries[source_index] - 0.001:
            source_index += 1
        source = source_shots[source_index]
        source_design = source.get("html_design") if isinstance(source.get("html_design"), dict) else {}
        authored = {
            key: deepcopy(source_design[key])
            for key in ("custom_html", "custom_css", "layout_summary", "edit_schema")
            if key in source_design
        }
        if authored:
            target["html_design"] = {**(target.get("html_design") or {}), **authored}
        elapsed += max(0.5, float(target.get("duration_seconds") or 0.5))
    return restored


def prepare_bespoke_html_scene_groups(topic: str, scene_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and attach Codex-authored HTML using Podcastor source helpers."""
    assets_by_shot: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    for group in scene_groups:
        if not isinstance(group, dict):
            continue
        for shot in group.get("shots") or []:
            if not isinstance(shot, dict) or not planner._shot_uses_html(shot):
                continue
            strategy = str(shot.get("html_render_strategy") or "llm_bespoke_html")
            if strategy == "template":
                continue
            if strategy != "llm_bespoke_html":
                failures.append(f"{shot.get('id') or shot.get('title')}: unsupported HTML render strategy {strategy}")
                continue

            shot_id = str(shot.get("id") or "")
            html_design = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
            custom_html = planner._minify_custom_html_fragment(
                planner._sanitize_custom_html_fragment(str(html_design.get("custom_html") or ""))
            )
            custom_css = planner._minify_custom_css(
                planner._sanitize_custom_css(str(html_design.get("custom_css") or ""))
            )
            if not custom_html:
                failures.append(f"{shot_id or shot.get('title')}: llm_bespoke_html requires html_design.custom_html")
                continue

            clip = planner._mg_clip_for_shot(shot)
            overlay_contract = planner._html_overlay_contract_for_clip(topic, clip, [shot])
            visual_system = str(overlay_contract.get("visual_system") or "comparison")
            if "ai-mg-layer" not in custom_html or 'data-ai-generated-html="true"' not in custom_html:
                custom_html = planner._minify_custom_html_fragment(
                    f'<main class="ai-mg-layer ai-mg-layer--{html.escape(visual_system, quote=True)}" '
                    f'data-ai-generated-html="true" data-mg-clip-id="{html.escape(str(clip.get("id") or ""), quote=True)}">'
                    f"{custom_html}</main>"
                )
            custom_css = (
                planner._base_bespoke_html_css(visual_system)
                + "\n"
                + custom_css
                + "\n"
                + planner._bespoke_html_canvas_guard_css()
            )
            custom_html = planner._activate_bespoke_html_layers(custom_html)
            custom_html, custom_css = planner._normalize_bespoke_html_font_sizes(custom_html, custom_css)
            generation = html_design.get("ai_html_generation") if isinstance(html_design.get("ai_html_generation"), dict) else {}
            edit_schema = html_design.get("edit_schema") if isinstance(html_design.get("edit_schema"), dict) else generation.get("edit_schema")
            validation = planner._validate_bespoke_html_asset(
                custom_html=custom_html,
                custom_css=custom_css,
                edit_schema=edit_schema if isinstance(edit_schema, dict) else {},
                overlay_contract=overlay_contract,
            )
            if validation.get("errors"):
                failures.append(
                    f"{shot_id or shot.get('title')}: " + "；".join(str(item) for item in validation["errors"][:3])
                )
                continue

            mg_director = shot.get("mg_director") if isinstance(shot.get("mg_director"), dict) else {}
            assets_by_shot[shot_id] = {
                "version": "bespoke_html_asset_v1",
                "source": "codex_local_bespoke_html",
                "model": "codex",
                "clip_id": str(clip.get("id") or ""),
                "visual_system": visual_system,
                "overlay_contract": overlay_contract,
                "custom_html": custom_html,
                "custom_css": custom_css,
                "layout_summary": str(
                    html_design.get("layout_summary")
                    or mg_director.get("main_visual_metaphor")
                    or ""
                ),
                "edit_schema": edit_schema if isinstance(edit_schema, dict) else {},
                "validation": validation,
            }

    if failures:
        raise BespokeHtmlContractError("Bespoke HTML contract failed: " + " | ".join(failures))
    return planner._apply_bespoke_html_assets_to_scene_groups(deepcopy(scene_groups), assets_by_shot)
