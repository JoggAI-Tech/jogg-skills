#!/usr/bin/env python3
"""Validate a declarative Smart Video ECharts MG author spec."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


RECIPES = {
    "universal-line-bar",
    "map-bar-morph",
    "graph-propagation",
    "radar-reveal",
    "causal-flow",
    "waterfall-decline",
    "stacked-leverage",
    "official-example",
}
LAYOUTS = {"standard", "avatar-left", "avatar-right"}
ALLOWED_KEYS = {
    "asset_type",
    "recipe_id",
    "title",
    "support",
    "transition_at_s",
    "duration_seconds",
    "layout",
    "data",
    "visual_reference",
}
SEMANTIC_COLORS = {
    "$mg-ink",
    "$mg-muted",
    "$mg-primary",
    "$mg-highlight",
    "$mg-danger",
    "$mg-outline",
    "$mg-surface",
    "$mg-surface-recessed",
    "transparent",
}
COLOR_KEYS = {"color", "backgroundcolor", "bordercolor", "areacolor", "shadowcolor"}
REMOTE_REFERENCE = re.compile(r"(?:https?:|data:|blob:|javascript:|//[^/])", re.I)
EXECUTABLE_TEXT = re.compile(
    r"(?:<script\b|\b(?:async\s+)?function\b|=>|\bnew\s+Function\b|"
    r"\b(?:eval|setTimeout|setInterval|require|import)\s*\()",
    re.I,
)
OFFICIAL_TOP_LEVEL_KEYS = {
    "angleAxis",
    "animation",
    "animationDuration",
    "animationDurationUpdate",
    "animationEasing",
    "animationEasingUpdate",
    "aria",
    "backgroundColor",
    "calendar",
    "color",
    "dataZoom",
    "dataset",
    "geo",
    "grid",
    "legend",
    "parallel",
    "parallelAxis",
    "polar",
    "radar",
    "radiusAxis",
    "series",
    "singleAxis",
    "textStyle",
    "title",
    "tooltip",
    "visualMap",
    "xAxis",
    "yAxis",
}
OFFICIAL_SERIES_TYPES = {
    "bar",
    "boxplot",
    "candlestick",
    "chord",
    "effectScatter",
    "funnel",
    "gauge",
    "graph",
    "heatmap",
    "line",
    "lines",
    "map",
    "matrix",
    "parallel",
    "pictorialBar",
    "pie",
    "radar",
    "sankey",
    "scatter",
    "sunburst",
    "themeRiver",
    "tree",
    "treemap",
}


class ValidationError(ValueError):
    pass


def require_number(value: Any, path: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValidationError(f"{path} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValidationError(f"{path} must be at least {minimum:g}")
    if maximum is not None and result > maximum:
        raise ValidationError(f"{path} must be at most {maximum:g}")
    return result


def require_text(value: Any, path: str, *, limit: int, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{path} must be a string")
    compact = " ".join(value.split())
    if not allow_empty and not compact:
        raise ValidationError(f"{path} must not be empty")
    if len(compact) > limit:
        raise ValidationError(f"{path} must be at most {limit} characters")
    if REMOTE_REFERENCE.search(compact) or EXECUTABLE_TEXT.search(compact):
        raise ValidationError(f"{path} contains executable code or a remote resource")
    return compact


def walk_json(value: Any, path: str = "$", key: str = "") -> None:
    if isinstance(value, str):
        if len(value) > 600:
            raise ValidationError(f"{path} contains an oversized string")
        if REMOTE_REFERENCE.search(value) or EXECUTABLE_TEXT.search(value):
            raise ValidationError(f"{path} contains executable code or a remote resource")
        if key.lower() in COLOR_KEYS or key.lower().endswith("color"):
            if value not in SEMANTIC_COLORS:
                raise ValidationError(f"{path} must use a Smart Video semantic color token")
        return
    if value is None or isinstance(value, (bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValidationError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list):
        if len(value) > 1000:
            raise ValidationError(f"{path} contains more than 1,000 items")
        for index, item in enumerate(value):
            walk_json(item, f"{path}[{index}]", key)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or key in {"__proto__", "constructor", "prototype"}:
                raise ValidationError(f"{path} contains an unsafe key")
            walk_json(item, f"{path}.{key}", key)
        return
    raise ValidationError(f"{path} must contain JSON values only")


def require_object_list(value: Any, path: str, *, minimum: int, maximum: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum or not all(isinstance(item, dict) for item in value):
        raise ValidationError(f"{path} must contain {minimum}-{maximum} objects")
    return value


def validate_recipe_data(recipe: str, data: dict[str, Any]) -> None:
    if recipe == "universal-line-bar":
        labels = data.get("labels")
        values = data.get("values")
        if not isinstance(labels, list) or not 2 <= len(labels) <= 16 or not all(isinstance(item, str) and item.strip() for item in labels):
            raise ValidationError("$.data.labels must contain 2-16 non-empty strings")
        if not isinstance(values, list) or len(values) != len(labels) or not all(
            isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(float(item))
            for item in values
        ):
            raise ValidationError("$.data.values must contain one number per label")
    elif recipe == "map-bar-morph":
        items = require_object_list(data.get("items"), "$.data.items", minimum=2, maximum=20)
        if any(
            not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or not isinstance(item.get("value"), (int, float))
            or isinstance(item.get("value"), bool)
            or not math.isfinite(float(item["value"]))
            for item in items
        ):
            raise ValidationError("$.data.items requires string name and numeric value")
    elif recipe in {"graph-propagation", "causal-flow"}:
        nodes = data.get("nodes")
        if not isinstance(nodes, list) or not 2 <= len(nodes) <= 18 or not all(
            isinstance(item, str) or isinstance(item, dict) for item in nodes
        ):
            raise ValidationError("$.data.nodes must contain 2-18 strings or objects")
        links = data.get("links")
        if links is not None and (
            not isinstance(links, list) or not links or not all(isinstance(item, dict) for item in links)
        ):
            raise ValidationError("$.data.links must be omitted or contain link objects")
    elif recipe == "radar-reveal":
        indicators = data.get("indicators")
        if not isinstance(indicators, list) or not 3 <= len(indicators) <= 8 or not all(
            isinstance(item, str) or isinstance(item, dict) for item in indicators
        ):
            raise ValidationError("$.data.indicators must contain 3-8 strings or objects")
        values = data.get("values")
        if not isinstance(values, list) or len(values) != len(indicators) or not all(
            isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(float(item)) and item >= 0
            for item in values
        ):
            raise ValidationError("$.data.values must contain one value per radar indicator")
        baseline = data.get("baseline")
        if baseline is not None and (
            not isinstance(baseline, list)
            or len(baseline) != len(indicators)
            or not all(isinstance(item, (int, float)) and not isinstance(item, bool) and item >= 0 for item in baseline)
        ):
            raise ValidationError("$.data.baseline must contain one non-negative value per radar indicator")
    elif recipe == "waterfall-decline":
        labels = data.get("labels")
        deltas = data.get("deltas")
        if not isinstance(labels, list) or not 2 <= len(labels) <= 16 or not all(isinstance(item, str) and item.strip() for item in labels):
            raise ValidationError("$.data.labels must contain 2-16 labels")
        if not isinstance(deltas, list) or len(deltas) != len(labels) or not all(
            isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(float(item))
            for item in deltas
        ):
            raise ValidationError("$.data.deltas must contain one delta per label")
    elif recipe == "stacked-leverage":
        labels = data.get("labels")
        series = require_object_list(data.get("series"), "$.data.series", minimum=2, maximum=5)
        if not isinstance(labels, list) or not 2 <= len(labels) <= 16 or not all(isinstance(item, str) and item.strip() for item in labels):
            raise ValidationError("$.data.labels must contain 2-16 labels")
        if any(
            not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or not isinstance(item.get("values"), list)
            or len(item["values"]) != len(labels)
            or not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in item["values"])
            for item in series
        ):
            raise ValidationError("$.data.series values must align with labels")
    elif recipe == "official-example":
        require_text(data.get("example_id"), "$.data.example_id", limit=80, allow_empty=False)
        validate_official_option(data.get("option"), "$.data.option")
        if "initial_option" in data:
            validate_official_option(data["initial_option"], "$.data.initial_option")


def validate_official_option(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    if len(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) > 65536:
        raise ValidationError(f"{path} exceeds the 64 KB budget")
    unexpected = sorted(set(value) - OFFICIAL_TOP_LEVEL_KEYS)
    if unexpected:
        raise ValidationError(f"{path} contains unsupported keys: {', '.join(unexpected)}")
    series = value.get("series")
    if not isinstance(series, list) or not 1 <= len(series) <= 8:
        raise ValidationError(f"{path}.series must contain 1-8 series")
    for index, item in enumerate(series):
        if not isinstance(item, dict) or item.get("type") not in OFFICIAL_SERIES_TYPES:
            raise ValidationError(f"{path}.series[{index}] has an unsupported type")
        if item.get("type") == "map" and item.get("map") != "USA":
            raise ValidationError(f"{path}.series[{index}] may use only the bundled USA map")
    geo = value.get("geo")
    geo_items = geo if isinstance(geo, list) else ([geo] if isinstance(geo, dict) else [])
    if any(item.get("map") != "USA" for item in geo_items):
        raise ValidationError(f"{path}.geo may use only the bundled USA map")
    walk_json(value, path)


def validate(spec: Any, *, duration_seconds: float | None) -> None:
    if not isinstance(spec, dict):
        raise ValidationError("$ must be a JSON object")
    missing = sorted({"asset_type", "recipe_id", "title", "support", "transition_at_s", "layout", "data"} - set(spec))
    if missing:
        raise ValidationError("missing required fields: " + ", ".join(missing))
    unexpected = sorted(set(spec) - ALLOWED_KEYS)
    if unexpected:
        raise ValidationError("unsupported fields: " + ", ".join(unexpected))
    if spec["asset_type"] != "echarts_mg":
        raise ValidationError("$.asset_type must be echarts_mg")
    recipe = spec["recipe_id"]
    if recipe not in RECIPES:
        raise ValidationError("$.recipe_id is not supported by the current runtime")
    require_text(spec["title"], "$.title", limit=48)
    require_text(spec["support"], "$.support", limit=88)
    if spec["layout"] not in LAYOUTS:
        raise ValidationError("$.layout must be standard, avatar-left, or avatar-right")
    transition = require_number(spec["transition_at_s"], "$.transition_at_s", minimum=0.05)
    declared_duration = spec.get("duration_seconds")
    if declared_duration is not None:
        declared_duration = require_number(declared_duration, "$.duration_seconds", minimum=0.2, maximum=900)
    effective_duration = duration_seconds if duration_seconds is not None else declared_duration
    if effective_duration is not None and transition >= effective_duration:
        raise ValidationError("$.transition_at_s must be earlier than the shot duration")
    data = spec["data"]
    if not isinstance(data, dict) or not data:
        raise ValidationError("$.data must be a non-empty object")
    walk_json(data, "$.data")
    validate_recipe_data(recipe, data)
    if "visual_reference" in spec:
        if not isinstance(spec["visual_reference"], dict):
            raise ValidationError("$.visual_reference must be an object")
        walk_json(spec["visual_reference"], "$.visual_reference")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="Path to the ECharts MG JSON spec")
    parser.add_argument("--duration-seconds", type=float, help="Shot duration used to verify transition timing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        validate(spec, duration_seconds=args.duration_seconds)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
