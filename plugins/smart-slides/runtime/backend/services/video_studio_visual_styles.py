"""Executable visual style profiles for Smart Slides HTML/MG.

The extracted Podcastor contracts decide what a scene communicates and how it
is composed. This module adds the missing project-wide finish contract: a
small semantic palette, type roles, line weights, motion personality, and
bounded material overrides that remain stable across clips.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


VISUAL_STYLE_PROFILE_VERSION = "smart_slides_visual_style_profile_v1"
STYLE_VALIDATION_VERSION = "smart_slides_authored_style_validation_v1"
DEFAULT_VISUAL_STYLE_PROFILE_ID = "editorial_tech_news"

_SEMANTIC_COLOR_ROLES = {
    "ink",
    "muted",
    "surface",
    "surface-recessed",
    "primary",
    "highlight",
    "danger",
    "outline",
}
_ACCENT_COLOR_ROLES = {"primary", "highlight", "danger"}
_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_FUNCTIONAL_COLOR = re.compile(r"(?i)\b(?:rgb|rgba|hsl|hsla|lab|lch|oklab|oklch|color)\s*\([^)]*\)")
_SEMANTIC_COLOR_VARIABLE = re.compile(r"var\(\s*--mg-([a-z-]+)\s*(?:,[^)]+)?\)", re.I)
_FONT_DECLARATION = re.compile(r"(?is)font-family\s*:\s*([^;}]+)")
_NAMED_COLOR_DECLARATION = re.compile(
    r"(?is)(?:color|fill|stroke|background(?:-color)?|border(?:-[a-z]+)?-color)\s*:\s*"
    r"(black|white|red|green|blue|yellow|cyan|magenta|gray|grey|orange|purple|pink|lime|navy|teal|silver|maroon)\b"
)
_CSS_RULE = re.compile(r"(?is)([^{}]+)\{([^{}]*)\}")


_BASE_MATERIAL_OVERRIDES: dict[str, dict[str, Any]] = {
    "editorial_color_field": {
        "allow_color_field": True,
        "max_color_field_coverage_percent": 42,
        "glow_policy": "none",
        "texture": "hard_edge_cut",
    },
    "archival_paper": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 18,
        "glow_policy": "none",
        "texture": "restrained_print_grain",
    },
    "ink_wash": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 24,
        "glow_policy": "none",
        "texture": "masked_ink_edge",
    },
    "cinematic_gradient": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 24,
        "glow_policy": "none",
        "texture": "single_directional_light",
    },
    "satellite_scan": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 18,
        "glow_policy": "endpoint_only",
        "texture": "scan_band_and_coordinates",
    },
    "technical_blueprint": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 16,
        "glow_policy": "none",
        "texture": "measured_drafting_lines",
    },
    "film_grain": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 16,
        "glow_policy": "none",
        "texture": "low_opacity_film_grain",
    },
    "luminous_data": {
        "allow_color_field": False,
        "max_color_field_coverage_percent": 12,
        "glow_policy": "endpoint_only",
        "glow_max_blur_px": 12,
        "texture": "single_active_energy_edge",
    },
}


_VISUAL_STYLE_PROFILES: dict[str, dict[str, Any]] = {
    "editorial_tech_news": {
        "label": "Editorial Tech News",
        "description": "Charcoal editorial stage with print-like hierarchy, decisive warm signals, and restrained data color.",
        "palette": {
            "surface": "#111315",
            "surface_recessed": "#262A2D",
            "ink": "#F2EEE8",
            "muted": "#B6B4AE",
            "primary": "#E85D3F",
            "highlight": "#F1C453",
            "danger": "#D7435B",
            "outline": "#55585A",
        },
        "accent_budget_percent": 12,
        "typography": {
            "display": "Georgia, 'Songti SC', 'STSong', serif",
            "body": "Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif",
            "mono": "Menlo, Monaco, monospace",
            "personality": "editorial_serif_plus_neutral_sans",
        },
        "line_weight": {"hairline_px": 1, "structural_px": 4, "hero_px": 8},
        "glow_policy": "endpoint_only",
        "motion_personality": {
            "name": "decisive_editorial_build",
            "enter_ms": 480,
            "stagger_ms": 90,
            "settle_ms": 260,
            "easing": "cubic-bezier(.2,.75,.2,1)",
            "loop_policy": "none",
        },
    },
    "technical_blueprint": {
        "label": "Technical Blueprint",
        "description": "Light drafting field with measured geometry, dense ink, and one engineering signal color.",
        "palette": {
            "surface": "#F1F4F2",
            "surface_recessed": "#DCE3E2",
            "ink": "#172127",
            "muted": "#4F5E66",
            "primary": "#2A6F97",
            "highlight": "#C75133",
            "danger": "#B23A48",
            "outline": "#98A8AE",
        },
        "accent_budget_percent": 10,
        "typography": {
            "display": "Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif",
            "body": "Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif",
            "mono": "Menlo, Monaco, monospace",
            "personality": "engineering_grotesk_plus_mono_labels",
        },
        "line_weight": {"hairline_px": 1, "structural_px": 3, "hero_px": 7},
        "glow_policy": "none",
        "motion_personality": {
            "name": "measured_draw_and_lock",
            "enter_ms": 620,
            "stagger_ms": 110,
            "settle_ms": 300,
            "easing": "cubic-bezier(.22,.61,.36,1)",
            "loop_policy": "none",
        },
    },
    "archival_documentary": {
        "label": "Archival Documentary",
        "description": "Neutral film-black field with paper ink, oxblood evidence marks, and restrained archival texture.",
        "palette": {
            "surface": "#171613",
            "surface_recessed": "#2B2924",
            "ink": "#EEE7DA",
            "muted": "#B7AEA1",
            "primary": "#B94C45",
            "highlight": "#D2B36B",
            "danger": "#B33D52",
            "outline": "#5C574F",
        },
        "accent_budget_percent": 8,
        "typography": {
            "display": "Georgia, 'Songti SC', 'STSong', serif",
            "body": "Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif",
            "mono": "Menlo, Monaco, monospace",
            "personality": "documentary_serif_plus_archive_labels",
        },
        "line_weight": {"hairline_px": 1, "structural_px": 3, "hero_px": 6},
        "glow_policy": "none",
        "motion_personality": {
            "name": "evidence_reveal_and_hold",
            "enter_ms": 700,
            "stagger_ms": 140,
            "settle_ms": 340,
            "easing": "cubic-bezier(.25,.7,.25,1)",
            "loop_policy": "none",
        },
    },
}


def visual_style_profile_ids() -> list[str]:
    return list(_VISUAL_STYLE_PROFILES)


def _normalize_hex(value: Any) -> str:
    color = str(value or "").strip().upper()
    if re.fullmatch(r"#[0-9A-F]{3}", color):
        color = "#" + "".join(character * 2 for character in color[1:])
    if not re.fullmatch(r"#[0-9A-F]{6}", color):
        return ""
    return color


def _rgb(hex_color: str) -> tuple[int, int, int]:
    normalized = _normalize_hex(hex_color)
    if not normalized:
        raise ValueError(f"invalid profile color: {hex_color}")
    return tuple(int(normalized[index:index + 2], 16) for index in (1, 3, 5))


def _blend(start: str, end: str, end_weight: float) -> str:
    start_rgb = _rgb(start)
    end_rgb = _rgb(end)
    weight = min(max(float(end_weight), 0.0), 1.0)
    channels = [round(left * (1 - weight) + right * weight) for left, right in zip(start_rgb, end_rgb)]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _relative_luminance(hex_color: str) -> float:
    channels = []
    for channel in _rgb(hex_color):
        value = channel / 255.0
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _topic_profile_id(topic: str) -> str:
    text = str(topic or "").lower()
    if any(token in text for token in ("新闻", "热点", "快讯", "突发", "news", "headline", "weekly", "本周")):
        return "editorial_tech_news"
    if any(token in text for token in ("历史", "档案", "人物", "战争", "年代", "回顾", "archive", "history", "biography")):
        return "archival_documentary"
    if any(token in text for token in ("原理", "架构", "工程", "芯片", "模型", "算法", "算力", "技术", "science", "system", "architecture")):
        return "technical_blueprint"
    return DEFAULT_VISUAL_STYLE_PROFILE_ID


def _legacy_palette_override(value: Any) -> dict[str, str] | None:
    if not isinstance(value, list) or len(value) < 5:
        return None
    colors = [_normalize_hex(item) for item in value[:5]]
    if not all(colors):
        return None
    surface, ink, primary, highlight, danger = colors
    if contrast_ratio(ink, surface) < 4.5:
        return None
    return {
        "surface": surface,
        "surface_recessed": _blend(surface, ink, 0.12),
        "ink": ink,
        "muted": _blend(surface, ink, 0.70),
        "primary": primary,
        "highlight": highlight,
        "danger": danger,
        "outline": _blend(surface, ink, 0.28),
    }


def resolve_visual_style_profile(
    *,
    topic: str = "",
    requested: Any = None,
    legacy_palette: Any = None,
) -> dict[str, Any]:
    requested_id = str(requested.get("id") if isinstance(requested, dict) else requested or "").strip()
    profile_id = requested_id if requested_id in _VISUAL_STYLE_PROFILES else _topic_profile_id(topic)
    profile = deepcopy(_VISUAL_STYLE_PROFILES[profile_id])

    semantic_palette = requested.get("palette") if isinstance(requested, dict) and isinstance(requested.get("palette"), dict) else None
    if semantic_palette:
        normalized_semantic = {
            role: _normalize_hex(semantic_palette.get(role))
            for role in profile["palette"]
        }
        if all(normalized_semantic.values()) and contrast_ratio(normalized_semantic["ink"], normalized_semantic["surface"]) >= 4.5:
            profile["palette"] = normalized_semantic
    else:
        legacy_override = _legacy_palette_override(legacy_palette)
        if legacy_override:
            profile["palette"] = legacy_override

    profile.update(
        {
            "version": VISUAL_STYLE_PROFILE_VERSION,
            "id": profile_id,
            "selection": "explicit" if requested_id in _VISUAL_STYLE_PROFILES else "topic_inferred",
            "material_overrides": deepcopy(_BASE_MATERIAL_OVERRIDES),
        }
    )
    profile["contrast"] = {
        "ink_on_surface": contrast_ratio(profile["palette"]["ink"], profile["palette"]["surface"]),
        "muted_on_surface": contrast_ratio(profile["palette"]["muted"], profile["palette"]["surface"]),
    }
    return profile


def resolve_visual_style_profile_from_project(project: dict[str, Any]) -> dict[str, Any]:
    requirement = project.get("production_requirement_document") if isinstance(project.get("production_requirement_document"), dict) else {}
    direction = requirement.get("html_mg_direction") if isinstance(requirement.get("html_mg_direction"), dict) else {}
    director = project.get("director_document") if isinstance(project.get("director_document"), dict) else {}
    director_style = director.get("html_mg_style") if isinstance(director.get("html_mg_style"), dict) else {}
    requested = (
        direction.get("visual_style_profile")
        or direction.get("visual_style_profile_id")
        or director_style.get("visual_style_profile")
        or director_style.get("visual_style_profile_id")
        or project.get("visual_style_profile")
    )
    legacy_palette = direction.get("palette") or director_style.get("palette")
    return resolve_visual_style_profile(
        topic=str(project.get("topic") or ""),
        requested=requested,
        legacy_palette=legacy_palette,
    )


def canonical_palette(profile: dict[str, Any]) -> list[str]:
    palette = profile.get("palette") if isinstance(profile.get("palette"), dict) else {}
    return [str(palette.get(role) or "") for role in ("surface", "ink", "primary", "highlight", "danger")]


def material_style_override(profile: dict[str, Any], material_id: str) -> dict[str, Any]:
    overrides = profile.get("material_overrides") if isinstance(profile.get("material_overrides"), dict) else {}
    material = deepcopy(overrides.get(material_id) if isinstance(overrides.get(material_id), dict) else {})
    if not material:
        material = {
            "allow_color_field": False,
            "max_color_field_coverage_percent": int(profile.get("accent_budget_percent") or 10),
            "glow_policy": "none",
            "texture": "profile_default",
        }
    profile_glow = str(profile.get("glow_policy") or "none")
    if profile_glow == "none":
        material["glow_policy"] = "none"
    material["material_id"] = str(material_id or "profile_default")
    return material


def profile_css_variables(profile: dict[str, Any]) -> dict[str, str]:
    resolved = resolve_visual_style_profile(
        topic="",
        requested=profile if isinstance(profile, dict) else DEFAULT_VISUAL_STYLE_PROFILE_ID,
    )
    palette = resolved["palette"]
    typography = resolved["typography"]
    lines = resolved["line_weight"]
    motion = resolved["motion_personality"]
    return {
        "--mg-surface": palette["surface"],
        "--mg-surface-recessed": palette["surface_recessed"],
        "--mg-ink": palette["ink"],
        "--mg-muted": palette["muted"],
        "--mg-primary": palette["primary"],
        "--mg-highlight": palette["highlight"],
        "--mg-danger": palette["danger"],
        "--mg-outline": palette["outline"],
        "--mg-font-display": typography["display"],
        "--mg-font-body": typography["body"],
        "--mg-font-mono": typography["mono"],
        "--mg-line-hairline": f"{int(lines['hairline_px'])}px",
        "--mg-line-structural": f"{int(lines['structural_px'])}px",
        "--mg-line-hero": f"{int(lines['hero_px'])}px",
        "--mg-enter-ms": f"{int(motion['enter_ms'])}ms",
        "--mg-stagger-ms": f"{int(motion['stagger_ms'])}ms",
        "--mg-settle-ms": f"{int(motion['settle_ms'])}ms",
        "--mg-easing": str(motion["easing"]),
    }


def profile_css(profile: dict[str, Any]) -> str:
    resolved = resolve_visual_style_profile(topic="", requested=profile)
    variables = profile_css_variables(resolved)
    declarations = ";".join(f"{name}:{value}" for name, value in variables.items())
    return (
        f'.ai-mg-layer[data-mg-style-profile="{resolved["id"]}"],'
        f'.ai-mg-layer{{{declarations};color:var(--mg-ink);font-family:var(--mg-font-body)}}'
    )


def semantic_color_token(profile: dict[str, Any], value: Any) -> str:
    raw = str(value or "").strip()
    variable = re.fullmatch(
        r"var\(\s*--mg-(ink|muted|surface|surface-recessed|primary|highlight|danger|outline)\s*\)",
        raw,
        flags=re.I,
    )
    if variable:
        return f"var(--mg-{variable.group(1).lower()})"
    normalized = _normalize_hex(raw)
    if not normalized:
        return ""
    resolved = resolve_visual_style_profile(topic="", requested=profile)
    for role, color in resolved["palette"].items():
        if _normalize_hex(color) == normalized:
            return f"var(--mg-{role.replace('_', '-')})"
    return ""


def _hardcoded_colors(custom_html: str, custom_css: str) -> list[str]:
    source = f"{custom_html}\n{custom_css}"
    colors = [*(_HEX_COLOR.findall(source)), *(_FUNCTIONAL_COLOR.findall(source))]
    colors.extend(match.group(1) for match in _NAMED_COLOR_DECLARATION.finditer(source))
    return sorted({str(color).lower() for color in colors})


def _glow_errors(custom_css: str, glow_policy: str, max_blur_px: float) -> list[str]:
    errors: list[str] = []
    for selector, declarations in _CSS_RULE.findall(custom_css):
        if not re.search(r"(?i)(?:text-shadow|box-shadow|drop-shadow\s*\()", declarations):
            continue
        clean_selector = " ".join(selector.split())
        if glow_policy == "none":
            errors.append(f"风格档案禁止发光：{clean_selector[:80]}")
            continue
        endpoint_selector = ".mg-endpoint" in clean_selector or re.search(
            r"data-mg-emphasis\s*=\s*['\"]?endpoint", clean_selector, flags=re.I
        )
        if glow_policy == "endpoint_only" and not endpoint_selector:
            errors.append(f"发光只能用于 .mg-endpoint 或 data-mg-emphasis=endpoint：{clean_selector[:80]}")
        pixel_values = [float(value) for value in re.findall(r"(-?\d+(?:\.\d+)?)px", declarations, flags=re.I)]
        if pixel_values and max(abs(value) for value in pixel_values) > max_blur_px:
            errors.append(f"发光模糊半径超过 {max_blur_px:g}px")
    return errors


def validate_authored_style(
    custom_html: str,
    custom_css: str,
    profile: dict[str, Any],
    *,
    material_id: str,
) -> dict[str, Any]:
    resolved = resolve_visual_style_profile(topic="", requested=profile)
    material = material_style_override(resolved, material_id)
    errors: list[str] = []
    warnings: list[str] = []

    hardcoded = _hardcoded_colors(custom_html, custom_css)
    if hardcoded:
        errors.append("HTML/CSS 存在硬编码颜色，必须改用 --mg-* 语义变量：" + " / ".join(hardcoded[:8]))

    token_redefinitions = sorted(
        {
            match.group(1).lower()
            for match in re.finditer(
                r"(?i)--mg-(ink|muted|surface|surface-recessed|primary|highlight|danger|outline)\s*:",
                custom_css,
            )
        }
    )
    if token_redefinitions:
        errors.append("不得重定义项目颜色令牌：" + " / ".join(f"--mg-{role}" for role in token_redefinitions))

    all_mg_variables = [match.group(1).lower() for match in _SEMANTIC_COLOR_VARIABLE.finditer(f"{custom_html}\n{custom_css}")]
    referenced_roles = [role for role in all_mg_variables if role in _SEMANTIC_COLOR_ROLES]
    unknown_roles = sorted(
        {
            role
            for role in all_mg_variables
            if role not in _SEMANTIC_COLOR_ROLES
            and not role.startswith(("font-", "line-", "enter-", "stagger-", "settle-", "easing"))
        }
    )
    if unknown_roles:
        errors.append("使用了未声明的 MG 颜色变量：" + " / ".join(f"--mg-{role}" for role in unknown_roles))
    used_roles = sorted({role for role in referenced_roles if role in _SEMANTIC_COLOR_ROLES})
    if len(used_roles) > 5:
        errors.append("单个 clip 使用的语义颜色角色超过 5 个，无法形成清晰视觉层级")

    for declaration in _FONT_DECLARATION.findall(custom_css):
        if not re.fullmatch(r"\s*var\(\s*--mg-font-(?:display|body|mono)\s*\)\s*", declaration, flags=re.I):
            errors.append("font-family 必须使用 --mg-font-display、--mg-font-body 或 --mg-font-mono")
            break

    for selector, declarations in _CSS_RULE.findall(custom_css):
        if "ai-mg-layer" not in selector:
            continue
        if re.search(r"(?is)(?:background(?:-color)?|fill)\s*:\s*var\(\s*--mg-(?:primary|highlight|danger)\s*\)", declarations):
            errors.append("根画布不能使用强调色铺满；强调色面积必须服从 accent budget")
            break

    glow_policy = str(material.get("glow_policy") or resolved.get("glow_policy") or "none")
    errors.extend(_glow_errors(custom_css, glow_policy, float(material.get("glow_max_blur_px") or 10)))

    accent_references = sum(1 for role in referenced_roles if role in _ACCENT_COLOR_ROLES)
    if len(referenced_roles) >= 4 and accent_references / len(referenced_roles) > 0.5:
        warnings.append(
            f"强调色引用占比偏高；暂停帧中强调色面积应控制在 {int(resolved['accent_budget_percent'])}% 以内"
        )

    if resolved["contrast"]["ink_on_surface"] < 4.5 or resolved["contrast"]["muted_on_surface"] < 4.5:
        errors.append("风格档案的正文颜色对比度低于 WCAG AA 4.5:1")

    return {
        "version": STYLE_VALIDATION_VERSION,
        "ok": not errors,
        "profile_id": resolved["id"],
        "material_id": str(material_id or ""),
        "errors": errors,
        "warnings": warnings,
        "contrast": deepcopy(resolved["contrast"]),
        "metrics": {
            "semantic_color_roles": len(used_roles),
            "semantic_color_role_ids": used_roles,
            "hardcoded_colors": hardcoded,
            "accent_references": accent_references,
            "accent_budget_percent": int(resolved["accent_budget_percent"]),
            "glow_policy": glow_policy,
        },
    }
