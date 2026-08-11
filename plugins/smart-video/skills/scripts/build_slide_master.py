#!/usr/bin/env python3
"""Build one immutable UI UX Pro Max design MASTER for a Smart Video."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


SCHEMA_ID = "smart-video.slide-master-input.v1"
MASTER_SCHEMA_ID = "smart-video.slide-design-master.v1"
MASTER_VERSION = "1.0.0"
INVENTORY_SCHEMA_ID = "smart-video.private-dependency-inventory.v1"
EXPECTED_PRIVATE_FILES = {
    "scripts/search.py",
    "scripts/core.py",
    "scripts/design_system.py",
    "data/ui-reasoning.csv",
    "data/products.csv",
    "data/styles.csv",
    "data/colors.csv",
    "data/landing.csv",
    "data/typography.csv",
    "data/charts.csv",
}
CSV_HEADERS = {
    "data/ui-reasoning.csv": {"UI_Category", "Decision_Rules", "Anti_Patterns"},
    "data/products.csv": {"Product Type", "Keywords", "Primary Style Recommendation"},
    "data/styles.csv": {"Style Category", "Keywords", "Primary Colors", "Best For"},
    "data/colors.csv": {"Product Type", "Primary", "Background", "Foreground", "Accent"},
    "data/landing.csv": {"Pattern Name", "Keywords", "Section Order"},
    "data/typography.csv": {"Font Pairing Name", "Heading Font", "Body Font", "Mood/Style Keywords"},
    "data/charts.csv": {"Data Type", "Keywords", "Best Chart Type", "When to Use"},
}
REQUIRED_MASTER_SECTIONS = {
    "## Slide Visual System",
    "### Visual Language",
    "### Palette",
    "### Typography",
    "### Shape And Material",
    "### Motion Character",
}
SLIDE_SHOT_TYPES = {"avatar_html", "broll_html", "html_only"}
RENDER_MODES = {"html_svg", "echarts"}
SEMANTIC_TIMELINE_PHASES = {"establish", "relate", "focus", "resolve"}
RUNTIME_PROFILE_STYLE_MAP = {
    # Archive, print, and historically textured visual languages.
    "Retro-Futurism": "archival_documentary",
    "Storytelling-Driven": "archival_documentary",
    "Y2K Aesthetic": "archival_documentary",
    "Vaporwave": "archival_documentary",
    "Pixel Art": "archival_documentary",
    "E-Ink / Paper": "archival_documentary",
    "Editorial Grid / Magazine": "archival_documentary",
    "Vintage Analog / Retro Film": "archival_documentary",
    "Bauhaus (包豪斯)": "archival_documentary",
    "Academia (Scholarly Mobile)": "archival_documentary",
    "Sketch Hand-Drawn (Mobile)": "archival_documentary",
    # Data, engineering, spatial, and machine-interface visual languages.
    "3D & Hyperrealism": "technical_blueprint",
    "Feature-Rich Showcase": "technical_blueprint",
    "Interactive Product Demo": "technical_blueprint",
    "Data-Dense Dashboard": "technical_blueprint",
    "Heat Map & Heatmap Style": "technical_blueprint",
    "Executive Dashboard": "technical_blueprint",
    "Real-Time Monitoring": "technical_blueprint",
    "Drill-Down Analytics": "technical_blueprint",
    "Comparative Analysis Dashboard": "technical_blueprint",
    "Predictive Analytics": "technical_blueprint",
    "User Behavior Analytics": "technical_blueprint",
    "Financial Dashboard": "technical_blueprint",
    "Sales Intelligence Dashboard": "technical_blueprint",
    "Cyberpunk UI": "technical_blueprint",
    "AI-Native UI": "technical_blueprint",
    "Dimensional Layering": "technical_blueprint",
    "HUD / Sci-Fi FUI": "technical_blueprint",
    "Spatial UI (VisionOS)": "technical_blueprint",
    "Voice-First Multimodal": "technical_blueprint",
    "3D Product Preview": "technical_blueprint",
    "SaaS Mobile (High-Tech Boutique)": "technical_blueprint",
    "Terminal CLI (Mobile)": "technical_blueprint",
    "Cyberpunk Mobile HUD": "technical_blueprint",
    "Bitcoin DeFi (Mobile)": "technical_blueprint",
    "Enterprise SaaS (Mobile)": "technical_blueprint",
    # Contemporary editorial visual languages.
    "Minimalism & Swiss Style": "editorial_tech_news",
    "Neumorphism": "editorial_tech_news",
    "Glassmorphism": "editorial_tech_news",
    "Brutalism": "editorial_tech_news",
    "Vibrant & Block-based": "editorial_tech_news",
    "Dark Mode (OLED)": "editorial_tech_news",
    "Accessible & Ethical": "editorial_tech_news",
    "Claymorphism": "editorial_tech_news",
    "Aurora UI": "editorial_tech_news",
    "Flat Design": "editorial_tech_news",
    "Skeuomorphism": "editorial_tech_news",
    "Liquid Glass": "editorial_tech_news",
    "Motion-Driven": "editorial_tech_news",
    "Micro-interactions": "editorial_tech_news",
    "Inclusive Design": "editorial_tech_news",
    "Zero Interface": "editorial_tech_news",
    "Soft UI Evolution": "editorial_tech_news",
    "Hero-Centric Design": "editorial_tech_news",
    "Conversion-Optimized": "editorial_tech_news",
    "Minimal & Direct": "editorial_tech_news",
    "Social Proof-Focused": "editorial_tech_news",
    "Trust & Authority": "editorial_tech_news",
    "Neubrutalism": "editorial_tech_news",
    "Bento Box Grid": "editorial_tech_news",
    "Organic Biophilic": "editorial_tech_news",
    "Memphis Design": "editorial_tech_news",
    "Exaggerated Minimalism": "editorial_tech_news",
    "Kinetic Typography": "editorial_tech_news",
    "Parallax Storytelling": "editorial_tech_news",
    "Swiss Modernism 2.0": "editorial_tech_news",
    "Bento Grids": "editorial_tech_news",
    "Gen Z Chaos / Maximalism": "editorial_tech_news",
    "Biomimetic / Organic 2.0": "editorial_tech_news",
    "Anti-Polish / Raw Aesthetic": "editorial_tech_news",
    "Tactile Digital / Deformable UI": "editorial_tech_news",
    "Nature Distilled": "editorial_tech_news",
    "Interactive Cursor Design": "editorial_tech_news",
    "Gradient Mesh / Aurora Evolved": "editorial_tech_news",
    "Chromatic Aberration / RGB Split": "editorial_tech_news",
    "Minimalist Monochrome": "editorial_tech_news",
    "Modern Dark (Cinema Mobile)": "editorial_tech_news",
    "Kinetic Brutalism (Mobile)": "editorial_tech_news",
    "Flat Design Mobile (Touch-First)": "editorial_tech_news",
    "Material You (MD3 Mobile)": "editorial_tech_news",
    "Neo Brutalism (Mobile)": "editorial_tech_news",
    "Bold Typography (Mobile Poster)": "editorial_tech_news",
    "Claymorphism (Mobile)": "editorial_tech_news",
    "Neumorphism (Mobile)": "editorial_tech_news",
}


class BuildError(Exception):
    pass


def fail(message: str) -> None:
    raise BuildError(message)


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        fail(f"MASTER input cannot be canonicalized: {exc}")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path, label: str) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {label}: {exc}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{label} is not valid JSON: {exc}")


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{path} must be a non-empty string")
    return value.strip()


def require_string_list(value: Any, path: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "an array" if allow_empty else "a non-empty array"
        fail(f"{path} must be {qualifier}")
    return [require_string(item, f"{path}[{index}]") for index, item in enumerate(value)]


def require_positive_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"{path} must be a finite number")
    if value <= 0:
        fail(f"{path} must be greater than zero")
    return float(value)


def require_fields(value: dict[str, Any], required: set[str], path: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        fail(f"{path} is missing required field {missing[0]}")


def require_ratio(value: Any, path: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or value > 1
    ):
        fail(f"{path} must be a finite number from 0 to 1")
    return float(value)


def validate_semantic_timeline(value: Any, path: str, narration: str) -> None:
    timeline = require_object(value, path)
    expected_fields = {"basis", "cues", "stable_hold_start_ratio"}
    if set(timeline) != expected_fields:
        missing = sorted(expected_fields - set(timeline))
        unknown = sorted(set(timeline) - expected_fields)
        if missing:
            fail(f"{path} is missing required field {missing[0]}")
        fail(f"{path} contains unknown field {unknown[0]}")
    if timeline["basis"] != "narration_relative":
        fail(f"{path}.basis must be narration_relative")
    cues = timeline["cues"]
    if not isinstance(cues, list) or not cues:
        fail(f"{path}.cues must be a non-empty array")

    cursor = 0
    previous_ratio = -1.0
    cue_ids: set[str] = set()
    for index, raw_cue in enumerate(cues):
        cue_path = f"{path}.cues[{index}]"
        cue = require_object(raw_cue, cue_path)
        cue_fields = {"cue_id", "narration_anchor", "visual_target", "phase", "start_ratio"}
        if set(cue) != cue_fields:
            missing = sorted(cue_fields - set(cue))
            unknown = sorted(set(cue) - cue_fields)
            if missing:
                fail(f"{cue_path} is missing required field {missing[0]}")
            fail(f"{cue_path} contains unknown field {unknown[0]}")
        cue_id = require_string(cue["cue_id"], f"{cue_path}.cue_id")
        if cue_id in cue_ids:
            fail(f"{cue_path}.cue_id must be unique")
        cue_ids.add(cue_id)
        anchor = require_string(cue["narration_anchor"], f"{cue_path}.narration_anchor")
        anchor_start = narration.find(anchor, cursor)
        if anchor_start < 0:
            fail(
                f"{cue_path}.narration_anchor must be exact narration text in spoken order"
            )
        cursor = anchor_start + len(anchor)
        require_string(cue["visual_target"], f"{cue_path}.visual_target")
        phase = require_string(cue["phase"], f"{cue_path}.phase")
        if phase not in SEMANTIC_TIMELINE_PHASES:
            fail(
                f"{cue_path}.phase must be establish, relate, focus, or resolve"
            )
        start_ratio = require_ratio(cue["start_ratio"], f"{cue_path}.start_ratio")
        if start_ratio <= previous_ratio:
            fail(f"{cue_path}.start_ratio must increase in narration order")
        expected_ratio = anchor_start / max(1, len(narration))
        if abs(start_ratio - expected_ratio) > 0.12:
            fail(
                f"{cue_path}.start_ratio must follow the narration anchor position"
            )
        previous_ratio = start_ratio

    hold_ratio = require_ratio(
        timeline["stable_hold_start_ratio"], f"{path}.stable_hold_start_ratio"
    )
    if hold_ratio < 0.75 or hold_ratio > 0.9:
        fail(f"{path}.stable_hold_start_ratio must be from 0.75 to 0.9")
    if hold_ratio - previous_ratio < 0.05:
        fail(f"{path}.stable_hold_start_ratio must follow the final cue")
    canonical_bytes(timeline)


def validate_bindings(value: Any, path: str, shot_id: str, *, require_narration: bool) -> None:
    bindings = require_object(value, path)
    required = {"shot_id", "segment_ids", "time_range_seconds"}
    if require_narration:
        required.add("narration")
    require_fields(bindings, required, path)
    if require_string(bindings["shot_id"], f"{path}.shot_id") != shot_id:
        fail(f"{path}.shot_id must match the Slide shot_id")
    require_string_list(bindings["segment_ids"], f"{path}.segment_ids")
    if require_narration:
        require_string(bindings["narration"], f"{path}.narration")
    time_range = require_object(bindings["time_range_seconds"], f"{path}.time_range_seconds")
    if set(time_range) != {"start", "end"}:
        fail(f"{path}.time_range_seconds must contain exactly start and end")
    start = time_range["start"]
    end = time_range["end"]
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, (int, float))
        or not isinstance(end, (int, float))
        or not math.isfinite(start)
        or not math.isfinite(end)
        or start < 0
        or end <= start
    ):
        fail(f"{path}.time_range_seconds must be a finite increasing range")
    canonical_bytes(bindings)


def validate_private_dependency(private_root: Path) -> dict[str, Any]:
    inventory_path = private_root / "INVENTORY.json"
    inventory = require_object(read_json(inventory_path, "private dependency inventory"), "inventory")
    if inventory.get("schema_id") != INVENTORY_SCHEMA_ID:
        fail("private dependency inventory schema is unsupported")
    require_string(inventory.get("version"), "inventory.version")
    files = require_object(inventory.get("files"), "inventory.files")
    for relative, expected_hash in files.items():
        require_string(relative, "inventory file path")
        path = private_root / relative
        if not path.is_file():
            fail(f"private dependency file is missing: {relative}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected_hash)):
            fail(f"private dependency hash is invalid: {relative}")
        actual_hash = sha256_bytes(path.read_bytes())
        if actual_hash != expected_hash:
            fail(f"private dependency hash mismatch: {relative}")
    if set(files) != EXPECTED_PRIVATE_FILES:
        fail("private dependency inventory file set is incomplete or contains unsupported files")
    for relative, required_headers in CSV_HEADERS.items():
        path = private_root / relative
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                headers = set(reader.fieldnames or [])
                if not required_headers.issubset(headers):
                    fail(f"private dependency table has invalid headers: {relative}")
                if next(reader, None) is None:
                    fail(f"private dependency table has no data rows: {relative}")
        except UnicodeError as exc:
            fail(f"private dependency table is not valid UTF-8: {relative}: {exc}")
        except OSError as exc:
            fail(f"cannot read private dependency table {relative}: {exc}")
    return inventory


def validate_input(value: Any) -> dict[str, Any]:
    payload = require_object(value, "input")
    expected_fields = {
        "schema_id", "version", "video_id", "project_name", "brief", "script", "slides"
    }
    if set(payload) != expected_fields:
        missing = sorted(expected_fields - set(payload))
        unknown = sorted(set(payload) - expected_fields)
        if missing:
            fail(f"input is missing required field {missing[0]}")
        fail(f"input contains unknown field {unknown[0]}")
    if payload["schema_id"] != SCHEMA_ID or payload["version"] != 1:
        fail(f"input schema/version must be {SCHEMA_ID} version 1")
    require_string(payload["video_id"], "input.video_id")
    require_string(payload["project_name"], "input.project_name")
    require_string(payload["script"], "input.script")
    brief = require_object(payload["brief"], "input.brief")
    brief_fields = {
        "goal", "audience", "starting_knowledge", "language", "aspect_ratio",
        "evidence_boundary", "explicit_unknowns", "design_domain", "visual_tone",
        "target_duration_seconds", "broll_availability",
    }
    require_fields(brief, brief_fields, "input.brief")
    for field in (
        "goal", "audience", "starting_knowledge", "language", "aspect_ratio",
        "evidence_boundary", "design_domain", "visual_tone", "broll_availability",
    ):
        require_string(brief[field], f"input.brief.{field}")
    require_string_list(brief["explicit_unknowns"], "input.brief.explicit_unknowns", allow_empty=True)
    require_positive_number(brief["target_duration_seconds"], "input.brief.target_duration_seconds")
    if brief["aspect_ratio"] != "16:9":
        fail("input.brief.aspect_ratio must be 16:9")
    canonical_bytes(brief)
    slides = payload["slides"]
    if not isinstance(slides, list) or not slides:
        fail("input.slides must be a non-empty array")
    shot_ids: set[str] = set()
    for index, raw_slide in enumerate(slides):
        path = f"input.slides[{index}]"
        slide = require_object(raw_slide, path)
        required_slide_fields = {
            "shot_id", "shot_type", "duration_seconds", "communication_intent", "visual_intent"
        }
        require_fields(slide, required_slide_fields, path)
        shot_id = require_string(slide["shot_id"], f"{path}.shot_id")
        if shot_id in shot_ids:
            fail(f"duplicate Slide shot_id {shot_id}")
        shot_ids.add(shot_id)
        if slide["shot_type"] not in SLIDE_SHOT_TYPES:
            fail(f"{path}.shot_type must be avatar_html, broll_html, or html_only")
        duration = slide["duration_seconds"]
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 2.5:
            fail(f"{path}.duration_seconds must be at least 2.5")
        communication_path = f"{path}.communication_intent"
        communication = require_object(slide["communication_intent"], communication_path)
        communication_fields = {
            "viewer_before", "viewer_after", "communication_operation", "required_facts",
            "relationships", "expected_viewer_response", "bindings",
        }
        require_fields(communication, communication_fields, communication_path)
        for field in (
            "viewer_before", "viewer_after", "communication_operation", "expected_viewer_response"
        ):
            require_string(communication[field], f"{communication_path}.{field}")
        require_string_list(communication["required_facts"], f"{path}.communication_intent.required_facts")
        require_string_list(communication["relationships"], f"{communication_path}.relationships")
        validate_bindings(
            communication["bindings"], f"{communication_path}.bindings", shot_id,
            require_narration=True,
        )
        canonical_bytes(communication)
        visual = require_object(slide["visual_intent"], f"{path}.visual_intent")
        visual_fields = {
            "render_mode", "primary_focus", "information_priority", "presentation_order",
            "semantic_timeline", "relationship", "simplicity", "final_frame", "bindings",
        }
        require_fields(visual, visual_fields, f"{path}.visual_intent")
        if visual["render_mode"] not in RENDER_MODES:
            fail(f"{path}.visual_intent.render_mode must be html_svg or echarts")
        for field in ("primary_focus", "relationship", "simplicity", "final_frame"):
            require_string(visual[field], f"{path}.visual_intent.{field}")
        require_string_list(visual["information_priority"], f"{path}.visual_intent.information_priority")
        require_string_list(visual["presentation_order"], f"{path}.visual_intent.presentation_order")
        validate_semantic_timeline(
            visual["semantic_timeline"],
            f"{path}.visual_intent.semantic_timeline",
            communication["bindings"]["narration"],
        )
        validate_bindings(
            visual["bindings"], f"{path}.visual_intent.bindings", shot_id,
            require_narration=False,
        )
        communication_bindings = {
            key: value for key, value in communication["bindings"].items()
            if key != "narration"
        }
        if canonical_bytes(communication_bindings) != canonical_bytes(visual["bindings"]):
            fail(f"{path} Communication and Visual bindings must exactly match")
        canonical_bytes(visual)
        canonical_bytes(slide)
    return payload


def build_query(payload: dict[str, Any]) -> str:
    parts = [
        "medium: fixed-canvas video presentation slides",
        f"project: {payload['project_name']}",
        f"complete brief JSON: {canonical_bytes(payload['brief']).decode('utf-8')}",
        f"complete narration script: {payload['script']}",
        "quality: information visualization editorial clarity readable high contrast",
    ]
    for index, slide in enumerate(payload["slides"], 1):
        parts.append(
            f"complete slide {index} JSON: {canonical_bytes(slide).decode('utf-8')}"
        )
    return " ".join(" ".join(parts).split())


def build_design_search_query(payload: dict[str, Any]) -> str:
    brief = payload["brief"]
    parts = [
        payload["project_name"],
        brief["goal"],
        brief["audience"],
        brief["starting_knowledge"],
        brief["design_domain"],
        brief["visual_tone"],
        "fixed-canvas video presentation slide information design",
    ]
    for slide in payload["slides"]:
        communication = slide["communication_intent"]
        visual = slide["visual_intent"]
        parts.extend(
            [
                communication["communication_operation"],
                " ".join(communication["relationships"]),
                visual["primary_focus"],
                visual["relationship"],
            ]
        )
    return " ".join(" ".join(parts).split())


def run_domain_search(
    private_root: Path,
    query: str,
    domain: str,
    *,
    max_results: int = 3,
) -> list[dict[str, Any]]:
    command = [
        sys.executable,
        str(private_root / "scripts" / "search.py"),
        query,
        "--domain",
        domain,
        "--max-results",
        str(max_results),
        "--json",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown private dependency error"
        fail(f"UI UX Pro Max {domain} search failed: {detail}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"UI UX Pro Max {domain} search is not valid JSON: {exc}")
    if not isinstance(response, dict) or response.get("error"):
        fail(f"UI UX Pro Max {domain} search returned an invalid response")
    rows = response.get("results")
    if not isinstance(rows, list) or not rows:
        fail(f"UI UX Pro Max {domain} search returned no matching result")
    return [require_object(row, f"{domain} search result {index}") for index, row in enumerate(rows)]


def reasoning_rule(private_root: Path, product_type: str) -> dict[str, str]:
    path = private_root / "data" / "ui-reasoning.csv"
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        fail(f"cannot read UI UX Pro Max reasoning rules: {exc}")
    normalized = product_type.casefold()
    for row in rows:
        category = str(row.get("UI_Category", "")).strip()
        if category.casefold() == normalized:
            return row
    for row in rows:
        category = str(row.get("UI_Category", "")).strip()
        candidate = category.casefold()
        if candidate and (candidate in normalized or normalized in candidate):
            return row
    fail(f"UI UX Pro Max reasoning search returned no matching rule for category: {product_type}")


def audience_compatible_rows(
    rows: list[dict[str, Any]],
    audience: str,
    *,
    fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    if "adult" not in audience.casefold():
        return rows
    blocked = ("children", "childrens", "kid", "teen", "youth-focused")
    compatible = [
        row for row in rows
        if not any(
            term in " ".join(str(row.get(field, "")) for field in fields).casefold()
            for term in blocked
        )
    ]
    if not compatible:
        fail("UI UX Pro Max returned no audience-compatible design result")
    return compatible


def select_style(
    rows: list[dict[str, Any]],
    style_priority: str,
    audience: str,
) -> dict[str, Any]:
    rows = audience_compatible_rows(rows, audience, fields=("Best For",))
    interface_style_terms = (
        "dashboard", "bento", "conversion", "hero-centric", "heat map",
        "interactive product demo", "spatial ui",
    )
    rows = [
        row for row in rows
        if not any(
            term in require_string(
                row.get("Style Category"), "style search result.Style Category"
            ).casefold()
            for term in interface_style_terms
        )
        and require_string(row.get("Type"), "style search result.Type") != "Landing Page"
    ]
    if not rows:
        fail("UI UX Pro Max returned no fixed-canvas-compatible style result")
    priorities = [part.strip().casefold() for part in style_priority.split("+") if part.strip()]
    for priority in priorities:
        for row in rows:
            name = require_string(row.get("Style Category"), "style search result.Style Category")
            if priority in name.casefold() or name.casefold() in priority:
                return row
    return rows[0]


def select_typography(rows: list[dict[str, Any]], audience: str) -> dict[str, Any]:
    compatible = audience_compatible_rows(
        rows,
        audience,
        fields=("Mood/Style Keywords", "Best For", "Notes"),
    )
    for row in compatible:
        if require_string(row.get("Category"), "typography search result.Category") == "Sans + Sans":
            return row
    return compatible[0]


def usable_effect_cues(value: str, *, motion: bool) -> list[str]:
    interaction_terms = {
        "active state", "hover", "tap", "press", "cursor", "scroll", "navbar",
        "loading", "responsive", "breakpoint", "page transition", "click",
        "transition-none",
    }
    motion_terms = {
        "animate", "animation", "fade", "kinetic", "motion", "reveal", "slide",
        "stagger", "transition", "wipe",
    }
    cues: list[str] = []
    for raw_cue in re.split(r"[,;]", value):
        cue = raw_cue.strip()
        lowered = cue.casefold()
        if not cue or any(term in lowered for term in interaction_terms):
            continue
        is_motion = any(term in lowered for term in motion_terms) or bool(
            re.search(r"\b\d+(?:-\d+)?ms\b", lowered)
        )
        if is_motion == motion:
            cues.append(cue)
    return cues


def format_slide_visual_system(
    product: dict[str, Any],
    reasoning: dict[str, str],
    style: dict[str, Any],
    colors: dict[str, Any],
    typography: dict[str, Any],
) -> str:
    product_type = require_string(product.get("Product Type"), "product search result.Product Type")
    style_name = require_string(style.get("Style Category"), "style search result.Style Category")
    style_keywords = require_string(style.get("Keywords"), "style search result.Keywords")
    style_effects = require_string(style.get("Effects & Animation"), "style search result.Effects & Animation")
    heading = require_string(typography.get("Heading Font"), "typography search result.Heading Font")
    body = require_string(typography.get("Body Font"), "typography search result.Body Font")
    mood = require_string(typography.get("Mood/Style Keywords"), "typography search result.Mood/Style Keywords")
    palette_roles = (
        ("Primary", "Primary"),
        ("Secondary", "Secondary"),
        ("Highlight", "Accent"),
        ("Background", "Background"),
        ("Foreground", "Foreground"),
        ("Muted", "Muted"),
        ("Border", "Border"),
        ("Danger", "Destructive"),
    )
    palette_lines = ["| Role | Hex |", "| --- | --- |"]
    for role, field in palette_roles:
        color = require_string(colors.get(field), f"color search result.{field}").upper()
        _hex_to_rgb(color, f"{field} color")
        palette_lines.append(f"| {role} | `{color}` |")
    material_cues = usable_effect_cues(style_effects, motion=False)
    motion_cues = usable_effect_cues(style_effects, motion=True)
    anti_patterns = require_string(reasoning.get("Anti_Patterns"), "reasoning rule.Anti_Patterns")
    return "\n".join(
        [
            "## Slide Visual System",
            "",
            "### Visual Language",
            f"- Audience context: {product_type}",
            f"- Style: {style_name}",
            f"- Character: {style_keywords}",
            f"- Source cautions: {anti_patterns}",
            "- Apply this character to a fixed video canvas; composition still follows each Slide's semantic relationship.",
            "",
            "### Palette",
            *palette_lines,
            "",
            "### Typography",
            f"- Heading role: {heading}",
            f"- Body role: {body}",
            f"- Character: {mood}",
            "- Use these as hierarchy and personality guidance through runtime-local font families only.",
            "",
            "### Shape And Material",
            f"- Source cues: {'; '.join(material_cues) if material_cues else 'No additional material cue survives fixed-canvas adaptation.'}",
            "- Keep one coherent geometry and depth language across the video; do not turn information into interface components.",
            "",
            "### Motion Character",
            f"- Source cues: {'; '.join(motion_cues) if motion_cues else 'No additional style motion cue survives fixed-canvas adaptation.'}",
            "- Use finite motion only to establish reading order, explain a relationship, and settle into a stable final frame.",
        ]
    )


def run_private_search(
    private_root: Path,
    query: str,
    project_name: str,
    product_query: str,
    style_query: str,
    typography_query: str,
    audience: str,
) -> str:
    product = run_domain_search(private_root, product_query, "product", max_results=1)[0]
    product_type = require_string(product.get("Product Type"), "product search result.Product Type")
    rule = reasoning_rule(private_root, product_type)
    style_priority = require_string(rule.get("Style_Priority"), "reasoning rule.Style_Priority")
    color_mood = require_string(rule.get("Color_Mood"), "reasoning rule.Color_Mood")
    typography_mood = require_string(rule.get("Typography_Mood"), "reasoning rule.Typography_Mood")
    style_rows = run_domain_search(
        private_root,
        f"{style_query} {style_priority} style",
        "style",
        max_results=16,
    )
    style = select_style(style_rows, style_priority, audience)
    colors = run_domain_search(
        private_root,
        f"{query} {product_type} {color_mood}",
        "color",
        max_results=1,
    )[0]
    typography_rows = run_domain_search(
        private_root,
        f"{typography_query} {typography_mood} typography",
        "typography",
        max_results=8,
    )
    typography = select_typography(typography_rows, audience)
    master = format_slide_visual_system(product, rule, style, colors, typography)
    missing_sections = sorted(section for section in REQUIRED_MASTER_SECTIONS if section not in master)
    if missing_sections:
        fail(f"UI UX Pro Max Slide MASTER output is incomplete: missing {missing_sections[0]}")
    return master


def _hex_to_rgb(value: str, path: str) -> tuple[int, int, int]:
    normalized = value.strip().upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", normalized):
        fail(f"UI UX Pro Max {path} must be a six-digit hex color")
    return tuple(int(normalized[index:index + 2], 16) for index in (1, 3, 5))


def _blend(start: str, end: str, end_weight: float) -> str:
    start_rgb = _hex_to_rgb(start, "background color")
    end_rgb = _hex_to_rgb(end, "foreground color")
    channels = [
        round(left * (1 - end_weight) + right * end_weight)
        for left, right in zip(start_rgb, end_rgb)
    ]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _relative_luminance(value: str) -> float:
    channels = []
    for channel in _hex_to_rgb(value, "palette color"):
        scaled = channel / 255.0
        channels.append(
            scaled / 12.92 if scaled <= 0.04045 else math.pow((scaled + 0.055) / 1.055, 2.4)
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def runtime_visual_style_profile(base_master: str) -> dict[str, Any]:
    role_values: dict[str, str] = {}
    for role, value in re.findall(
        r"^\|\s*(Primary|Highlight|Background|Foreground|Danger)\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|",
        base_master,
        flags=re.MULTILINE,
    ):
        role_values[role] = value.upper()
    required_roles = {"Primary", "Highlight", "Background", "Foreground", "Danger"}
    if set(role_values) != required_roles:
        fail("UI UX Pro Max MASTER output does not expose a complete runtime palette")
    surface = role_values["Background"]
    ink = role_values["Foreground"]
    if _contrast_ratio(surface, ink) < 4.5:
        fail("UI UX Pro Max MASTER foreground/background contrast is below 4.5:1")
    style_section = re.search(
        r"^### Visual Language\s*$\n(?P<body>.*?)(?=^### |\Z)",
        base_master,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not style_section:
        fail("UI UX Pro Max MASTER output does not expose a runtime visual style profile")
    style_name_match = re.search(
        r"^- Style:\s*(?P<name>.+?)\s*$",
        style_section.group("body"),
        flags=re.MULTILINE,
    )
    style_name = style_name_match.group("name") if style_name_match else ""
    profile_id = RUNTIME_PROFILE_STYLE_MAP.get(style_name)
    if not profile_id:
        fail(f"UI UX Pro Max runtime visual style profile is unmapped: {style_name or 'missing style name'}")
    return {
        "id": profile_id,
        "palette": {
            "surface": surface,
            "surface_recessed": _blend(surface, ink, 0.12),
            "ink": ink,
            "muted": _blend(surface, ink, 0.70),
            "primary": role_values["Primary"],
            "highlight": role_values["Highlight"],
            "danger": role_values["Danger"],
            "outline": _blend(surface, ink, 0.28),
        },
    }


def run_chart_search(private_root: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    chart_slides = [
        slide for slide in payload["slides"]
        if slide["visual_intent"]["render_mode"] == "echarts"
    ]
    if not chart_slides:
        return []
    query = " ".join(
        f"{slide['visual_intent']['relationship']} {slide['visual_intent']['primary_focus']}"
        for slide in chart_slides
    )
    command = [
        sys.executable,
        str(private_root / "scripts" / "search.py"),
        query,
        "--domain",
        "chart",
        "--max-results",
        "3",
        "--json",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown chart search error"
        fail(f"UI UX Pro Max chart guidance failed: {detail}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"UI UX Pro Max chart guidance is not valid JSON: {exc}")
    if not isinstance(response, dict) or response.get("error") or not response.get("results"):
        fail("UI UX Pro Max chart guidance returned no supported result")
    return response["results"]


def format_chart_guidance(results: list[dict[str, Any]]) -> str:
    if not results:
        return "- No ECharts Slide is planned for this video."
    lines: list[str] = []
    for index, row in enumerate(results, 1):
        chart_type = require_string(row.get("Best Chart Type"), f"chart result {index}.Best Chart Type")
        when = require_string(row.get("When to Use"), f"chart result {index}.When to Use")
        color = require_string(row.get("Color Guidance"), f"chart result {index}.Color Guidance")
        accessibility = require_string(row.get("Accessibility Notes"), f"chart result {index}.Accessibility Notes")
        lines.extend(
            [
                f"### Candidate {index}: {chart_type}",
                f"- Use when: {when}",
                f"- Color guidance: {color}",
                f"- Accessibility: {accessibility}",
            ]
        )
    return "\n".join(lines)


def compose_master(
    payload: dict[str, Any],
    inventory: dict[str, Any],
    base_master: str,
    chart_results: list[dict[str, Any]],
) -> str:
    input_hash = sha256_bytes(canonical_bytes(payload))
    master_id = f"sv-master-{input_hash[:16]}"
    runtime_profile = runtime_visual_style_profile(base_master)
    metadata = {
        "schema_id": MASTER_SCHEMA_ID,
        "version": MASTER_VERSION,
        "id": master_id,
        "video_id": payload["video_id"],
        "input_sha256": input_hash,
        "private_dependency_version": inventory["version"],
        "safe_area_px": {"top": 64, "right": 96, "bottom": 64, "left": 96},
        "runtime_visual_style_profile": runtime_profile,
    }
    return "\n".join(
        [
            "<!-- smart-video-master",
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            "-->",
            "",
            "# Smart Video Slide Design MASTER",
            "",
            "This is the single visual source of truth for every Slide in this video.",
            "",
            "## UI UX Pro Max Adaptation",
            "",
            base_master,
            "",
            "## Slide Production Constraints",
            "",
            "- Design for a fixed 16:9 video canvas, not a website or application.",
            "- Use one primary visual focus and a clear reading order for each shot.",
            "- Use only source-authorized visible copy, facts, values, units, and relationships.",
            "- Author ordinary Slides with HTML, CSS, and inline SVG only.",
            "- Author chart Slides as declarative ECharts JSON only; the trusted runtime owns initialization and timeline execution.",
            "- Do not emit JavaScript, interaction, hover-dependent meaning, scrolling, remote resources, external fonts, or perpetual motion.",
            "- Use recommended font roles only through locally available font families and system fallbacks; never load remote font resources.",
            "- Keep the complete final meaning visible in a stable hold after finite entrance and emphasis motion.",
            "- Do not repeat one layout mechanically across Slides. Preserve the MASTER tokens while composing each semantic relationship directly.",
            "",
            "## Safe Area",
            "",
            "- Top: 64px",
            "- Right: 96px",
            "- Bottom: 64px",
            "- Left: 96px",
            "",
            "For avatar_html, keep the primary claim, critical values, and essential relationship outside the runtime-owned lower-right Avatar region. Do not draw an Avatar placeholder or change Avatar geometry.",
            "",
            "## Composition Profiles",
            "",
            "- html_only: backdrop opacity 0.95-0.99; default 0.99.",
            "- avatar_html: backdrop opacity 0.95-0.99; default 0.99; Avatar remains above the Slide.",
            "- broll_html: backdrop opacity 0.20-0.55; default 0.35; B-roll remains recognizable below the Slide.",
            "- The backdrop never reaches 1.00. Content remains fully opaque.",
            "",
            "## Runtime Visual Style Profile",
            "",
            "Write the exact runtime_visual_style_profile object from the metadata header to the whole-video planning document. Author colors only through the resulting --mg-* semantic variables; do not hardcode or redefine palette colors in a Slide.",
            "",
            "## ECharts Guidance",
            "",
            format_chart_guidance(chart_results),
            "",
        ]
    )


def build(input_path: Path, output_dir: Path, private_root: Path) -> Path:
    master_path = output_dir / "MASTER.md"
    temporary_path = output_dir / ".MASTER.md.tmp"
    for stale_path in (master_path, temporary_path):
        if stale_path.exists() or stale_path.is_symlink():
            if not stale_path.is_file() and not stale_path.is_symlink():
                fail(f"existing MASTER output path is not a file: {stale_path.name}")
            try:
                stale_path.unlink()
            except OSError as exc:
                fail(f"cannot invalidate existing MASTER output: {exc}")
    inventory = validate_private_dependency(private_root)
    payload = validate_input(read_json(input_path, "MASTER input"))
    base_master = run_private_search(
        private_root,
        build_design_search_query(payload),
        payload["project_name"],
        payload["brief"]["design_domain"],
        " ".join(
            [
                payload["brief"]["design_domain"],
                payload["brief"]["audience"],
                payload["brief"]["visual_tone"],
            ]
        ),
        f"{payload['brief']['audience']} {payload['brief']['visual_tone']}",
        payload["brief"]["audience"],
    )
    chart_results = run_chart_search(private_root, payload)
    master = compose_master(payload, inventory, base_master, chart_results)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        temporary_path.write_text(master, encoding="utf-8")
        temporary_path.replace(master_path)
    except OSError as exc:
        try:
            if temporary_path.exists() or temporary_path.is_symlink():
                temporary_path.unlink()
        except OSError as cleanup_exc:
            fail(f"cannot write MASTER output: {exc}; cannot remove partial output: {cleanup_exc}")
        fail(f"cannot write MASTER output: {exc}")
    return master_path


def parse_args() -> argparse.Namespace:
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--private-root",
        type=Path,
        default=skill_root / "assets" / "private" / "ui-ux-pro-max",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        path = build(args.input, args.output_dir, args.private_root)
    except BuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
