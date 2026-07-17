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


def apply_local_caption_preview_adapters(output: str) -> str:
    """Keep the browser preview on the same bounded cues as final FFmpeg."""
    future_import = "from __future__ import annotations\n\n"
    if future_import not in output:
        raise SystemExit("planner extraction has no future import for caption adapter")
    output = output.replace(
        future_import,
        future_import + "from backend.services import video_studio_captions\n",
        1,
    )
    replacements = [
        (
            '        narration = str(scripts.get(shot_id) or shot.get("narration") or "")\n'
            '        option = _selected_broll_option_for_preview(shot, selected_broll)\n',
            '        narration = str(scripts.get(shot_id) or shot.get("narration") or "")\n'
            '        caption_cues = video_studio_captions.build_caption_cues(narration, durations[index - 1])\n'
            '        caption_data = html.escape(json.dumps(caption_cues, ensure_ascii=False, separators=(",", ":")), quote=True)\n'
            '        caption_text = str(caption_cues[0].get("text") or "") if caption_cues else ""\n'
            '        option = _selected_broll_option_for_preview(shot, selected_broll)\n',
        ),
        (
            '              <div class="caption">{html.escape(narration)}</div>\n',
            '              <div class="caption" data-caption-cues="{caption_data}">{html.escape(caption_text)}</div>\n',
        ),
        (
            '    .caption {{ position: absolute; left: 30px; right: 132px; bottom: 28px; padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,.58); font-size: clamp(14px, 1.3vw, 20px); line-height: 1.45; font-weight: 900; backdrop-filter: blur(8px); }}\n',
            '    .caption {{ position: absolute; left: 7.5%; right: 132px; bottom: 6.7%; max-height: 20%; overflow: hidden; padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,.58); font-size: clamp(14px, 1.3vw, 20px); line-height: 1.32; font-weight: 900; text-align: center; white-space: pre-line; overflow-wrap: normal; backdrop-filter: blur(8px); }}\n',
        ),
        (
            '    function activeVideo() {{ return scenes[current]?.querySelector(\'video\'); }}\n'
            '    function activeVoice() {{ return scenes[current]?.querySelector(\'audio.voice-audio\'); }}\n',
            '    function activeVideo() {{ return scenes[current]?.querySelector(\'video\'); }}\n'
            '    function activeVoice() {{ return scenes[current]?.querySelector(\'audio.voice-audio\'); }}\n'
            '    function syncCaption(scene, localSeconds) {{\n'
            '      const caption = scene?.querySelector(\'.caption\');\n'
            '      if (!caption) return;\n'
            '      let cues = [];\n'
            '      try {{ cues = JSON.parse(caption.dataset.captionCues || \'[]\'); }} catch (_) {{}}\n'
            '      const time = Math.max(0, Number(localSeconds) || 0);\n'
            '      const cue = cues.find((item, index) => time >= Number(item.start_seconds || 0) && (time < Number(item.end_seconds || 0) || index === cues.length - 1));\n'
            '      caption.textContent = cue?.text || \'\';\n'
            '      caption.hidden = !cue;\n'
            '    }}\n',
        ),
        (
            '        scene.classList.toggle(\'active\', active);\n'
            '        seekMgScene(scene, 0, active && playing);\n',
            '        scene.classList.toggle(\'active\', active);\n'
            '        seekMgScene(scene, 0, active && playing);\n'
            '        syncCaption(scene, 0);\n',
        ),
        (
            '      seekMgScene(scenes[current], progress, playing);\n'
            '      if (playing) startBgm(); else stopBgm();\n',
            '      seekMgScene(scenes[current], progress, playing);\n'
            '      syncCaption(scenes[current], progress);\n'
            '      if (playing) startBgm(); else stopBgm();\n',
        ),
        (
            '      progress += 0.2;\n'
            '      bar.style.width = Math.min(100, progress / duration * 100) + \'%\';\n',
            '      progress += 0.2;\n'
            '      syncCaption(scenes[current], progress);\n'
            '      bar.style.width = Math.min(100, progress / duration * 100) + \'%\';\n',
        ),
    ]
    for expected, replacement in replacements:
        if expected not in output:
            raise SystemExit("planner extraction no longer matches the local caption-preview adapter")
        output = output.replace(expected, replacement, 1)
    return output


def apply_local_mg_adapters(output: str) -> str:
    """Reapply local continuous-MG preview and CSS safety adapters."""
    replacements = [
        (
            'def _minify_custom_css(raw_css: str) -> str:\n'
            '    text = re.sub(r"(?is)/\\*.*?\\*/", "", raw_css or "")\n'
            '    text = re.sub(r"\\s+", " ", text)\n'
            '    text = re.sub(r"\\s*([{}:;,>+~])\\s*", r"\\1", text)\n'
            '    text = re.sub(r";}", "}", text)\n'
            '    return text.strip()\n',
            'def _minify_custom_css(raw_css: str) -> str:\n'
            '    text = re.sub(r"(?is)/\\*.*?\\*/", "", raw_css or "")\n'
            '    text = re.sub(r"\\s+", " ", text)\n'
            '    # CSS calc() requires whitespace around binary + and - operators. Keeping\n'
            '    # \'+\' out of the punctuation compactor also remains valid for sibling\n'
            '    # selectors while preserving authored animation delays.\n'
            '    text = re.sub(r"\\s*([{}:;,>~])\\s*", r"\\1", text)\n'
            '    text = re.sub(r";}", "}", text)\n'
            '    return text.strip()\n',
        ),
        (
            '        html_enabled = _shot_uses_html(shot)\n'
            '        html_overlay = ""\n'
            '        if html_enabled:\n'
            '            html_design = _html_design_for_preview(shot, html_design_overrides)\n'
            '            mg_clip = mg_clip_by_shot.get(shot_id) or _mg_clip_for_preview(shot, html_design)\n'
            '            html_layer_markup = _html_layer_markup_for_preview(shot, info, html_design, mg_clip)\n',
            '        html_enabled = _shot_uses_html(shot)\n'
            '        html_overlay = ""\n'
            '        mg_clip_offset = 0.0\n'
            '        if html_enabled:\n'
            '            html_design = _html_design_for_preview(shot, html_design_overrides)\n'
            '            mg_clip = mg_clip_by_shot.get(shot_id) or _mg_clip_for_preview(shot, html_design)\n'
            '            clip_offsets = mg_clip.get("shot_offsets") if isinstance(mg_clip.get("shot_offsets"), dict) else {}\n'
            '            mg_clip_offset = max(\n'
            '                0.0,\n'
            '                _positive_float(shot.get("mg_clip_offset_seconds"), _positive_float(clip_offsets.get(shot_id), 0.0)),\n'
            '            )\n'
            '            html_layer_markup = _html_layer_markup_for_preview(shot, info, html_design, mg_clip)\n',
        ),
        (
            '            <section class="scene{\' scene--html\' if html_enabled else \'\'}" data-index="{index}">\n',
            '            <section class="scene{\' scene--html\' if html_enabled else \'\'}" data-index="{index}" data-shot-id="{html.escape(shot_id, quote=True)}" data-mg-clip-offset="{mg_clip_offset:.3f}">\n',
        ),
        (
            '    function activeVideo() {{ return scenes[current]?.querySelector(\'video\'); }}\n'
            '    function activeVoice() {{ return scenes[current]?.querySelector(\'audio.voice-audio\'); }}\n'
            '    function syncVideos() {{\n',
            '    function activeVideo() {{ return scenes[current]?.querySelector(\'video\'); }}\n'
            '    function activeVoice() {{ return scenes[current]?.querySelector(\'audio.voice-audio\'); }}\n'
            '    function setMgAnimationTime(animation, timeMs, shouldPlay) {{\n'
            '      try {{\n'
            '        animation.pause();\n'
            '        animation.currentTime = timeMs;\n'
            '        const timing = animation.effect?.getComputedTiming?.();\n'
            '        const endTime = Number(timing?.endTime);\n'
            '        if (shouldPlay && (!Number.isFinite(endTime) || timeMs < endTime)) animation.play();\n'
            '      }} catch (_) {{}}\n'
            '    }}\n'
            '    function seekMgScene(scene, localSeconds, shouldPlay) {{\n'
            '      if (!scene) return;\n'
            '      const offsetSeconds = Math.max(0, Number(scene.dataset.mgClipOffset) || 0);\n'
            '      const timeMs = (offsetSeconds + Math.max(0, Number(localSeconds) || 0)) * 1000;\n'
            '      const overlay = scene.querySelector(\'.info-layer\');\n'
            '      for (const animation of overlay?.getAnimations({{subtree: true}}) || []) {{\n'
            '        setMgAnimationTime(animation, timeMs, shouldPlay);\n'
            '      }}\n'
            '      const frame = scene.querySelector(\'iframe.custom-html-frame\');\n'
            '      if (!frame) return;\n'
            '      try {{\n'
            '        const frameDocument = frame.contentDocument;\n'
            '        if (!frameDocument || frameDocument.readyState === \'loading\') {{\n'
            '          frame.addEventListener(\'load\', () => {{\n'
            '            const active = scenes[current] === scene;\n'
            '            seekMgScene(scene, active ? progress : 0, active && playing);\n'
            '          }}, {{once: true}});\n'
            '          return;\n'
            '        }}\n'
            '        for (const animation of frameDocument.getAnimations({{subtree: true}})) {{\n'
            '          setMgAnimationTime(animation, timeMs, shouldPlay);\n'
            '        }}\n'
            '      }} catch (_) {{}}\n'
            '    }}\n'
            '    function syncVideos() {{\n',
        ),
        (
            '      scenes.forEach((scene, i) => scene.classList.toggle(\'active\', i === current));\n',
            '      scenes.forEach((scene, i) => {{\n'
            '        const active = i === current;\n'
            '        scene.classList.toggle(\'active\', active);\n'
            '        seekMgScene(scene, 0, active && playing);\n'
            '      }});\n',
        ),
        (
            '      syncVideos();\n'
            '      if (playing) startBgm(); else stopBgm();\n',
            '      syncVideos();\n'
            '      seekMgScene(scenes[current], progress, playing);\n'
            '      if (playing) startBgm(); else stopBgm();\n',
        ),
        (
            '        \'sandbox="" \'\n',
            '        \'sandbox="allow-same-origin" \'\n',
        ),
    ]
    for expected, replacement in replacements:
        if expected not in output:
            raise SystemExit("planner extraction no longer matches the local continuous-MG adapter")
        output = output.replace(expected, replacement, 1)
    return output


def apply_local_visual_style_adapters(output: str) -> str:
    """Add the plugin-only executable style layer without changing source files."""
    future_import = "from __future__ import annotations\n\n"
    if future_import not in output:
        raise SystemExit("planner extraction has no future import for visual-style adapter")
    output = output.replace(
        future_import,
        future_import + "from backend.services import video_studio_visual_styles\n",
        1,
    )
    output += r'''

# Smart Slides local visual-style profile adapter. Podcastor owns the semantic
# scene and composition contracts; this layer supplies the missing project-wide
# palette, type, line, glow, and motion tokens.
def _smart_slides_visual_profile_from_director(
    topic: str,
    director_document: Dict[str, Any] | None,
    fallback_requested: Any = None,
) -> Dict[str, Any]:
    style = (
        director_document.get("html_mg_style")
        if isinstance((director_document or {}).get("html_mg_style"), dict)
        else {}
    )
    return video_studio_visual_styles.resolve_visual_style_profile(
        topic=topic,
        requested=style.get("visual_style_profile") or style.get("visual_style_profile_id") or fallback_requested,
        legacy_palette=style.get("palette"),
    )


_podcastor_normalize_director_document = normalize_director_document
def normalize_director_document(document: Dict[str, Any], topic: str, production_format: str) -> Dict[str, Any]:
    normalized = _podcastor_normalize_director_document(document, topic, production_format)
    if production_format != "broll_html":
        return normalized
    source_style = document.get("html_mg_style") if isinstance(document.get("html_mg_style"), dict) else {}
    profile = video_studio_visual_styles.resolve_visual_style_profile(
        topic=topic,
        requested=source_style.get("visual_style_profile") or source_style.get("visual_style_profile_id"),
        legacy_palette=source_style.get("palette"),
    )
    style = normalized.get("html_mg_style") if isinstance(normalized.get("html_mg_style"), dict) else {}
    normalized["html_mg_style"] = {
        **style,
        "animation_style": str(source_style.get("animation_style") or "编辑化信息图、强层级、克制动效"),
        "palette": video_studio_visual_styles.canonical_palette(profile),
        "typography": str(source_style.get("typography") or profile["typography"]["personality"]),
        "icon_style": str(source_style.get("icon_style") or "语义明确的大型图形，细线只作辅助"),
        "visual_style_profile_id": profile["id"],
        "visual_style_profile": profile,
    }
    return normalized


_podcastor_normalize_requirement_document = normalize_requirement_document
def normalize_requirement_document(document: Dict[str, Any], topic: str, production_format: str) -> Dict[str, Any]:
    normalized = _podcastor_normalize_requirement_document(document, topic, production_format)
    source_direction = document.get("html_mg_direction") if isinstance(document.get("html_mg_direction"), dict) else {}
    profile = video_studio_visual_styles.resolve_visual_style_profile(
        topic=topic,
        requested=source_direction.get("visual_style_profile") or source_direction.get("visual_style_profile_id"),
        legacy_palette=source_direction.get("palette"),
    )
    direction = normalized.get("html_mg_direction") if isinstance(normalized.get("html_mg_direction"), dict) else {}
    normalized["html_mg_direction"] = {
        **direction,
        "style": str(source_direction.get("style") or profile["description"]),
        "palette": video_studio_visual_styles.canonical_palette(profile),
        "typography": str(source_direction.get("typography") or profile["typography"]["personality"]),
        "icon_style": str(source_direction.get("icon_style") or "语义明确的大型图形，细线只作辅助"),
        "visual_style_profile_id": profile["id"],
        "visual_style_profile": profile,
    }
    return normalized


_podcastor_normalize_creative_plan = normalize_creative_plan
def normalize_creative_plan(
    plan: Dict[str, Any],
    topic: str,
    requirement_document: Dict[str, Any] | None,
    selected_option: Dict[str, Any] | None,
) -> Dict[str, Any]:
    normalized = _podcastor_normalize_creative_plan(plan, topic, requirement_document, selected_option)
    direction = (
        requirement_document.get("html_mg_direction")
        if isinstance((requirement_document or {}).get("html_mg_direction"), dict)
        else {}
    )
    profile = video_studio_visual_styles.resolve_visual_style_profile(
        topic=topic,
        requested=direction.get("visual_style_profile") or direction.get("visual_style_profile_id"),
        legacy_palette=direction.get("palette"),
    )
    for scene in normalized.get("scenes") or []:
        director = scene.get("mg_director") if isinstance(scene.get("mg_director"), dict) else {}
        if director.get("enabled"):
            director["visual_style_profile"] = deepcopy(profile)
    return normalized


def _smart_slides_requested_profile_from_groups(groups: List[Any]) -> Any:
    for group in groups:
        if not isinstance(group, dict):
            continue
        candidates = [
            shot.get("mg_director")
            for shot in group.get("shots") or []
            if isinstance(shot, dict) and isinstance(shot.get("mg_director"), dict)
        ]
        candidates.extend(
            layer.get("mg_director")
            for layer in group.get("html_layers") or []
            if isinstance(layer, dict) and isinstance(layer.get("mg_director"), dict)
        )
        for director in candidates:
            if director.get("visual_style_profile") or director.get("visual_style_profile_id"):
                return director.get("visual_style_profile") or director.get("visual_style_profile_id")
    return None


_podcastor_normalize_scene_groups = normalize_scene_groups
def normalize_scene_groups(
    groups: List[Any],
    production_format: str,
    director_document: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    normalized = _podcastor_normalize_scene_groups(groups, production_format, director_document)
    profile = _smart_slides_visual_profile_from_director(
        str((director_document or {}).get("title") or (director_document or {}).get("reference_style") or ""),
        director_document,
        _smart_slides_requested_profile_from_groups(groups),
    )
    for group in normalized:
        for shot in group.get("shots") or []:
            director = shot.get("mg_director") if isinstance(shot.get("mg_director"), dict) else {}
            if director.get("enabled"):
                director["visual_style_profile"] = deepcopy(profile)
        for layer in group.get("html_layers") or []:
            director = layer.get("mg_director") if isinstance(layer.get("mg_director"), dict) else {}
            if director.get("enabled"):
                director["visual_style_profile"] = deepcopy(profile)
    return normalized


_podcastor_html_overlay_contract_for_clip = _html_overlay_contract_for_clip
def _html_overlay_contract_for_clip(topic: str, clip: Dict[str, Any], bound_shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    contract = _podcastor_html_overlay_contract_for_clip(topic, clip, bound_shots)
    director = clip.get("mg_director") if isinstance(clip.get("mg_director"), dict) else {}
    profile = video_studio_visual_styles.resolve_visual_style_profile(
        topic=topic,
        requested=director.get("visual_style_profile"),
    )
    recipe = director.get("visual_recipe") if isinstance(director.get("visual_recipe"), dict) else {}
    material_id = str(recipe.get("material_id") or "editorial_color_field")
    contract["visual_style_profile"] = profile
    contract["style_tokens"] = {
        "css_variables": video_studio_visual_styles.profile_css_variables(profile),
        "accent_budget_percent": profile["accent_budget_percent"],
        "glow_policy": profile["glow_policy"],
    }
    contract["material_style_override"] = video_studio_visual_styles.material_style_override(profile, material_id)
    contract["visual_quality_rules"] = [
        *(contract.get("visual_quality_rules") or []),
        "no_undeclared_color_literals",
        "all_authored_colors_use_semantic_mg_css_variables",
        "accent_area_respects_project_profile_budget",
        "material_id_may_adjust_texture_but_never_replace_project_palette",
    ]
    contract["allowed_freedom"] = [
        "主视觉隐喻、SVG/HTML 构图、扫描/测量/路径动效可以自由设计；颜色和字体只能使用项目 style tokens",
        "工程边界、画布、安全区、文本来源、selector 和输出长度不能自由更改",
    ]
    return contract


_podcastor_design_plan_for_shots = _design_plan_for_shots
def _design_plan_for_shots(
    shots: List[Dict[str, Any]],
    *,
    topic: str,
    production_format: str,
    director_document: Dict[str, Any] | None,
    scene_groups: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    plan = _podcastor_design_plan_for_shots(
        shots,
        topic=topic,
        production_format=production_format,
        director_document=director_document,
        scene_groups=scene_groups,
    )
    first_profile = next(
        (
            shot.get("mg_director", {}).get("visual_style_profile")
            for shot in shots
            if isinstance(shot.get("mg_director"), dict)
            and isinstance(shot.get("mg_director", {}).get("visual_style_profile"), dict)
        ),
        None,
    )
    plan["visual_style_profile"] = _smart_slides_visual_profile_from_director(topic, director_document, first_profile)
    return plan


_podcastor_build_render_contract_package = build_render_contract_package
def build_render_contract_package(
    *,
    topic: str,
    production_format: str,
    script: str,
    director_document: Dict[str, Any] | None,
    scene_groups: List[Dict[str, Any]],
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Dict[str, Any]:
    package = _podcastor_build_render_contract_package(
        topic=topic,
        production_format=production_format,
        script=script,
        director_document=director_document,
        scene_groups=scene_groups,
        width=width,
        height=height,
    )
    design_plan = package.get("design_plan") if isinstance(package.get("design_plan"), dict) else {}
    profile = design_plan.get("visual_style_profile") if isinstance(design_plan.get("visual_style_profile"), dict) else video_studio_visual_styles.resolve_visual_style_profile(topic=topic)
    package["visual_style_profile"] = profile
    render_manifest = package.get("render_manifest") if isinstance(package.get("render_manifest"), dict) else {}
    render_manifest["visual_style_profile"] = profile
    return package


def _base_bespoke_html_css(visual_system: str) -> str:
    return """
html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: transparent; }
body { font-family: var(--mg-font-body, Arial, sans-serif); color: var(--mg-ink, #F8FAFC); }
.ai-mg-layer { position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; padding: 6.7% 5.4% 17% !important; overflow: hidden; background: transparent; --mg-primary:#E85D3F;--mg-ink:#F2EEE8;--mg-muted:#B6B4AE;--ai-accent:var(--mg-primary);--ai-ink:var(--mg-ink);--ai-muted:var(--mg-muted); }
.ai-mg-layer * { box-sizing: border-box; }
.ai-mg-layer b, .ai-mg-layer strong { color: var(--ai-ink); }
@media (max-width: 760px) { .ai-mg-layer { padding: 28px 24px 116px; } }
"""


_podcastor_bespoke_html_asset_prompt = _bespoke_html_asset_prompt
def _bespoke_html_asset_prompt(
    topic: str,
    clip: Dict[str, Any],
    bound_shots: List[Dict[str, Any]],
    *,
    compact_retry: bool = False,
    simple_retry: bool = False,
    composition_retry: bool = False,
    composition_feedback: str = "",
) -> str:
    prompt = _podcastor_bespoke_html_asset_prompt(
        topic,
        clip,
        bound_shots,
        compact_retry=compact_retry,
        simple_retry=simple_retry,
        composition_retry=composition_retry,
        composition_feedback=composition_feedback,
    )
    contract = _html_overlay_contract_for_clip(topic, clip, bound_shots)
    style_block = """
项目视觉风格合同（所有 clip 继承同一 profile，material_id 只能做受控质感覆盖）：
- visual_style_profile={profile}
- CSS variables={tokens}
- material override={material}
- authored HTML/CSS 禁止 hex、RGB/HSL 和 named color；所有颜色使用合同中的 var(--mg-*)。
- font-family 只能使用 var(--mg-font-display)、var(--mg-font-body) 或 var(--mg-font-mono)。
- 强调色总面积不得超过 accent_budget_percent；大面积承载面使用 surface/surface-recessed。
- glow 服从 material override；endpoint_only 只允许 .mg-endpoint 或 data-mg-emphasis=endpoint。
""".format(
        profile=json.dumps(contract.get("visual_style_profile") or {}, ensure_ascii=False),
        tokens=json.dumps((contract.get("style_tokens") or {}).get("css_variables") or {}, ensure_ascii=False),
        material=json.dumps(contract.get("material_style_override") or {}, ensure_ascii=False),
    )
    prompt = prompt.replace("\n工作方式：", "\n" + style_block + "\n工作方式：", 1)
    prompt = prompt.replace("color:white", "color:var(--mg-ink);font-family:var(--mg-font-body)")
    prompt = prompt.replace(
        "可以用 45%-70% 画面的实体纯色色场、档案纸块、墨迹遮罩或大型几何主体承载主视觉",
        "可以用 profile 的 surface/surface-recessed 构成大型承载面；primary/highlight/danger 只做少量焦点",
    )
    prompt = prompt.replace("资金流黄条", "资金流强调带").replace("主要主路径、黄条", "主要主路径、强调带")
    prompt = prompt.replace(
        "- custom_css 不得使用外链、@import、url()、JS。",
        "- custom_css 不得使用外链、@import、url()、JS。\n"
        "- custom_html/custom_css 不得写硬编码颜色；所有 fill/stroke/color/background/border/gradient stop 使用 style_tokens 的 var(--mg-*)。\n"
        "- font-family 只能引用 var(--mg-font-display)、var(--mg-font-body) 或 var(--mg-font-mono)。",
        1,
    )
    return prompt
'''
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
    output = apply_local_mg_adapters(output)
    output = apply_local_caption_preview_adapters(output)
    output = apply_local_visual_style_adapters(output)
    forbidden = ("call_video_studio_llm", "api.siliconflow", "api.deepseek", "VIDEO_STUDIO_HTML_LLM")
    leaked = [token for token in forbidden if token in output]
    if leaked:
        raise SystemExit(f"extracted planner retained forbidden LLM symbols: {', '.join(leaked)}")

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
