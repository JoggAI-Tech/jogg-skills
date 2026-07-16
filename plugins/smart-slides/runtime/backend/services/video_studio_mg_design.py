import hashlib
from copy import deepcopy
from typing import Any, Dict, List, Optional

from backend.services.video_studio_mg_templates import get_mg_template


CANVAS = {
    "profile_id": "landscape_16_9",
    "width": 1920,
    "height": 1080,
    "aspect_ratio": "16:9",
}
SAFE_ZONES = {
    "canvas_padding": {"left": 96, "right": 96, "top": 72, "bottom": 72},
    "subtitle": {"x": 96, "y": 856, "w": 1344, "h": 160},
    "avatar": {"x": 1560, "y": 720, "w": 264, "h": 264},
}


def instantiate_mg_design_doc(
    *,
    template_id: str,
    clip: Dict[str, Any],
    information_blocks: List[Dict[str, Any]],
    duration_seconds: float,
    motion_sequence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    blueprint = get_mg_template(template_id)
    duration = _positive_float(duration_seconds, _positive_float(clip.get("duration"), 6.0))
    blocks = _normalize_blocks(information_blocks)
    instance_seed = "|".join([
        template_id,
        str(clip.get("id") or ""),
        ",".join(str(item) for item in clip.get("bound_shots", []) if str(item)),
        "|".join(block["text"] for block in blocks),
    ])
    instance_id = f"{template_id}:{hashlib.sha1(instance_seed.encode('utf-8')).hexdigest()[:12]}"
    timeline_events = _normalize_timeline_events(motion_sequence, duration)
    elements = [
        *_elements_for_blueprint(blueprint, blocks, duration),
        *_motion_elements_for_timeline(timeline_events, blueprint, duration),
    ]
    design_doc = {
        "version": "mg_design_doc_v1",
        "template_id": template_id,
        "template_instance_id": instance_id,
        "template_name": blueprint["name"],
        "canvas": deepcopy(CANVAS),
        "safe_zones": deepcopy(SAFE_ZONES),
        "editable": True,
        "mutation_scope": "project_instance_only",
        "source_clip_id": str(clip.get("id") or ""),
        "bound_shots": [str(item) for item in clip.get("bound_shots", []) if str(item)],
        "visual_system": str(clip.get("visual_system") or blueprint.get("visual_system") or "comparison"),
        "timeline": {
            "start_s": _positive_float(clip.get("start"), 0.0),
            "duration_seconds": duration,
            "end_s": _positive_float(clip.get("start"), 0.0) + duration,
        },
        "timeline_events": timeline_events,
        "elements": elements,
    }
    return normalize_mg_design_doc(design_doc)


def normalize_mg_design_doc(design_doc: Dict[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(design_doc)
    normalized["canvas"] = deepcopy(CANVAS)
    normalized["safe_zones"] = deepcopy(SAFE_ZONES)
    timeline = normalized.get("timeline") if isinstance(normalized.get("timeline"), dict) else {}
    duration = _positive_float(timeline.get("duration_seconds"), 6.0)
    normalized["timeline"] = {
        "start_s": _positive_float(timeline.get("start_s"), 0.0),
        "duration_seconds": duration,
        "end_s": _positive_float(timeline.get("start_s"), 0.0) + duration,
    }
    normalized["timeline_events"] = _normalize_timeline_events(
        normalized.get("timeline_events") if isinstance(normalized.get("timeline_events"), list) else [],
        duration,
    )
    elements = normalized.get("elements") if isinstance(normalized.get("elements"), list) else []
    normalized["elements"] = [_normalize_element(element, index, duration) for index, element in enumerate(elements)]
    return normalized


def _elements_for_blueprint(blueprint: Dict[str, Any], blocks: List[Dict[str, str]], duration: float) -> List[Dict[str, Any]]:
    title = blocks[0] if blocks else {"label": "主题", "text": str(blueprint.get("name") or "关键信息")}
    supporting = blocks[1:] or blocks[:1]
    accent = _accent_for_system(str(blueprint.get("visual_system") or "comparison"))
    base_elements: List[Dict[str, Any]] = [
        {
            "id": "headline",
            "type": "text",
            "semantic_role": "primary_claim",
            "module": blueprint["modules"][0],
            "text": title["text"],
            "label": title["label"],
            "rect": {"x": 150, "y": 126, "w": 740, "h": 150},
            "z_index": 20,
            "opacity": 0.96,
            "style": {"font_size": 64, "font_weight": 900, "color": "#F8FAFC", "accent": accent},
            "motion": {"start_s": 0.0, "end_s": min(duration, 1.1), "preset": "fade_slide_in"},
            "lock": {"can_edit": True, "can_delete": False, "can_create_sibling": False},
        },
        {
            "id": "main_shape",
            "type": _shape_type_for_layout(str(blueprint.get("layout") or "")),
            "semantic_role": "visual_metaphor",
            "module": blueprint["modules"][1],
            "text": "",
            "label": str(blueprint.get("name") or ""),
            "rect": {"x": 980, "y": 144, "w": 570, "h": 360},
            "z_index": 10,
            "opacity": 0.72,
            "style": {"stroke": accent, "fill": "rgba(15,23,42,0.24)", "stroke_width": 5},
            "motion": {"start_s": min(duration, 0.55), "end_s": min(duration, 3.2), "preset": "draw_reveal"},
            "lock": {"can_edit": True, "can_delete": False, "can_create_sibling": False},
        },
    ]
    for index, block in enumerate(supporting[:4], start=1):
        base_elements.append(
            {
                "id": f"info_{index}",
                "type": "text_block",
                "semantic_role": "supporting_fact",
                "module": blueprint["modules"][min(2, len(blueprint["modules"]) - 1)],
                "text": block["text"],
                "label": block["label"],
                "rect": {"x": 150 + ((index - 1) % 2) * 410, "y": 330 + ((index - 1) // 2) * 138, "w": 360, "h": 96},
                "z_index": 18,
                "opacity": 0.9,
                "style": {"font_size": 28, "font_weight": 760, "color": "#E2E8F0", "accent": accent},
                "motion": {"start_s": min(duration, 0.8 + index * 0.55), "end_s": min(duration, 2.0 + index * 0.55), "preset": "fade_pop"},
                "lock": {"can_edit": True, "can_delete": False, "can_create_sibling": False},
            }
        )
    return base_elements


def _normalize_timeline_events(events: Optional[List[Dict[str, Any]]], duration: float) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, event in enumerate(events or []):
        if not isinstance(event, dict):
            continue
        target = str(event.get("target") or f"event_{index + 1}").strip() or f"event_{index + 1}"
        action = str(event.get("action") or "reveal").strip() or "reveal"
        text = str(event.get("text") or "").strip()
        at_s = round(_clamp(_positive_float(event.get("at_s"), index * 0.8), 0, duration), 3)
        normalized.append(
            {
                "at_s": at_s,
                "target": target,
                "action": action,
                "text": text,
            }
        )
    return sorted(normalized, key=lambda item: item["at_s"])


def _motion_elements_for_timeline(events: List[Dict[str, Any]], blueprint: Dict[str, Any], duration: float) -> List[Dict[str, Any]]:
    if not events:
        return []
    accent = _accent_for_system(str(blueprint.get("visual_system") or "comparison"))
    elements: List[Dict[str, Any]] = []
    for index, event in enumerate(events[:6]):
        column = index % 3
        row = index // 3
        start_s = _clamp(_positive_float(event.get("at_s"), 0.0), 0, duration)
        elements.append(
            {
                "id": f"motion_event_{index + 1}",
                "type": "timeline_event",
                "semantic_role": "motion_timeline_event",
                "module": blueprint["modules"][min(2, len(blueprint["modules"]) - 1)],
                "text": str(event.get("text") or event.get("action") or ""),
                "label": str(event.get("target") or f"event_{index + 1}"),
                "rect": {"x": 960 + column * 250, "y": 548 + row * 118, "w": 220, "h": 88},
                "z_index": 22 + index,
                "opacity": 0.92,
                "style": {"font_size": 22, "font_weight": 820, "color": "#F8FAFC", "accent": accent},
                "motion": {
                    "start_s": start_s,
                    "end_s": min(duration, start_s + 1.2),
                    "preset": str(event.get("action") or "reveal"),
                },
                "lock": {"can_edit": True, "can_delete": False, "can_create_sibling": False},
            }
        )
    return elements


def _normalize_element(element: Any, index: int, duration: float) -> Dict[str, Any]:
    raw = element if isinstance(element, dict) else {}
    rect = raw.get("rect") if isinstance(raw.get("rect"), dict) else {}
    w = min(max(int(_positive_float(rect.get("w"), 320)), 80), CANVAS["width"] - 192)
    h = min(max(int(_positive_float(rect.get("h"), 80)), 48), 784)
    x = int(_clamp(_positive_float(rect.get("x"), 120), 96, CANVAS["width"] - 96 - w))
    y = int(_clamp(_positive_float(rect.get("y"), 120), 72, 856 - h))
    if _overlaps_avatar(x, y, w, h):
        x = max(96, SAFE_ZONES["avatar"]["x"] - w - 48)
        if _overlaps_avatar(x, y, w, h):
            y = max(72, SAFE_ZONES["avatar"]["y"] - h - 48)
    motion = raw.get("motion") if isinstance(raw.get("motion"), dict) else {}
    start_s = _clamp(_positive_float(motion.get("start_s"), 0.0), 0, duration)
    end_s = _clamp(_positive_float(motion.get("end_s"), min(duration, start_s + 1.0)), start_s, duration)
    return {
        **raw,
        "id": str(raw.get("id") or f"element_{index + 1}"),
        "type": str(raw.get("type") or "text"),
        "semantic_role": str(raw.get("semantic_role") or "supporting_fact"),
        "text": str(raw.get("text") or ""),
        "label": str(raw.get("label") or ""),
        "rect": {"x": x, "y": y, "w": w, "h": h},
        "z_index": int(_positive_float(raw.get("z_index"), index + 1)),
        "opacity": round(_clamp(_positive_float(raw.get("opacity"), 1.0), 0.0, 1.0), 3),
        "style": raw.get("style") if isinstance(raw.get("style"), dict) else {},
        "motion": {
            **motion,
            "start_s": round(start_s, 3),
            "end_s": round(end_s, 3),
            "preset": str(motion.get("preset") or "fade_in"),
        },
        "lock": {
            "can_edit": True,
            "can_delete": False,
            "can_create_sibling": False,
        },
    }


def _normalize_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for index, block in enumerate(blocks or [], start=1):
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or block.get("label") or "").strip()
        if not text:
            continue
        normalized.append({"label": str(block.get("label") or f"{index:02d}"), "text": text})
    return normalized or [{"label": "核心", "text": "关键信息"}]


def _shape_type_for_layout(layout: str) -> str:
    if "timeline" in layout or "strip" in layout:
        return "timeline"
    if "map" in layout or "route" in layout:
        return "path"
    if "matrix" in layout or "grid" in layout:
        return "grid"
    if "orbit" in layout or "ring" in layout:
        return "diagram"
    return "shape"


def _accent_for_system(system: str) -> str:
    return {
        "metric": "#38BDF8",
        "causal": "#A3E635",
        "route": "#FBBF24",
        "timeline": "#C084FC",
        "comparison": "#2DD4BF",
    }.get(system, "#38BDF8")


def _overlaps_avatar(x: int, y: int, w: int, h: int) -> bool:
    avatar = SAFE_ZONES["avatar"]
    return x < avatar["x"] + avatar["w"] and x + w > avatar["x"] and y < avatar["y"] + avatar["h"] and y + h > avatar["y"]


def _positive_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if parsed < 0:
        return float(fallback)
    return parsed


def _clamp(value: float, minimum: float, maximum: float) -> float:
    if maximum < minimum:
        return minimum
    return min(max(value, minimum), maximum)
