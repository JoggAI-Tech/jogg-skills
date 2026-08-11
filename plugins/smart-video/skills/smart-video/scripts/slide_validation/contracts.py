"""Versioned request, manifest, provenance, and identity contracts."""

from __future__ import annotations

import hashlib
import json
import math
import colorsys
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .shared import *

PRODUCTION_STRATEGY = {
    "id": "smart_video_slide_design",
    "version": "1.0.0",
    "selection_source": "production_default",
}
IDENTITY_FIELDS = {"video_id", "shot_id", "segment_id", "slide_id", "clip_id"}
SLIDE_SHOT_TYPES = {"html_only", "avatar_html", "broll_html"}
MIN_SLIDE_DURATION_SECONDS = 2.5
RENDER_MODES = {"html_svg", "echarts"}
ECHARTS_ACTION_TYPES = {
    "establish_chart", "reveal_series", "highlight_data", "show_annotation",
    "hold_conclusion",
}
TRUSTED_SCRIPTS = [
    "runtime/vendor/echarts.min.js",
    "runtime/vendor/gsap.min.js",
    "runtime/vendor/smart-video-echarts-timeline.js",
]
RENDER_CHECKS = {
    "nonblank_visible_pixels",
    "overflow",
    "overlap",
    "clipping",
    "contrast_legibility",
    "final_frame_completeness",
    "strategy_root_validation",
    "runtime_errors",
    "resource_loads",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VISUAL_SYSTEM_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "assets/contracts/visual-system.v1.schema.json"
)
VISUAL_PROTOTYPES_PATH = (
    Path(__file__).resolve().parents[2] / "assets/visual-knowledge/visual-prototypes.json"
)
EXPRESSION_GRAMMARS_PATH = (
    Path(__file__).resolve().parents[2] / "assets/visual-knowledge/expression-grammar.json"
)
SYNTHESIS_TRAITS_PATH = (
    Path(__file__).resolve().parents[2] / "assets/visual-knowledge/synthesis-traits.json"
)
MAX_SLIDE_DURATION_SECONDS = 60.0
SUPPORTED_BACKGROUNDS = {
    "html_only": "self_contained_slide",
    "avatar_html": "avatar_visible_backplate",
    "broll_html": "broll_visible_backplate",
}
REQUIRED_SELECTOR_RUNTIME_CAPABILITIES = {
    "html_svg", "echarts_canvas", "inline_svg", "local_fonts",
    "final_frame_capture",
}
MIN_EFFECTIVE_SEMANTIC_LOAD = 4
MAX_EFFECTIVE_SEMANTIC_LOAD = 400

def load_json(path: Path, label: str) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {label}: {exc}")
    return parse_json_text(raw, label)


def load_artifact_bytes(path: Path, label: str) -> bytes:
    """Read one immutable artifact byte snapshot."""
    try:
        return path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {label}: {exc}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize smart-video-canonical-json-v1 for source and artifact hashes."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        fail(f"value is outside the canonical JSON profile: {exc}")


def jcs_safe_bytes(value: Any, path: str) -> bytes:
    """Serialize the exact RFC 8785 subset admitted for selection provenance."""

    def serialize(node: Any, node_path: str) -> str:
        if node is None:
            return "null"
        if node is True:
            return "true"
        if node is False:
            return "false"
        if isinstance(node, (int, float)):
            fail(f"unsupported provenance domain at {node_path}: numeric JSON values are not supported")
        if isinstance(node, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in node):
                fail(f"unsupported provenance domain at {node_path}: surrogate code points are not supported")
            return json.dumps(node, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if isinstance(node, list):
            return "[" + ",".join(serialize(child, f"{node_path}[{index}]") for index, child in enumerate(node)) + "]"
        if isinstance(node, dict):
            for key in node:
                if not isinstance(key, str):
                    fail(f"unsupported provenance domain at {node_path}: object keys must be strings")
                if any(0xD800 <= ord(character) <= 0xDFFF for character in key):
                    fail(f"unsupported provenance domain at {node_path}: surrogate code points are not supported in object keys")
            ordered_keys = sorted(node, key=lambda key: key.encode("utf-16-be"))
            entries = []
            for key in ordered_keys:
                child_path = f"{node_path}.{key}"
                entries.append(f"{serialize(key, child_path)}:{serialize(node[key], child_path)}")
            return "{" + ",".join(entries) + "}"
        fail(f"unsupported provenance domain at {node_path}: unsupported JSON value type")

    try:
        return serialize(value, path).encode("utf-8")
    except UnicodeError as exc:
        fail(f"unsupported provenance domain at {path}: Unicode encoding failed: {exc}")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


SYNTHESIS_DIMENSIONS = ("palette", "typography", "material", "geometry", "motion")


def synthesis_evidence_status(refs: Any, path: str) -> str:
    if not isinstance(refs, list):
        fail(f"visual_knowledge_integrity_failed: {path} must be an array")
    levels = set()
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            fail(f"visual_knowledge_integrity_failed: {path}[{index}] must be an object")
        source_level = ref.get("source_level")
        if source_level not in {"visual_system_catalog", "layout_template"}:
            fail(
                f"visual_knowledge_integrity_failed: {path}[{index}].source_level is unsupported"
            )
        levels.add(source_level)
    if levels == {"visual_system_catalog"}:
        return "direct_catalog_field"
    if levels == {"layout_template"}:
        return "direct_layout_level"
    if not levels:
        return "coverage_gap_no_matching_layout"
    fail(f"visual_knowledge_integrity_failed: {path} mixes evidence levels")


def validate_synthesis_candidate_census(library: Any) -> None:
    if not isinstance(library, dict):
        fail("visual_knowledge_integrity_failed: synthesis qualitative library is invalid")
    census = library.get("candidate_census", [])
    bundles = {
        bundle.get("id"): bundle
        for bundle in library.get("evidence_bundles", [])
        if isinstance(bundle, dict)
    }
    for index, item in enumerate(census):
        path = f"synthesis.candidate_census[{index}]"
        if not isinstance(item, dict):
            fail(f"visual_knowledge_integrity_failed: {path} must be an object")
        family_id = item.get("id")
        comparisons = item.get("qualitative_dimension_comparison")
        dimension_refs = item.get("dimension_evidence_refs")
        if (
            not isinstance(comparisons, dict)
            or set(comparisons) != set(SYNTHESIS_DIMENSIONS)
            or not isinstance(dimension_refs, dict)
            or set(dimension_refs) != set(SYNTHESIS_DIMENSIONS)
        ):
            fail(
                f"visual_knowledge_integrity_failed: {path} lacks complete dimension evidence"
            )
        flattened_refs = []
        for dimension in SYNTHESIS_DIMENSIONS:
            refs = dimension_refs[dimension]
            expected_status = synthesis_evidence_status(
                refs, f"{path}.dimension_evidence_refs.{dimension}"
            )
            if comparisons[dimension] != expected_status:
                fail(
                    "visual_knowledge_integrity_failed: "
                    f"{path}.{dimension} status disagrees with evidence source level"
                )
            flattened_refs.extend(refs)
        if item.get("evidence_refs") != flattened_refs:
            fail(
                f"visual_knowledge_integrity_failed: {path}.evidence_refs do not equal dimension evidence"
            )
        if item.get("status") == "retained":
            bundle = bundles.get(family_id)
            if not isinstance(bundle, dict):
                fail(
                    f"visual_knowledge_integrity_failed: {path} has no executable retained bundle"
                )
            traits = bundle.get("traits", {})
            for dimension in SYNTHESIS_DIMENSIONS:
                trait = traits.get(dimension)
                if (
                    not isinstance(trait, dict)
                    or trait.get("evidence_refs") != dimension_refs[dimension]
                ):
                    fail(
                        "visual_knowledge_integrity_failed: "
                        f"{path}.{dimension} evidence differs from executable bundle"
                    )


def load_synthesis_knowledge() -> dict[str, Any]:
    knowledge = load_json(SYNTHESIS_TRAITS_PATH, "synthesis trait asset")
    expected_groups = {"palette", "typography", "material", "geometry", "motion"}
    coverage = knowledge.get("source_coverage", {})
    catalog = coverage.get("visual_system_catalog", {})
    layouts = coverage.get("reference_layouts", {})
    scenes = coverage.get("scene_candidates", {})
    if (
        knowledge.get("schema") != "smart-video.synthesis-traits"
        or knowledge.get("role") != "aggregate_clean_room_synthesis_knowledge_not_finished_styles"
        or knowledge.get("prototype_role") != "macro_structural_anchor_only"
        or set(knowledge.get("trait_groups", {})) != expected_groups
        or catalog.get("reviewed_count") != 24
        or catalog.get("direct_trait_count") != 18
        or catalog.get("coverage_gap_count") != 6
        or layouts.get("measured_count") != 30
        or scenes.get("measured_count") != 216
    ):
        fail("visual_knowledge_integrity_failed: synthesis trait asset is inconsistent")
    library = knowledge.get("qualitative_trait_library", {})
    census = library.get("candidate_census", [])
    bundles = library.get("evidence_bundles", [])
    census_ids = {item.get("id") for item in census if isinstance(item, dict)}
    retained_ids = {
        item.get("id") for item in census
        if isinstance(item, dict) and item.get("status") == "retained"
    }
    if (
        len(census) != 18
        or len(census_ids) != 18
        or not {item.get("status") for item in census} <= {
            "retained", "excluded_redundant", "coverage_gap",
        }
        or sum(item.get("status") == "retained" for item in census) != 16
        or sum(item.get("status") == "coverage_gap" for item in census) != 2
        or any(not item.get("evidence_refs") or not item.get("decision_reason") for item in census)
        or any(not item.get("qualitative_dimension_comparison") for item in census)
        or any(
            item.get("status") == "excluded_redundant" and not item.get("measured_distance")
            for item in census
        )
        or any(not item.get("applicability") for item in census)
        or {item.get("id") for item in bundles} != retained_ids
        or any(not item.get("applicability") for item in bundles)
        or "observed_associations" in library
    ):
        fail("visual_knowledge_integrity_failed: synthesis candidate census is inconsistent")
    validate_synthesis_candidate_census(library)
    return knowledge


def synthesis_metric_envelope(
    knowledge: dict[str, Any], group: str, metric: str
) -> tuple[float, float]:
    sources = knowledge["trait_groups"][group]["aggregate_measurement_sources"]
    envelopes = [
        source["metric_envelopes"][metric]
        for source in sources.values()
        if metric in source["metric_envelopes"]
    ]
    if not envelopes:
        fail(f"visual_knowledge_integrity_failed: synthesis metric {group}.{metric} is absent")
    return (
        min(float(envelope["minimum"]) for envelope in envelopes),
        max(float(envelope["maximum"]) for envelope in envelopes),
    )


def select_style_traits(
    brief: dict[str, Any],
    semantic_profile: dict[str, Any],
    synthesis: dict[str, Any],
    slides: list[dict[str, Any]],
    qualitative_family_intent: dict[str, Any],
) -> dict[str, Any]:
    library = synthesis["qualitative_trait_library"]
    bundles = library["evidence_bundles"]
    groups = ("palette", "typography", "material", "geometry", "motion")
    qualitative_input = {
        "brief": {
            field: brief[field]
            for field in (
                "topic", "goal", "audience", "evidence_boundary", "visual_tone",
                "language", "aspect_ratio", "confirmed_revision",
            )
        },
        "semantic_profile": semantic_profile,
        "slide_semantics": [
            {
                "primary_claim": slide["primary_claim"],
                "communication_operation_enum": slide["communication_intent"]["communication_operation_enum"],
                "relationship_kind": slide["director_visual_intent"]["primary_relationship"]["kind"],
                "background_mode": slide["background_mode"],
            }
            for slide in slides
        ],
        "qualitative_family_intent": qualitative_family_intent,
    }
    selected_family_id = qualitative_family_intent["selected_family_id"]
    background_modes = {slide["background_mode"] for slide in slides}
    bundle_by_id = {bundle["id"]: bundle for bundle in bundles}
    selected_bundle = bundle_by_id[selected_family_id]
    allowed_backgrounds = set(
        selected_bundle["applicability"]["allowed_background_modes"]
    )
    if not background_modes <= allowed_backgrounds:
        fail(
            "coverage_gap_no_style_traits: requested observed family "
            f"{selected_family_id} is incompatible with the Slide backgrounds"
        )
    selected_by_group = {
        group: {
            "bundle_id": selected_family_id,
            "trait_id": selected_bundle["traits"][group]["id"],
            "evidence_refs": selected_bundle["traits"][group]["evidence_refs"],
            "qualitative_values": selected_bundle["traits"][group]["qualitative_values"],
        }
        for group in groups
    }
    return {
        "prototype_role": "macro_structural_anchor_only",
        "selection_source": "system_qualitative_semantic_trait_selector",
        "selection_mode": "source_bound_qualitative_family_intent",
        "qualitative_family_profile": {
            "source": "system_source_bound_qualitative_family_intent",
            "input_sha256": sha256_bytes(canonical_json_bytes(qualitative_input)),
            "selected_family_id": selected_family_id,
            "candidate_family_ids": qualitative_family_intent["candidate_family_ids"],
            "candidate_count": 1,
        },
        "selected_trait_ids": {
            group: selected_by_group[group]["trait_id"] for group in groups
        },
        "selected_bundle_ids": {
            group: selected_by_group[group]["bundle_id"] for group in groups
        },
        "selected_qualitative_values": {
            group: selected_by_group[group]["qualitative_values"] for group in groups
        },
        "evidence_refs": [
            {"trait_id": selected_by_group[group]["trait_id"], **evidence}
            for group in groups
            for evidence in selected_by_group[group]["evidence_refs"]
        ],
        "combination_score": 0.0,
        "mutual_exclusion_check": "pass",
        "applicability_boundary_check": "pass",
        "trait_substitution": False,
        "source_token_copy": False,
    }


def require_sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        fail(f"{path} must be a lowercase SHA-256")
    return value


def reject_public_projection(value: Any, path: str) -> None:
    stack: list[tuple[Any, str]] = [(value, path)]
    while stack:
        node, node_path = stack.pop()
        if isinstance(node, dict):
            for key, child in reversed(tuple(node.items())):
                child_path = f"{node_path}.{key}"
                if key == "public_projection":
                    fail(f"public_projection is forbidden at {child_path}")
                stack.append((child, child_path))
        elif isinstance(node, list):
            stack.extend((child, f"{node_path}[{index}]") for index, child in reversed(tuple(enumerate(node))))


def validate_identity(value: Any, path: str) -> dict[str, Any]:
    identity = strict_object(value, path, IDENTITY_FIELDS)
    for field in sorted(IDENTITY_FIELDS):
        require_string(identity[field], f"{path}.{field}")
    return identity


def validate_strategy(value: Any, path: str, parent: dict[str, Any]) -> dict[str, Any]:
    strategy = strict_object(value, path, {"id", "version", "selection_source"})
    if strategy != PRODUCTION_STRATEGY:
        fail(f"{path} must equal the production strategy tuple")
    return strategy


def require_unique_strings(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        fail(f"{path} must be a {qualifier}array")
    strings = [require_string(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if len(strings) != len(set(strings)):
        fail(f"{path} must contain unique values")
    return strings


def semantic_slide_payload(slide: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(slide)
    payload.pop("grammar_id", None)
    director = payload.get("director_visual_intent")
    if isinstance(director, dict):
        director.pop("visual_system_targets", None)
    return payload


def source_content_for_slide(slide: dict[str, Any]) -> dict[str, Any]:
    return {
        "screen_content": [
            {
                "content_id": item["id"],
                "text": item["text"],
                "source_binding_ids": item["source_binding_ids"],
            }
            for item in slide["content_objects"]
        ],
        "source_bindings": slide["source_bindings"],
    }


def _spacing_tokens_for_semantic_load(semantic_load: int | float) -> dict[str, Any]:
    """Map whole-video semantic load to a monotonic, clamped density scale."""
    load = min(
        MAX_EFFECTIVE_SEMANTIC_LOAD,
        max(MIN_EFFECTIVE_SEMANTIC_LOAD, float(semantic_load)),
    )
    position = (
        (load - MIN_EFFECTIVE_SEMANTIC_LOAD)
        / (MAX_EFFECTIVE_SEMANTIC_LOAD - MIN_EFFECTIVE_SEMANTIC_LOAD)
    )
    group_gap = round(32.0 - 12.0 * position, 2)
    section_gap = round(group_gap * 2.0, 2)
    return {
        "base_unit_px": 8,
        "scale_px": [8, 16, 24, 32, 48, 64],
        "group_gap_px": group_gap,
        "section_gap_px": section_gap,
        "safe_area_px": {
            "top": section_gap,
            "right": round(section_gap + group_gap, 2),
            "bottom": section_gap,
            "left": round(section_gap + group_gap, 2),
        },
    }


def validate_target_intervals(
    value: Any,
    path: str,
    *,
    required_metrics: set[str],
) -> dict[str, Any]:
    intervals = strict_object(value, path, required_metrics)
    for metric in sorted(required_metrics):
        interval_path = f"{path}.{metric}"
        interval = strict_object(
            intervals[metric], interval_path, {"lower", "upper", "basis_refs"}
        )
        lower = require_number(interval["lower"], f"{interval_path}.lower")
        upper = require_number(interval["upper"], f"{interval_path}.upper")
        if lower > upper:
            fail(f"invalid_source_or_intent: {interval_path} must be ordered")
        require_unique_strings(interval["basis_refs"], f"{interval_path}.basis_refs", nonempty=True)
    return intervals


def derive_visual_system_intent(
    brief: dict[str, Any], slides: list[dict[str, Any]], *, required_metrics: set[str]
) -> dict[str, Any]:
    target_intervals: dict[str, Any] = {}
    brief_targets = brief["visual_tone"]["target_intervals"]
    for metric in sorted(required_metrics):
        intervals = [brief_targets[metric]] + [
            slide["director_visual_intent"]["visual_system_targets"][metric]
            for slide in slides
        ]
        lower = max(interval["lower"] for interval in intervals)
        upper = min(interval["upper"] for interval in intervals)
        if lower > upper:
            fail(
                f"coverage_gap_no_prototype: visual-system intent has no shared interval for {metric}"
            )
        target_intervals[metric] = {
            "lower": lower,
            "upper": upper,
            "basis_refs": sorted({
                ref for interval in intervals for ref in interval["basis_refs"]
            }),
        }
    return {
        "schema_id": "smart-video.visual-system-intent.v1",
        "selector_version": "1.0.0",
        "target_intervals": target_intervals,
        "background_modes": sorted({slide["background_mode"] for slide in slides}),
        "basis": {
            "brief_sha256": sha256_bytes(canonical_json_bytes(brief)),
            "semantic_slide_set_sha256": sha256_bytes(canonical_json_bytes([
                semantic_slide_payload(slide) for slide in slides
            ])),
        },
    }


def select_prototype(
    intent: dict[str, Any], prototypes: dict[str, Any], path: str
) -> str:
    targets = intent["target_intervals"]
    candidates: list[tuple[str, list[float]]] = []
    for prototype in prototypes.get("items", []):
        priors = prototype.get("intent_intervals", {})
        if set(priors) != set(targets):
            continue
        distances: list[float] = []
        for metric in sorted(targets):
            target = targets[metric]
            prior = priors[metric]
            if target["upper"] < prior["lower"] or target["lower"] > prior["upper"]:
                break
            target_midpoint = (target["lower"] + target["upper"]) / 2.0
            scale = max(prior["upper"] - prior["lower"], 1.0e-9)
            distances.append(abs(target_midpoint - prior["preferred"]) / scale)
        else:
            candidates.append((prototype["id"], distances))
    if not candidates:
        fail(f"coverage_gap_no_prototype: {path} has no source-supported prototype overlap")
    if len(candidates) == 1:
        return candidates[0][0]

    def dominates(left: list[float], right: list[float]) -> bool:
        return all(a <= b for a, b in zip(left, right)) and any(
            a < b for a, b in zip(left, right)
        )

    dominant = [
        candidate_id
        for candidate_id, vector in candidates
        if all(
            other_id == candidate_id or dominates(vector, other_vector)
            for other_id, other_vector in candidates
        )
    ]
    if len(dominant) != 1:
        fail(
            f"ambiguous_visual_system_intent: {path} has multiple nondominated source-supported prototypes"
        )
    return dominant[0]


def validate_relationship(
    value: Any,
    path: str,
    *,
    content_ids: set[str],
    optional_control_fields: bool = False,
) -> tuple[str, str, list[str]]:
    optional = (
        {"communication_operation_enum", "visual_encoding_enum", "render_mode", "evidence_spans"}
        if optional_control_fields else set()
    )
    optional.update({
        "evidence_spans", "metric_relationship", "chronology_relationship",
        "formal_relationship",
    })
    relationship = strict_object(
        value, path, {"kind", "direction", "role_bindings"}, optional
    )
    kind = require_string(relationship["kind"], f"{path}.kind")
    direction = require_string(relationship["direction"], f"{path}.direction")
    bindings = relationship["role_bindings"]
    if not isinstance(bindings, list) or not bindings:
        fail(f"{path}.role_bindings must be a non-empty array")
    roles: list[str] = []
    for index, raw_binding in enumerate(bindings):
        binding_path = f"{path}.role_bindings[{index}]"
        binding = strict_object(raw_binding, binding_path, {"role", "content_object_ids"})
        roles.append(require_string(binding["role"], f"{binding_path}.role"))
        object_ids = require_unique_strings(
            binding["content_object_ids"], f"{binding_path}.content_object_ids", nonempty=True
        )
        if not set(object_ids) <= content_ids:
            fail(f"invalid_source_or_intent: {binding_path} references an unknown content object")
    if len(roles) != len(set(roles)):
        fail(f"{path}.role_bindings must bind each role exactly once")
    return kind, direction, roles


SOURCE_BOUND_METRIC_KINDS = {"paired_metric", "target_actual", "parts"}
METRIC_FACT_FIELDS = {
    "fact_id", "canonical_metric_id", "display_name", "dimension", "unit", "value",
}


def _resolve_json_pointer(document: Any, pointer: str, path: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        fail(f"semantic_critic_rejected: {path} source pointer is invalid")
    node = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            fail(f"semantic_critic_rejected: {path} source pointer does not resolve")
    return node


def _metric_number_text_matches(text: str, value: float) -> bool:
    numbers = [
        float(raw)
        for raw in re.findall(r"(?<![0-9.])-?\d+(?:\.\d+)?", text)
    ]
    return bool(numbers) and all(math.isclose(number, value, abs_tol=1.0e-9) for number in numbers)


def _validate_source_bound_metric_relationship(
    slide: dict[str, Any], relationship: dict[str, Any], path: str
) -> str | None:
    relationship_kind = relationship["kind"]
    raw_contract = relationship.get("metric_relationship")
    if relationship_kind not in SOURCE_BOUND_METRIC_KINDS:
        if raw_contract is not None:
            fail(f"semantic_critic_rejected: {path} does not permit a metric relationship contract")
        return None
    if raw_contract is None:
        fail(f"semantic_critic_rejected: {path} lacks a source-bound metric relationship")
    metric_contract = strict_object(
        raw_contract,
        f"{path}.metric_relationship",
        {"schema_id", "operand_bindings", "equation"},
    )
    if metric_contract["schema_id"] != "smart-video.source-bound-metric-relationship.v1":
        fail(f"semantic_critic_rejected: {path} metric relationship schema is unsupported")
    equation_path = f"{path}.metric_relationship.equation"
    raw_equation = metric_contract["equation"]
    if not isinstance(raw_equation, dict):
        fail(f"semantic_critic_rejected: {equation_path} must be an object")
    operator = require_string(raw_equation.get("operator"), f"{equation_path}.operator")
    required_fact_fields = (
        METRIC_FACT_FIELDS | {"uncertainty"}
        if operator == "divide_percent"
        else METRIC_FACT_FIELDS
    )

    content_by_id = {item["id"]: item for item in slide["content_objects"]}
    source_by_id = {item["id"]: item for item in slide["source_bindings"]}
    role_by_name = {
        item["role"]: item["content_object_ids"]
        for item in relationship["role_bindings"]
    }
    raw_bindings = metric_contract["operand_bindings"]
    if not isinstance(raw_bindings, list) or len(raw_bindings) != len(role_by_name):
        fail(f"semantic_critic_rejected: {path} metric relationship must bind every role exactly once")

    facts_by_role: dict[str, dict[str, Any]] = {}
    fact_ids: set[str] = set()
    for index, raw_binding in enumerate(raw_bindings):
        binding_path = f"{path}.metric_relationship.operand_bindings[{index}]"
        binding = strict_object(
            raw_binding, binding_path,
            {"role", "content_object_id", "source_binding_id"},
        )
        role = require_string(binding["role"], f"{binding_path}.role")
        object_id = require_string(
            binding["content_object_id"], f"{binding_path}.content_object_id"
        )
        source_id = require_string(
            binding["source_binding_id"], f"{binding_path}.source_binding_id"
        )
        if role in facts_by_role or role not in role_by_name or role_by_name[role] != [object_id]:
            fail(f"semantic_critic_rejected: {path} metric relationship role binding is not exact")
        content_object = content_by_id.get(object_id)
        source_binding = source_by_id.get(source_id)
        if (
            content_object is None
            or source_binding is None
            or source_id not in content_object["source_binding_ids"]
            or source_binding.get("kind") != "structured_metric"
        ):
            fail(f"semantic_critic_rejected: {path} metric relationship is not source-bound")
        source_binding = strict_object(
            source_binding,
            f"{path}.source_bindings[{source_id}]",
            {"id", "kind", "source_pointer", "metric_identity"},
        )
        fact = _resolve_json_pointer(
            slide["source_data"], source_binding["source_pointer"], binding_path
        )
        if not isinstance(fact, dict) or set(fact) != required_fact_fields:
            fail(f"semantic_critic_rejected: {path} source-bound metric fact is incomplete")
        fact_id = require_string(fact["fact_id"], f"{binding_path}.fact_id")
        if fact_id in fact_ids:
            fail(f"semantic_critic_rejected: {path} metric facts must be distinct source records")
        fact_ids.add(fact_id)
        for field in ("canonical_metric_id", "display_name", "dimension", "unit"):
            require_string(fact[field], f"{binding_path}.{field}")
        metric_identity = strict_object(
            source_binding["metric_identity"],
            f"{path}.source_bindings[{source_id}].metric_identity",
            {"canonical_metric_id", "display_name", "dimension", "unit"},
        )
        expected_identity = {
            field: fact[field]
            for field in ("canonical_metric_id", "display_name", "dimension", "unit")
        }
        if metric_identity != expected_identity:
            fail(
                f"semantic_critic_rejected: {path} metric identity does not match "
                "source-bound fact"
            )
        if type(fact["value"]) not in (int, float) or not math.isfinite(float(fact["value"])):
            fail(f"semantic_critic_rejected: {path} source-bound metric value must be finite")
        authoritative_text = content_object["text"]
        if (
            fact["display_name"].casefold() not in authoritative_text.casefold()
            or fact["unit"].casefold() not in authoritative_text.casefold()
            or not _metric_number_text_matches(authoritative_text, float(fact["value"]))
        ):
            fail(f"semantic_critic_rejected: {path} metric fact does not match authoritative role text")
        facts_by_role[role] = fact

    equation_fields = {"operator", "operand_roles", "result_role"}
    if operator == "divide_percent":
        equation_fields.add("comparison")
    equation = strict_object(raw_equation, equation_path, equation_fields)
    operand_roles = require_unique_strings(
        equation["operand_roles"], f"{equation_path}.operand_roles", nonempty=True
    )
    result_role = require_string(equation["result_role"], f"{equation_path}.result_role")
    if operator == "divide_percent" and (
        operand_roles != ["numerator", "denominator"] or result_role != "result"
    ):
        fail(
            f"semantic_critic_rejected: {path} divide_percent roles must be "
            "numerator, denominator, and result"
        )
    if result_role not in facts_by_role or any(role not in facts_by_role for role in operand_roles):
        fail(f"semantic_critic_rejected: {path} metric equation references an unknown role")
    if result_role in operand_roles:
        fail(f"semantic_critic_rejected: {path} metric equation result must be a distinct role")
    if set(operand_roles) | {result_role} != set(facts_by_role):
        fail(f"semantic_critic_rejected: {path} metric equation introduces an unrelated role")
    operand_values = [float(facts_by_role[role]["value"]) for role in operand_roles]
    if operator in {"subtract", "sum"}:
        metric_keys = {
            (
                fact["canonical_metric_id"],
                fact["display_name"],
                fact["dimension"],
                fact["unit"],
            )
            for fact in facts_by_role.values()
        }
        if len(metric_keys) != 1:
            fail(
                f"semantic_critic_rejected: {path} metric relationship requires one "
                "canonical metric identity including display name, dimension, and unit"
            )
        if operator == "subtract" and len(operand_values) == 2:
            expected = operand_values[0] - operand_values[1]
        elif operator == "sum" and len(operand_values) >= 2:
            expected = sum(operand_values)
        else:
            fail(f"semantic_critic_rejected: {path} metric equation operator is unsupported")
        if not math.isclose(
            expected,
            float(facts_by_role[result_role]["value"]),
            abs_tol=1.0e-9,
        ):
            fail(f"semantic_critic_rejected: {path} metric equation does not reconcile")
    elif operator == "divide_percent":
        if len(operand_roles) != 2:
            fail(
                f"semantic_critic_rejected: {path} divide_percent requires exactly "
                "two operand roles"
            )
        if any(
            fact["uncertainty"] != "approximate_from_source"
            for fact in facts_by_role.values()
        ):
            fail(
                f"semantic_critic_rejected: {path} divide_percent requires "
                "source-bound approximate uncertainty"
            )
        operand_keys = {
            (
                facts_by_role[role]["canonical_metric_id"],
                facts_by_role[role]["display_name"],
                facts_by_role[role]["dimension"],
                facts_by_role[role]["unit"],
            )
            for role in operand_roles
        }
        if len(operand_keys) != 1:
            fail(
                f"semantic_critic_rejected: {path} divide_percent operands require one "
                "canonical metric identity including display name, dimension, and unit"
            )
        result_fact = facts_by_role[result_role]
        if result_fact["dimension"] != "ratio" or result_fact["unit"] != "percent":
            fail(
                f"semantic_critic_rejected: {path} divide_percent result must have "
                "dimension ratio and unit percent"
            )
        comparison = strict_object(
            equation["comparison"],
            f"{equation_path}.comparison",
            {"mode", "decimal_places"},
        )
        if comparison["mode"] != "rounded":
            fail(
                f"semantic_critic_rejected: {path} divide_percent comparison mode "
                "must be rounded"
            )
        decimal_places = comparison["decimal_places"]
        if type(decimal_places) is not int or decimal_places < 0:
            fail(
                f"semantic_critic_rejected: {path} divide_percent decimal_places "
                "must be a non-negative integer"
            )
        result_binding = next(
            binding for binding in raw_bindings if binding["role"] == result_role
        )
        result_text = content_by_id[result_binding["content_object_id"]]["text"]
        result_tokens = re.findall(r"(?<![0-9.])-?\d+(?:\.\d+)?", result_text)
        result_precisions = {
            len(token.partition(".")[2]) if "." in token else 0
            for token in result_tokens
        }
        if result_precisions != {decimal_places}:
            fail(
                f"semantic_critic_rejected: {path} divide_percent decimal_places does "
                "not match authoritative result text"
            )
        numerator = Decimal(str(facts_by_role[operand_roles[0]]["value"]))
        denominator = Decimal(str(facts_by_role[operand_roles[1]]["value"]))
        if denominator <= 0:
            fail(f"semantic_critic_rejected: {path} divide_percent denominator must be positive")
        stated_result = Decimal(str(result_fact["value"]))
        half_unit = Decimal(5).scaleb(-decimal_places - 1)
        with localcontext() as context:
            context.prec = 50
            computed_percent = numerator / denominator * Decimal(100)
        if not (
            stated_result - half_unit <= computed_percent
            < stated_result + half_unit
        ):
            fail(
                f"semantic_critic_rejected: {path} divide_percent result is outside "
                "the declared rounding interval"
            )
    else:
        fail(f"semantic_critic_rejected: {path} metric equation operator is unsupported")
    return sha256_bytes(canonical_json_bytes({
        "metric_relationship": metric_contract,
        "resolved_facts": facts_by_role,
    }))


CHRONOLOGY_EVENT_FIELDS = {
    "event_id", "chronology_id", "label", "display_order_value",
    "normalized_order_value",
}
CHRONOLOGY_ORDER_FIELDS = {
    "chronology_id", "order_direction", "ordered_event_ids", "relation_statement",
}


def _authoritative_slide_field(slide: dict[str, Any], field: str, path: str) -> str:
    if field == "narration":
        return slide["narration"]
    if field == "source_excerpt":
        return slide["source_excerpt"]
    if field == "primary_claim.text":
        return slide["primary_claim"]["text"]
    fail(f"semantic_critic_rejected: {path}.authoritative_field is unsupported")


def _validate_source_bound_chronology_relationship(
    slide: dict[str, Any], relationship: dict[str, Any], operation: str, path: str
) -> str | None:
    raw_contract = relationship.get("chronology_relationship")
    if operation != "chronology_schedule":
        if raw_contract is not None:
            fail(
                f"semantic_critic_rejected: {path} does not permit a chronology relationship contract"
            )
        return None
    if raw_contract is None:
        fail(
            f"semantic_critic_rejected: {path} lacks a source-bound chronology relationship"
        )
    chronology_contract = strict_object(
        raw_contract,
        f"{path}.chronology_relationship",
        {"schema_id", "event_bindings", "ordering"},
    )
    if (
        chronology_contract["schema_id"]
        != "smart-video.source-bound-chronology-relationship.v1"
    ):
        fail(f"semantic_critic_rejected: {path} chronology relationship schema is unsupported")

    content_by_id = {item["id"]: item for item in slide["content_objects"]}
    source_by_id = {item["id"]: item for item in slide["source_bindings"]}
    role_objects = {
        item["role"]: item["content_object_ids"]
        for item in relationship["role_bindings"]
    }
    expected_pairs = {
        (role, object_id)
        for role, object_ids in role_objects.items()
        for object_id in object_ids
    }
    raw_event_bindings = chronology_contract["event_bindings"]
    if not isinstance(raw_event_bindings, list) or not raw_event_bindings:
        fail(f"semantic_critic_rejected: {path} chronology event bindings must be non-empty")

    resolved_events: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_source_ids: set[str] = set()
    seen_event_ids: set[str] = set()
    for index, raw_binding in enumerate(raw_event_bindings):
        binding_path = f"{path}.chronology_relationship.event_bindings[{index}]"
        binding = strict_object(
            raw_binding,
            binding_path,
            {"role", "content_object_id", "source_binding_id"},
        )
        role = require_string(binding["role"], f"{binding_path}.role")
        object_id = require_string(
            binding["content_object_id"], f"{binding_path}.content_object_id"
        )
        source_id = require_string(
            binding["source_binding_id"], f"{binding_path}.source_binding_id"
        )
        pair = (role, object_id)
        if pair not in expected_pairs or pair in seen_pairs:
            fail(f"semantic_critic_rejected: {path} chronology role/event binding is not exact")
        seen_pairs.add(pair)
        if source_id in seen_source_ids:
            fail(f"semantic_critic_rejected: {path} chronology events reuse a source record")
        seen_source_ids.add(source_id)
        content_object = content_by_id.get(object_id)
        source_binding = source_by_id.get(source_id)
        if (
            content_object is None
            or source_binding is None
            or source_id not in content_object["source_binding_ids"]
            or source_binding.get("kind") != "structured_chronology_event"
        ):
            fail(f"semantic_critic_rejected: {path} chronology event is not source-bound")
        source_binding = strict_object(
            source_binding,
            f"{path}.source_bindings[{source_id}]",
            {"id", "kind", "source_pointer", "chronology_identity"},
        )
        identity = strict_object(
            source_binding["chronology_identity"],
            f"{path}.source_bindings[{source_id}].chronology_identity",
            {"chronology_id"},
        )
        fact = _resolve_json_pointer(
            slide["source_data"], source_binding["source_pointer"], binding_path
        )
        if not isinstance(fact, dict) or set(fact) != CHRONOLOGY_EVENT_FIELDS:
            fail(f"semantic_critic_rejected: {path} source-bound chronology event is incomplete")
        event_id = require_string(fact["event_id"], f"{binding_path}.event_id")
        if event_id in seen_event_ids:
            fail(f"semantic_critic_rejected: {path} chronology event IDs must be distinct")
        seen_event_ids.add(event_id)
        chronology_id = require_string(
            fact["chronology_id"], f"{binding_path}.chronology_id"
        )
        label = require_string(fact["label"], f"{binding_path}.label")
        display_order = require_string(
            fact["display_order_value"], f"{binding_path}.display_order_value"
        )
        if identity["chronology_id"] != chronology_id:
            fail(f"semantic_critic_rejected: {path} chronology identity differs from source event")
        order_value = fact["normalized_order_value"]
        if type(order_value) not in (int, float) or not math.isfinite(float(order_value)):
            fail(f"semantic_critic_rejected: {path} chronology normalized order must be finite")
        authoritative_text = content_object["text"]
        if label not in authoritative_text or display_order not in authoritative_text:
            fail(f"semantic_critic_rejected: {path} chronology event does not match role text")
        resolved_events.append({
            "role": role,
            "content_object_id": object_id,
            "source_binding_id": source_id,
            "fact": fact,
        })
    if seen_pairs != expected_pairs:
        fail(f"semantic_critic_rejected: {path} chronology relationship must bind every role event")

    ordering_path = f"{path}.chronology_relationship.ordering"
    ordering = strict_object(
        chronology_contract["ordering"],
        ordering_path,
        {
            "source_binding_id", "content_object_id", "ordered_roles", "order_direction",
            "authoritative_field", "quote",
        },
    )
    ordering_source_id = require_string(
        ordering["source_binding_id"], f"{ordering_path}.source_binding_id"
    )
    ordering_object_id = require_string(
        ordering["content_object_id"], f"{ordering_path}.content_object_id"
    )
    if ordering_source_id in seen_source_ids:
        fail(f"semantic_critic_rejected: {path} chronology ordering must use a distinct source record")
    ordering_source = source_by_id.get(ordering_source_id)
    ordering_object = content_by_id.get(ordering_object_id)
    if (
        ordering_source is None
        or ordering_object is None
        or ordering_source_id not in ordering_object["source_binding_ids"]
        or ordering_source.get("kind") != "structured_chronology_order"
    ):
        fail(f"semantic_critic_rejected: {path} chronology ordering is not source-bound")
    ordering_source = strict_object(
        ordering_source,
        f"{path}.source_bindings[{ordering_source_id}]",
        {"id", "kind", "source_pointer", "chronology_identity"},
    )
    ordering_identity = strict_object(
        ordering_source["chronology_identity"],
        f"{path}.source_bindings[{ordering_source_id}].chronology_identity",
        {"chronology_id"},
    )
    order_record = _resolve_json_pointer(
        slide["source_data"], ordering_source["source_pointer"], ordering_path
    )
    if not isinstance(order_record, dict) or set(order_record) != CHRONOLOGY_ORDER_FIELDS:
        fail(f"semantic_critic_rejected: {path} source-bound chronology ordering is incomplete")
    chronology_ids = {item["fact"]["chronology_id"] for item in resolved_events}
    chronology_ids.add(order_record["chronology_id"])
    chronology_ids.add(ordering_identity["chronology_id"])
    if len(chronology_ids) != 1:
        fail(f"semantic_critic_rejected: {path} chronology events do not share one identity")
    direction = require_string(ordering["order_direction"], f"{ordering_path}.order_direction")
    if direction not in {"ascending", "descending"} or order_record["order_direction"] != direction:
        fail(f"semantic_critic_rejected: {path} chronology order direction is inconsistent")
    ordered_roles_raw = ordering["ordered_roles"]
    if not isinstance(ordered_roles_raw, list) or not ordered_roles_raw:
        fail(f"{ordering_path}.ordered_roles must be a non-empty array")
    ordered_roles = [
        require_string(role, f"{ordering_path}.ordered_roles[{index}]")
        for index, role in enumerate(ordered_roles_raw)
    ]
    resolved_roles = [item["role"] for item in resolved_events]
    role_positions = {role: index for index, role in enumerate(role_objects)}
    if ordered_roles != resolved_roles or any(
        role_positions[left] > role_positions[right]
        for left, right in zip(resolved_roles, resolved_roles[1:])
    ):
        fail(f"semantic_critic_rejected: {path} chronology order does not match relationship roles")
    event_ids = [item["fact"]["event_id"] for item in resolved_events]
    if order_record["ordered_event_ids"] != event_ids:
        fail(f"semantic_critic_rejected: {path} chronology order does not match source events")
    order_values = [float(item["fact"]["normalized_order_value"]) for item in resolved_events]
    comparator = (lambda left, right: left < right) if direction == "ascending" else (
        lambda left, right: left > right
    )
    if not all(comparator(left, right) for left, right in zip(order_values, order_values[1:])):
        fail(f"semantic_critic_rejected: {path} chronology normalized order is not strict")
    quote = require_string(ordering["quote"], f"{ordering_path}.quote")
    field = require_string(
        ordering["authoritative_field"], f"{ordering_path}.authoritative_field"
    )
    if field == "content_object.text":
        authoritative = ordering_object["text"]
    else:
        authoritative = _authoritative_slide_field(slide, field, ordering_path)
    if quote != order_record["relation_statement"] or quote not in authoritative:
        fail(f"semantic_critic_rejected: {path} chronology ordering statement is not authoritative")
    return sha256_bytes(canonical_json_bytes({
        "chronology_relationship": chronology_contract,
        "resolved_events": resolved_events,
        "resolved_ordering": order_record,
    }))


FORMAL_RELATION_TYPES = {
    "correction_reversal": "reversal",
    "definition_classification": "classification_membership",
    "question_resolution": "question_resolution",
    "linear_process_progression": "ordered_progression",
    "causal_mechanism": "directed_causation",
    "entity_network_dependency": "directed_dependency",
    "evidence_binding": "claim_support",
    "spatial_geography_route": "spatial_path",
    "hierarchy_layers": "parent_child_layers",
    "cycle_feedback": "closed_feedback",
    "transformation_change": "state_transition",
    "quantitative_rank_summary": "ordered_rank",
    "distribution_association": "statistical_association",
    "trend_forecast": "ordered_series_change",
}
FORMAL_PARTICIPANT_FIELDS = {
    "participant_id", "relationship_id", "role", "content_object_id",
    "statement", "ordinal",
}
FORMAL_RELATION_RECORD_FIELDS = {
    "relationship_id", "operation", "relation_type", "relationship_kind",
    "direction", "participant_ids", "role_cardinality", "object_cardinality",
    "closed_cycle", "relation_statement",
}


def _validate_source_bound_formal_relationship(
    slide: dict[str, Any], relationship: dict[str, Any], operation: str, path: str
) -> str | None:
    raw_contract = relationship.get("formal_relationship")
    expected_relation_type = FORMAL_RELATION_TYPES.get(operation)
    if expected_relation_type is None:
        if raw_contract is not None:
            fail(
                f"semantic_critic_rejected: {path} does not permit a formal relationship contract"
            )
        return None
    if raw_contract is None:
        fail(f"semantic_critic_rejected: {path} lacks a source-bound formal relationship")

    contract = strict_object(
        raw_contract,
        f"{path}.formal_relationship",
        {"schema_id", "participant_bindings", "relation_record_binding"},
    )
    if contract["schema_id"] != "smart-video.source-bound-formal-relationship.v1":
        fail(f"semantic_critic_rejected: {path} formal relationship schema is unsupported")

    content_by_id = {item["id"]: item for item in slide["content_objects"]}
    source_by_id = {item["id"]: item for item in slide["source_bindings"]}
    expected_pairs = [
        (role_binding["role"], object_id)
        for role_binding in relationship["role_bindings"]
        for object_id in role_binding["content_object_ids"]
    ]
    raw_bindings = contract["participant_bindings"]
    if not isinstance(raw_bindings, list) or len(raw_bindings) != len(expected_pairs):
        fail(
            f"semantic_critic_rejected: {path} formal relationship must bind every role object"
        )

    resolved_participants: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_source_ids: set[str] = set()
    seen_source_pointers: set[str] = set()
    seen_participant_ids: set[str] = set()
    relationship_ids: set[str] = set()
    for index, raw_binding in enumerate(raw_bindings):
        binding_path = f"{path}.formal_relationship.participant_bindings[{index}]"
        binding = strict_object(
            raw_binding,
            binding_path,
            {"role", "content_object_id", "source_binding_id"},
        )
        role = require_string(binding["role"], f"{binding_path}.role")
        object_id = require_string(
            binding["content_object_id"], f"{binding_path}.content_object_id"
        )
        source_id = require_string(
            binding["source_binding_id"], f"{binding_path}.source_binding_id"
        )
        pair = (role, object_id)
        if pair not in expected_pairs or pair in seen_pairs:
            fail(
                f"semantic_critic_rejected: {path} formal participant binding is not exact"
            )
        seen_pairs.add(pair)
        if source_id in seen_source_ids:
            fail(
                f"semantic_critic_rejected: {path} formal participants reuse a source record"
            )
        seen_source_ids.add(source_id)

        content_object = content_by_id.get(object_id)
        source_binding = source_by_id.get(source_id)
        if (
            content_object is None
            or source_binding is None
            or source_id not in content_object["source_binding_ids"]
            or source_binding.get("kind") != "structured_relationship_participant"
        ):
            fail(f"semantic_critic_rejected: {path} formal participant is not source-bound")
        source_binding = strict_object(
            source_binding,
            f"{path}.source_bindings[{source_id}]",
            {"id", "kind", "source_pointer", "relationship_identity"},
        )
        source_pointer = require_string(
            source_binding["source_pointer"],
            f"{path}.source_bindings[{source_id}].source_pointer",
        )
        if source_pointer in seen_source_pointers:
            fail(
                f"semantic_critic_rejected: {path} formal participants reuse a source pointer"
            )
        seen_source_pointers.add(source_pointer)
        identity = strict_object(
            source_binding["relationship_identity"],
            f"{path}.source_bindings[{source_id}].relationship_identity",
            {"relationship_id"},
        )
        identity_id = require_string(
            identity["relationship_id"],
            f"{path}.source_bindings[{source_id}].relationship_identity.relationship_id",
        )
        fact = _resolve_json_pointer(slide["source_data"], source_pointer, binding_path)
        if not isinstance(fact, dict) or set(fact) != FORMAL_PARTICIPANT_FIELDS:
            fail(
                f"semantic_critic_rejected: {path} source-bound formal participant is incomplete"
            )
        participant_id = require_string(
            fact["participant_id"], f"{binding_path}.participant_id"
        )
        if participant_id in seen_participant_ids:
            fail(f"semantic_critic_rejected: {path} formal participant IDs must be distinct")
        seen_participant_ids.add(participant_id)
        fact_relationship_id = require_string(
            fact["relationship_id"], f"{binding_path}.relationship_id"
        )
        fact_role = require_string(fact["role"], f"{binding_path}.role")
        fact_object_id = require_string(
            fact["content_object_id"], f"{binding_path}.content_object_id"
        )
        statement = require_string(fact["statement"], f"{binding_path}.statement")
        ordinal = fact["ordinal"]
        if type(ordinal) is not int or ordinal != index:
            fail(
                f"semantic_critic_rejected: {path} formal participant order is not exact"
            )
        if (
            identity_id != fact_relationship_id
            or fact_role != role
            or fact_object_id != object_id
            or statement != content_object["text"]
        ):
            fail(
                f"semantic_critic_rejected: {path} formal participant differs from its authoritative role object"
            )
        relationship_ids.add(fact_relationship_id)
        resolved_participants.append({
            "role": role,
            "content_object_id": object_id,
            "source_binding_id": source_id,
            "fact": fact,
        })
    if [
        (item["role"], item["content_object_id"])
        for item in resolved_participants
    ] != expected_pairs:
        fail(
            f"semantic_critic_rejected: {path} formal participant order differs from role bindings"
        )

    record_path = f"{path}.formal_relationship.relation_record_binding"
    record_binding = strict_object(
        contract["relation_record_binding"],
        record_path,
        {
            "content_object_id", "source_binding_id", "authoritative_field", "quote",
        },
    )
    record_object_id = require_string(
        record_binding["content_object_id"], f"{record_path}.content_object_id"
    )
    record_source_id = require_string(
        record_binding["source_binding_id"], f"{record_path}.source_binding_id"
    )
    if record_source_id in seen_source_ids:
        fail(
            f"semantic_critic_rejected: {path} formal relation record must be source-distinct"
        )
    record_object = content_by_id.get(record_object_id)
    record_source = source_by_id.get(record_source_id)
    if (
        record_object is None
        or record_source is None
        or record_source_id not in record_object["source_binding_ids"]
        or record_source.get("kind") != "structured_relationship_record"
    ):
        fail(f"semantic_critic_rejected: {path} formal relation record is not source-bound")
    record_source = strict_object(
        record_source,
        f"{path}.source_bindings[{record_source_id}]",
        {"id", "kind", "source_pointer", "relationship_identity"},
    )
    record_pointer = require_string(
        record_source["source_pointer"],
        f"{path}.source_bindings[{record_source_id}].source_pointer",
    )
    if record_pointer in seen_source_pointers:
        fail(f"semantic_critic_rejected: {path} formal relation record reuses a source pointer")
    record_identity = strict_object(
        record_source["relationship_identity"],
        f"{path}.source_bindings[{record_source_id}].relationship_identity",
        {"relationship_id"},
    )
    record = _resolve_json_pointer(slide["source_data"], record_pointer, record_path)
    if not isinstance(record, dict) or set(record) != FORMAL_RELATION_RECORD_FIELDS:
        fail(f"semantic_critic_rejected: {path} source-bound formal relation is incomplete")
    record_relationship_id = require_string(
        record["relationship_id"], f"{record_path}.relationship_id"
    )
    relationship_ids.add(record_relationship_id)
    relationship_ids.add(require_string(
        record_identity["relationship_id"],
        f"{record_path}.relationship_identity.relationship_id",
    ))
    if len(relationship_ids) != 1:
        fail(f"semantic_critic_rejected: {path} formal records do not share one relationship ID")
    if (
        record["operation"] != operation
        or record["relation_type"] != expected_relation_type
        or record["relationship_kind"] != relationship["kind"]
        or record["direction"] != relationship["direction"]
    ):
        fail(
            f"semantic_critic_rejected: {path} formal relation topology does not match the selected operation"
        )
    expected_participant_ids = [
        item["fact"]["participant_id"] for item in resolved_participants
    ]
    if record["participant_ids"] != expected_participant_ids:
        fail(f"semantic_critic_rejected: {path} formal relation participants do not reconcile")
    if (
        type(record["role_cardinality"]) is not int
        or record["role_cardinality"] != len(relationship["role_bindings"])
        or type(record["object_cardinality"]) is not int
        or record["object_cardinality"] != len(expected_pairs)
        or type(record["closed_cycle"]) is not bool
        or record["closed_cycle"] is not (operation == "cycle_feedback")
    ):
        fail(f"semantic_critic_rejected: {path} formal relation cardinality is inconsistent")
    relation_statement = require_string(
        record["relation_statement"], f"{record_path}.relation_statement"
    )
    authoritative_field = require_string(
        record_binding["authoritative_field"], f"{record_path}.authoritative_field"
    )
    quote = require_string(record_binding["quote"], f"{record_path}.quote")
    if authoritative_field == "content_object.text":
        authoritative = record_object["text"]
    else:
        authoritative = _authoritative_slide_field(slide, authoritative_field, record_path)
    if quote != relation_statement or quote != authoritative:
        fail(
            f"semantic_critic_rejected: {path} formal relation statement is not an exact authoritative span"
        )
    return sha256_bytes(canonical_json_bytes({
        "formal_relationship": contract,
        "resolved_participants": resolved_participants,
        "resolved_relation": record,
    }))


def _semantic_text(slide: dict[str, Any]) -> str:
    values: list[str] = [
        slide["narration"], slide["source_excerpt"],
        slide["primary_claim"]["text"],
    ]
    values.extend(item["text"] for item in slide["content_objects"])

    def collect(node: Any) -> None:
        if isinstance(node, str):
            values.append(node)
        elif isinstance(node, list):
            for child in node:
                collect(child)
        elif isinstance(node, dict):
            for child in node.values():
                collect(child)

    for binding in slide["source_bindings"]:
        collect(binding)
    return "\n".join(values).casefold()


def _validate_relationship_evidence(
    slide: dict[str, Any], relationship: dict[str, Any], path: str
) -> str:
    spans = relationship.get("evidence_spans")
    if not isinstance(spans, list) or not spans:
        fail(f"semantic_critic_rejected: {path} lacks relationship evidence spans")
    content_by_id = {item["id"]: item for item in slide["content_objects"]}
    binding_by_id = {item["id"]: item for item in slide["source_bindings"]}
    role_object_ids = {
        object_id
        for binding in relationship["role_bindings"]
        for object_id in binding["content_object_ids"]
    }
    role_evidence: list[tuple[set[str], set[str], str]] = []
    for role_binding in relationship["role_bindings"]:
        object_ids = set(role_binding["content_object_ids"])
        source_ids = {
            source_id
            for object_id in object_ids
            for source_id in content_by_id[object_id]["source_binding_ids"]
        }
        authoritative_text = " ".join(
            content_by_id[object_id]["text"] for object_id in sorted(object_ids)
        )
        normalized_text = re.sub(r"\s+", " ", authoritative_text).strip().casefold()
        role_evidence.append((object_ids, source_ids, normalized_text))
    for index, (object_ids, source_ids, normalized_text) in enumerate(role_evidence):
        for other_object_ids, other_source_ids, other_text in role_evidence[index + 1:]:
            if object_ids & other_object_ids or source_ids & other_source_ids:
                slide_path = path.split(".director_visual_intent", 1)[0]
                fail(
                    f"semantic_critic_rejected: {slide_path} relationship roles reuse an authoritative object or source"
                )
            if normalized_text == other_text:
                slide_path = path.split(".director_visual_intent", 1)[0]
                fail(
                    f"semantic_critic_rejected: {slide_path} relationship roles repeat the same authoritative content"
                )
    covered: set[str] = set()
    for index, raw_span in enumerate(spans):
        span_path = f"{path}.evidence_spans[{index}]"
        span = strict_object(
            raw_span,
            span_path,
            {"content_object_id", "source_binding_id", "authoritative_field", "quote"},
        )
        object_id = require_string(span["content_object_id"], f"{span_path}.content_object_id")
        binding_id = require_string(span["source_binding_id"], f"{span_path}.source_binding_id")
        field = require_string(span["authoritative_field"], f"{span_path}.authoritative_field")
        quote = require_string(span["quote"], f"{span_path}.quote")
        if object_id not in role_object_ids or object_id not in content_by_id:
            fail(f"semantic_critic_rejected: {span_path} is not bound to a relationship role object")
        content_object = content_by_id[object_id]
        if binding_id not in content_object["source_binding_ids"] or binding_id not in binding_by_id:
            fail(f"semantic_critic_rejected: {span_path} is not bound to the role object's source")
        if field == "content_object.text":
            authoritative = content_object["text"]
        elif field == "narration":
            authoritative = slide["narration"]
        elif field == "source_excerpt":
            authoritative = slide["source_excerpt"]
        elif field == "primary_claim.text":
            authoritative = slide["primary_claim"]["text"]
        else:
            fail(f"semantic_critic_rejected: {span_path}.authoritative_field is unsupported")
        if quote not in authoritative:
            fail(f"semantic_critic_rejected: {span_path}.quote is not an exact authoritative span")
        covered.add(object_id)
    if covered != role_object_ids:
        fail(f"semantic_critic_rejected: {path} does not evidence every role object")
    return sha256_bytes(canonical_json_bytes({
        "role_bindings": relationship["role_bindings"],
        "evidence_spans": spans,
    }))


FIELD_LOCAL_STOPWORDS = {
    "actual", "and", "benchmark", "content", "evidence", "filing", "for",
    "from", "gap", "report", "source", "sourced", "the", "value", "with",
    "percent", "percentage", "point", "points",
}


def _field_local_role_texts(
    slide: dict[str, Any], relationship: dict[str, Any]
) -> dict[str, list[str]]:
    content_by_id = {item["id"]: item["text"] for item in slide["content_objects"]}
    return {
        binding["role"]: [
            content_by_id[object_id].casefold()
            for object_id in binding["content_object_ids"]
        ]
        for binding in relationship["role_bindings"]
    }


def _field_local_tokens(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z][a-z0-9_-]{2,}", text)
        if token not in FIELD_LOCAL_STOPWORDS
    }
    for sequence in re.findall(r"[\u3400-\u9fff]{2,}", text):
        for width in (2, 3, 4):
            tokens.update(
                sequence[index:index + width]
                for index in range(len(sequence) - width + 1)
            )
    return tokens


def _comparison_has_field_local_relation(
    role_texts: dict[str, list[str]], relationship_kind: str
) -> bool:
    roles = list(role_texts)
    if len(roles) != 3 or any(not role_texts[role] for role in roles):
        return False
    tokens = {
        role: set().union(*(_field_local_tokens(text) for text in texts))
        for role, texts in role_texts.items()
    }
    relation_markers = re.compile(
        r"\b(compare(?:d|s|ing)?|versus|vs\.?|contrast|difference|higher|lower|"
        r"greater than|less than|cannot replace|does not eliminate|target|actual|"
        r"benchmark|variance|option|benefit|limit|priority|leader|follower)\b|"
        r"对比|相比|差异|差距|大于|小于|高于|低于|不能替代|不等同于|不消除|目标|实际|基准|偏差"
    )
    joined = {role: "\n".join(texts) for role, texts in role_texts.items()}

    if relationship_kind in {"paired_metric", "target_actual"}:
        left, right, relation = roles
        left_numbers = re.findall(r"(?<![0-9.])-?\d+(?:\.\d+)?", joined[left])
        right_numbers = re.findall(r"(?<![0-9.])-?\d+(?:\.\d+)?", joined[right])
        return bool(
            left_numbers
            and right_numbers
            and relation_markers.search(joined[relation])
            and tokens[left] & tokens[right]
            and tokens[relation] & tokens[left]
            and tokens[relation] & tokens[right]
        )

    if relationship_kind == "multi_scenario":
        contexts, conditions, recommendation = roles
        return bool(
            len(set(role_texts[contexts])) >= 2
            and len(set(role_texts[conditions])) >= 2
            and relation_markers.search(joined[conditions])
            and tokens[conditions] & tokens[recommendation]
        )

    if relationship_kind == "benefit_risk":
        benefits, limits, boundary = roles
        return bool(
            relation_markers.search(joined[boundary])
            and tokens[boundary] & tokens[benefits]
            and tokens[boundary] & tokens[limits]
        )

    left, right, relation = roles
    return bool(
        relation_markers.search(joined[relation])
        and tokens[relation] & tokens[left]
        and tokens[relation] & tokens[right]
    )


def _semantic_critic_supports(
    operation: str,
    slide: dict[str, Any],
    relationship: dict[str, Any],
    *,
    metric_relationship_sha256: str | None = None,
    chronology_relationship_sha256: str | None = None,
    formal_relationship_sha256: str | None = None,
) -> bool:
    role_texts = _field_local_role_texts(slide, relationship)
    if operation == "focus_assertion":
        return bool(slide["primary_claim"]["text"].strip())
    if operation == "chronology_schedule":
        return chronology_relationship_sha256 is not None
    if operation in FORMAL_RELATION_TYPES:
        return formal_relationship_sha256 is not None
    if operation == "comparison_contrast":
        return (
            metric_relationship_sha256 is not None
            if relationship["kind"] in SOURCE_BOUND_METRIC_KINDS
            else _comparison_has_field_local_relation(role_texts, relationship["kind"])
        )
    if operation == "part_whole_contribution":
        return metric_relationship_sha256 is not None if relationship["kind"] == "parts" else False
    return False


def select_grammar_for_slide(
    slide: dict[str, Any], grammars: dict[str, Any], path: str
) -> dict[str, Any]:
    director = slide["director_visual_intent"]
    operation = director["communication_operation_enum"]
    relationship = director["primary_relationship"]
    roles = [item["role"] for item in relationship["role_bindings"]]
    matches = [
        (grammar, signature)
        for grammar in grammars.get("items", [])
        for signature in grammar.get("semantic_signatures", [])
        if operation == grammar.get("communication_operation_enum")
        and relationship["kind"] == signature.get("relationship_kind")
        and relationship["direction"] == signature.get("relationship_direction")
        and roles == signature.get("relationship_roles")
        and director["visual_encoding_enum"] == signature.get("visual_encoding_enum")
    ]
    if len(matches) != 1:
        fail(
            f"coverage_gap_no_grammar: {path} must match exactly one controlled grammar signature"
        )
    grammar, signature = matches[0]
    expected_relationship_contract = (
        "source_bound_metric_equation_v1"
        if relationship["kind"] in SOURCE_BOUND_METRIC_KINDS
        else "source_bound_chronology_order_v1"
        if operation == "chronology_schedule"
        else "source_bound_typed_relation_v1"
        if operation in FORMAL_RELATION_TYPES
        else "source_bound_role_evidence_v1"
    )
    if signature.get("relationship_validation_contract") != expected_relationship_contract:
        fail("visual_knowledge_integrity_failed: grammar relationship contract is inconsistent")
    relationship_hash = _validate_relationship_evidence(
        slide, relationship, f"{path}.director_visual_intent.primary_relationship"
    )
    metric_relationship_hash = _validate_source_bound_metric_relationship(
        slide, relationship, f"{path}.director_visual_intent.primary_relationship"
    )
    chronology_relationship_hash = _validate_source_bound_chronology_relationship(
        slide,
        relationship,
        operation,
        f"{path}.director_visual_intent.primary_relationship",
    )
    formal_relationship_hash = _validate_source_bound_formal_relationship(
        slide,
        relationship,
        operation,
        f"{path}.director_visual_intent.primary_relationship",
    )
    if not _semantic_critic_supports(
        operation,
        slide,
        relationship,
        metric_relationship_sha256=metric_relationship_hash,
        chronology_relationship_sha256=chronology_relationship_hash,
        formal_relationship_sha256=formal_relationship_hash,
    ):
        label = "chronology" if operation == "chronology_schedule" else operation
        if operation == "comparison_contrast":
            fail(
                f"semantic_critic_rejected: {path} lacks field-local comparison relation proof"
            )
        fail(f"semantic_critic_rejected: {path} lacks authoritative {label} evidence")
    decision = {
        "slide_id": slide["slide_id"],
        "grammar_id": grammar["id"],
        "signature_evidence_id": signature["evidence_id"],
        "semantic_input_sha256": sha256_bytes(canonical_json_bytes(semantic_slide_payload(slide))),
        "relationship_evidence_sha256": relationship_hash,
        "source": "system_semantic_critic",
    }
    if metric_relationship_hash is not None:
        decision.update({
            "metric_relationship_contract": "source_bound_metric_equation_v1",
            "metric_relationship_sha256": metric_relationship_hash,
        })
    if chronology_relationship_hash is not None:
        decision.update({
            "chronology_relationship_contract": "source_bound_chronology_order_v1",
            "chronology_relationship_sha256": chronology_relationship_hash,
        })
    if formal_relationship_hash is not None:
        decision.update({
            "formal_relationship_contract": "source_bound_typed_relation_v1",
            "formal_relationship_sha256": formal_relationship_hash,
        })
    return decision


def _semantic_design_profile(brief: dict[str, Any], slides: list[dict[str, Any]]) -> dict[str, Any]:
    slide_count = len(slides)
    object_count = sum(len(slide["content_objects"]) for slide in slides)
    relationship_count = sum(
        1 + len(slide["director_visual_intent"]["secondary_relationships"])
        for slide in slides
    )
    priority_count = sum(len(slide["director_visual_intent"]["information_priority"]) for slide in slides)
    order_count = sum(len(slide["director_visual_intent"]["presentation_order"]) for slide in slides)
    text_length = sum(
        len(slide["narration"]) + len(slide["primary_claim"]["text"])
        + sum(len(item["text"]) for item in slide["content_objects"])
        for slide in slides
    )
    avg_duration = sum(slide["duration_seconds"] for slide in slides) / slide_count
    structural_operations = {
        "linear_process_progression", "causal_mechanism", "cycle_feedback",
        "hierarchy_layers", "entity_network_dependency", "chronology_schedule",
    }
    structural_slide_count = sum(
        slide["director_visual_intent"]["communication_operation_enum"] in structural_operations
        for slide in slides
    )
    tone = brief["visual_tone"].casefold()
    restraint = 1.0 if re.search(r"restrained|minimal|clear|克制|清晰|简洁", tone) else 0.0
    structure = min(1.0, (
        relationship_count / max(slide_count * 2, 1)
        + structural_slide_count / slide_count
    ) / 2.0)
    density = min(1.0, object_count / max(slide_count * 6, 1))
    text_share = min(1.0, text_length / max(slide_count * 500, 1))
    hierarchy = min(1.0, priority_count / max(object_count, 1))
    return {
        "slide_count": slide_count,
        "content_object_count": object_count,
        "relationship_count": relationship_count,
        "information_priority_count": priority_count,
        "presentation_order_count": order_count,
        "average_duration_seconds": round(avg_duration, 6),
        "density_signal": round(density, 6),
        "structure_signal": round(structure, 6),
        "text_share_signal": round(text_share, 6),
        "hierarchy_signal": round(hierarchy, 6),
        "restraint_signal": round(restraint, 6),
    }


def _select_prototype_from_profile(
    profile: dict[str, Any], prototypes: dict[str, Any], path: str
) -> tuple[str, list[dict[str, Any]]]:
    expected = {
        "unified-cluster-1": {"density": 0.90, "structure": 0.35, "text": 0.30, "hierarchy": 0.55, "restraint": 0.35},
        "unified-cluster-2": {"density": 0.80, "structure": 0.95, "text": 0.45, "hierarchy": 0.60, "restraint": 0.20},
        "unified-cluster-3": {"density": 0.35, "structure": 0.35, "text": 0.95, "hierarchy": 0.95, "restraint": 0.45},
        "unified-cluster-4": {"density": 0.15, "structure": 0.10, "text": 0.35, "hierarchy": 0.40, "restraint": 0.95},
    }
    actual = {
        "density": profile["density_signal"],
        "structure": profile["structure_signal"],
        "text": profile["text_share_signal"],
        "hierarchy": profile["hierarchy_signal"],
        "restraint": profile["restraint_signal"],
    }
    available = {item["id"] for item in prototypes.get("items", [])}
    scores = []
    for prototype_id, target in expected.items():
        if prototype_id not in available:
            continue
        score = sum((actual[key] - target[key]) ** 2 for key in sorted(target))
        scores.append({"prototype_id": prototype_id, "normalized_distance": round(score, 9)})
    if not scores:
        fail(f"coverage_gap_no_prototype: {path} has no evidence-qualified prototype")
    scores.sort(key=lambda item: item["normalized_distance"])
    if len(scores) > 1 and math.isclose(
        scores[0]["normalized_distance"], scores[1]["normalized_distance"], abs_tol=1.0e-9
    ):
        fail(f"ambiguous_visual_system_intent: {path} has multiple equally supported prototypes")
    return scores[0]["prototype_id"], scores


def _system_target_intervals(prototype: dict[str, Any]) -> dict[str, Any]:
    return {
        metric: {
            "lower": interval["preferred"],
            "upper": interval["preferred"],
            "basis_refs": [
                "system.semantic_design_profile",
                interval["basis_evidence_id"],
            ],
        }
        for metric, interval in prototype["intent_intervals"].items()
    }


def validate_qualitative_family_intent(
    value: Any,
    visual_tone: str,
    synthesis: dict[str, Any],
    path: str,
) -> dict[str, Any]:
    intent = strict_object(
        value,
        path,
        {
            "schema_id", "resolution", "selected_family_id",
            "candidate_family_ids", "source_binding", "semantic_critic",
        },
    )
    if intent["schema_id"] != "smart-video.source-bound-qualitative-family-intent.v1":
        fail(f"{path}.schema_id is unsupported")
    source_binding = strict_object(
        intent["source_binding"],
        f"{path}.source_binding",
        {"field", "value_sha256"},
    )
    if source_binding["field"] != "brief.visual_tone":
        fail(f"{path}.source_binding.field must be brief.visual_tone")
    require_sha256(source_binding["value_sha256"], f"{path}.source_binding.value_sha256")
    if source_binding["value_sha256"] != sha256_bytes(canonical_json_bytes(visual_tone)):
        fail(
            f"blocked_stale_visual_selection: {path} source binding does not match "
            "brief.visual_tone"
        )
    critic = strict_object(
        intent["semantic_critic"],
        f"{path}.semantic_critic",
        {"id", "version"},
    )
    if critic != {"id": "visual-style-semantic-critic", "version": "1.0.0"}:
        fail(f"{path}.semantic_critic provenance tuple is unsupported")
    resolution = require_string(intent["resolution"], f"{path}.resolution")
    candidate_ids = require_unique_strings(
        intent["candidate_family_ids"],
        f"{path}.candidate_family_ids",
    )
    selected_family_id = intent["selected_family_id"]
    if selected_family_id is not None:
        require_string(selected_family_id, f"{path}.selected_family_id")
    census_by_id = {
        item["id"]: item
        for item in synthesis["qualitative_trait_library"]["candidate_census"]
    }
    if any(family_id not in census_by_id for family_id in candidate_ids):
        fail("coverage_gap_no_style_traits: qualitative family intent names an unknown family")
    if resolution == "ambiguous":
        if selected_family_id is not None or len(candidate_ids) < 2:
            fail(f"{path} ambiguous resolution is malformed")
        fail("ambiguous_visual_style_traits: qualitative family intent has multiple candidates")
    if resolution == "coverage_gap":
        if selected_family_id is not None:
            fail(f"{path} coverage-gap resolution may not select a family")
        fail("coverage_gap_no_style_traits: qualitative family intent is unresolved")
    if resolution != "resolved":
        fail(f"{path}.resolution is unsupported")
    if candidate_ids != [selected_family_id]:
        fail(f"{path} resolved identity must contain exactly its selected family")
    candidate = census_by_id.get(selected_family_id)
    if candidate is None:
        fail("coverage_gap_no_style_traits: qualitative family intent names an unknown family")
    if candidate["status"] != "retained":
        fail(
            "coverage_gap_no_style_traits: requested observed family "
            f"{selected_family_id} is not retained"
        )
    return deepcopy(intent)


def validate_visual_system_input(value: Any, path: str) -> dict[str, Any]:
    visual_input = strict_object(
        value,
        path,
        {
            "schema_id", "version", "immutable", "brief", "slides", "aspect_ratio",
            "local_runtime_capabilities", "compatibility_results", "risk_results",
            "visual_knowledge", "qualitative_family_intent",
        },
    )
    if visual_input["schema_id"] != "smart-video.visual-system-input.v1":
        fail(f"{path}.schema_id must be smart-video.visual-system-input.v1")
    if type(visual_input["version"]) is not int or visual_input["version"] != 1:
        fail(f"{path}.version must be 1")
    if visual_input["immutable"] is not True:
        fail(f"{path}.immutable must be true")
    brief = strict_object(
        visual_input["brief"], f"{path}.brief",
        {
            "topic", "goal", "audience", "evidence_boundary", "visual_tone",
            "broll_availability", "language", "aspect_ratio", "confirmed_revision",
        },
    )
    for field in ("topic", "goal", "audience", "evidence_boundary", "visual_tone", "language", "confirmed_revision"):
        require_string(brief[field], f"{path}.brief.{field}")
    if brief["aspect_ratio"] != "16:9" or visual_input["aspect_ratio"] != "16:9":
        fail(f"unsupported_aspect_ratio: {path} must be 16:9")
    broll = strict_object(
        brief["broll_availability"], f"{path}.brief.broll_availability", {"available", "note"}
    )
    if type(broll["available"]) is not bool or not isinstance(broll["note"], str):
        fail(f"{path}.brief.broll_availability is invalid")
    if not isinstance(visual_input["slides"], list) or not visual_input["slides"]:
        fail(f"blocked_incomplete_slide_set: {path}.slides must be a non-empty complete set")

    grammars = load_json(EXPRESSION_GRAMMARS_PATH, "expression grammar asset")
    prototypes = load_json(VISUAL_PROTOTYPES_PATH, "visual prototype asset")
    synthesis = load_synthesis_knowledge()
    qualitative_family_intent = validate_qualitative_family_intent(
        visual_input["qualitative_family_intent"],
        brief["visual_tone"],
        synthesis,
        f"{path}.qualitative_family_intent",
    )
    knowledge = visual_input["visual_knowledge"]
    expected_knowledge = {
        "grammar_version": grammars["version"],
        "grammar_asset_sha256": sha256_bytes(EXPRESSION_GRAMMARS_PATH.read_bytes()),
        "prototype_version": prototypes["version"],
        "prototype_asset_sha256": sha256_bytes(VISUAL_PROTOTYPES_PATH.read_bytes()),
        "synthesis_version": synthesis["version"],
        "synthesis_asset_sha256": sha256_bytes(SYNTHESIS_TRAITS_PATH.read_bytes()),
        "integrity_status": "current",
    }
    if knowledge != expected_knowledge:
        fail(f"visual_knowledge_integrity_failed: {path}.visual_knowledge is not current")

    slide_required = {
        "slide_id", "narration", "source_excerpt", "primary_claim", "content_objects",
        "communication_intent", "director_visual_intent", "source_bindings", "source_data",
        "shot_type", "background_mode", "duration_seconds", "explicit_user_rules",
        "user_rule_results",
    }
    director_required = {
        "communication_operation_enum", "primary_relationship", "secondary_relationships",
        "visual_encoding_enum", "render_mode", "primary_focus", "information_priority",
        "presentation_order", "simplicity_rules", "final_frame_requirement", "source_bindings",
    }
    grammar_decisions = []
    for index, slide in enumerate(visual_input["slides"]):
        slide_path = f"{path}.slides[{index}]"
        strict_object(slide, slide_path, slide_required)
        strict_object(slide["director_visual_intent"], f"{slide_path}.director_visual_intent", director_required)
        grammar_decisions.append(select_grammar_for_slide(slide, grammars, slide_path))

    profile = _semantic_design_profile(brief, visual_input["slides"])
    prototype_id, candidate_scores = _select_prototype_from_profile(profile, prototypes, path)
    prototype = next(item for item in prototypes["items"] if item["id"] == prototype_id)
    targets = _system_target_intervals(prototype)
    internal_brief = deepcopy(brief)
    internal_brief["visual_tone"] = {
        "description": brief["visual_tone"],
        "target_intervals": deepcopy(targets),
        "basis_refs": [
            "brief.visual_tone", "system.semantic_design_profile",
        ],
    }
    internal_slides = deepcopy(visual_input["slides"])
    for slide, grammar_decision in zip(internal_slides, grammar_decisions):
        slide["grammar_id"] = grammar_decision["grammar_id"]
        slide["director_visual_intent"]["visual_system_targets"] = deepcopy(targets)
    intent = derive_visual_system_intent(
        internal_brief,
        internal_slides,
        required_metrics=set(targets),
    )
    intent["selector_version"] = "2.0.0"
    intent["semantic_design_profile"] = profile
    intent["candidate_scores"] = candidate_scores
    selection = {
        "schema_id": "smart-video.prototype-selection.v1",
        "version": 1,
        "immutable": True,
        "brief": internal_brief,
        "slides": internal_slides,
        "aspect_ratio": visual_input["aspect_ratio"],
        "local_runtime_capabilities": deepcopy(visual_input["local_runtime_capabilities"]),
        "compatibility_results": deepcopy(visual_input["compatibility_results"]),
        "risk_results": deepcopy(visual_input["risk_results"]),
        "visual_knowledge": deepcopy(knowledge),
        "qualitative_family_intent": qualitative_family_intent,
        "visual_system_intent": intent,
        "prototype_id": prototype_id,
        "decision": "unique_match",
    }
    return {
        "input": visual_input,
        "selection": selection,
        "grammar_decisions": grammar_decisions,
    }


def validate_prototype_selection(value: Any, path: str) -> dict[str, Any]:
    selection = strict_object(
        value,
        path,
        {
            "schema_id", "version", "immutable", "brief", "slides",
            "aspect_ratio", "local_runtime_capabilities",
            "compatibility_results", "risk_results", "visual_knowledge",
            "qualitative_family_intent", "visual_system_intent", "prototype_id", "decision",
        },
    )
    if (
        selection["schema_id"] != "smart-video.prototype-selection.v1"
        or type(selection["version"]) is not int
        or selection["version"] != 1
        or selection["immutable"] is not True
    ):
        fail(f"blocked_stale_visual_selection: {path} must be immutable prototype-selection v1")

    brief = strict_object(
        selection["brief"],
        f"{path}.brief",
        {
            "topic", "goal", "audience", "evidence_boundary", "visual_tone",
            "broll_availability", "language", "aspect_ratio", "confirmed_revision",
        },
    )
    for field in (
        "topic", "goal", "audience", "evidence_boundary", "language", "confirmed_revision",
    ):
        require_string(brief[field], f"{path}.brief.{field}")
    if brief["aspect_ratio"] != "16:9":
        fail(f"unsupported_aspect_ratio: {path}.brief.aspect_ratio must be 16:9")
    broll = strict_object(
        brief["broll_availability"], f"{path}.brief.broll_availability", {"available", "note"}
    )
    if type(broll["available"]) is not bool:
        fail(f"{path}.brief.broll_availability.available must be a boolean")
    if not isinstance(broll["note"], str):
        fail(f"{path}.brief.broll_availability.note must be a string")

    if selection["aspect_ratio"] != "16:9":
        fail(f"unsupported_aspect_ratio: {path}.aspect_ratio must be 16:9")

    grammars = load_json(EXPRESSION_GRAMMARS_PATH, "expression grammar asset")
    prototypes = load_json(VISUAL_PROTOTYPES_PATH, "visual prototype asset")
    synthesis = load_synthesis_knowledge()
    knowledge = strict_object(
        selection["visual_knowledge"],
        f"{path}.visual_knowledge",
        {
            "grammar_version", "grammar_asset_sha256", "prototype_version",
            "prototype_asset_sha256", "synthesis_version",
            "synthesis_asset_sha256", "integrity_status",
        },
    )
    integrity_matches = (
        knowledge["integrity_status"] == "current"
        and knowledge["grammar_version"] == grammars.get("version")
        and knowledge["prototype_version"] == prototypes.get("version")
        and knowledge["grammar_asset_sha256"] == sha256_bytes(EXPRESSION_GRAMMARS_PATH.read_bytes())
        and knowledge["prototype_asset_sha256"] == sha256_bytes(VISUAL_PROTOTYPES_PATH.read_bytes())
        and knowledge["synthesis_version"] == synthesis.get("version")
        and knowledge["synthesis_asset_sha256"] == sha256_bytes(SYNTHESIS_TRAITS_PATH.read_bytes())
    )
    if not integrity_matches:
        fail(f"visual_knowledge_integrity_failed: {path}.visual_knowledge is not current")

    required_metrics = set(prototypes.get("items", [{}])[0].get("intent_intervals", {}))
    if not required_metrics or any(
        set(item.get("intent_intervals", {})) != required_metrics
        for item in prototypes.get("items", [])
    ):
        fail("visual_knowledge_integrity_failed: prototype intent dimensions are inconsistent")
    visual_tone = strict_object(
        brief["visual_tone"], f"{path}.brief.visual_tone",
        {"target_intervals", "basis_refs"}, {"description"},
    )
    if "description" in visual_tone:
        require_string(visual_tone["description"], f"{path}.brief.visual_tone.description")
    validate_qualitative_family_intent(
        selection["qualitative_family_intent"],
        visual_tone.get("description", ""),
        synthesis,
        f"{path}.qualitative_family_intent",
    )
    validate_target_intervals(
        visual_tone["target_intervals"],
        f"{path}.brief.visual_tone.target_intervals",
        required_metrics=required_metrics,
    )
    require_unique_strings(
        visual_tone["basis_refs"], f"{path}.brief.visual_tone.basis_refs", nonempty=True
    )

    slides = selection["slides"]
    if not isinstance(slides, list) or not slides:
        fail(f"blocked_incomplete_slide_set: {path}.slides must be a non-empty complete set")
    slide_ids: set[str] = set()
    for index, raw_slide in enumerate(slides):
        slide_path = f"{path}.slides[{index}]"
        slide = strict_object(
            raw_slide,
            slide_path,
            {
                "slide_id", "narration", "source_excerpt", "primary_claim",
                "content_objects", "communication_intent", "director_visual_intent",
                "source_bindings", "source_data", "shot_type", "background_mode",
                "duration_seconds", "explicit_user_rules", "user_rule_results", "grammar_id",
            },
        )
        slide_id = require_string(slide["slide_id"], f"{slide_path}.slide_id")
        if slide_id in slide_ids:
            fail(f"blocked_incomplete_slide_set: duplicate selector slide id {slide_id}")
        slide_ids.add(slide_id)
        shot_type = require_enum_string(slide["shot_type"], f"{slide_path}.shot_type")
        if shot_type not in SLIDE_SHOT_TYPES:
            fail(f"invalid_source_or_intent: {slide_path}.shot_type is unsupported")
        if slide["background_mode"] != SUPPORTED_BACKGROUNDS[shot_type]:
            fail(f"invalid_slide_environment: {slide_path}.background_mode is unsupported for {shot_type}")
        duration = require_number(slide["duration_seconds"], f"{slide_path}.duration_seconds", positive=True)
        if not MIN_SLIDE_DURATION_SECONDS <= duration <= MAX_SLIDE_DURATION_SECONDS:
            fail(
                f"invalid_slide_environment: {slide_path}.duration_seconds must be between "
                f"{MIN_SLIDE_DURATION_SECONDS} and {MAX_SLIDE_DURATION_SECONDS}"
            )
        rules = require_unique_strings(slide["explicit_user_rules"], f"{slide_path}.explicit_user_rules")
        results = slide["user_rule_results"]
        if not isinstance(results, list) or len(results) != len(rules):
            fail(f"coverage_gap_no_prototype: {slide_path}.user_rule_results must cover every explicit rule")
        result_rules: list[str] = []
        for result_index, raw_result in enumerate(results):
            result_path = f"{slide_path}.user_rule_results[{result_index}]"
            result = strict_object(raw_result, result_path, {"rule", "status"})
            result_rules.append(require_string(result["rule"], f"{result_path}.rule"))
            if result["status"] != "compatible":
                fail(f"coverage_gap_no_prototype: {result_path}.status must be compatible")
        if result_rules != rules:
            fail(f"coverage_gap_no_prototype: {slide_path}.user_rule_results do not match explicit rules")
        for field in ("narration", "source_excerpt"):
            require_string(slide[field], f"{slide_path}.{field}")
        source_bindings = slide["source_bindings"]
        if not isinstance(source_bindings, list) or not source_bindings:
            fail(f"{slide_path}.source_bindings must be a non-empty array")
        source_binding_ids: set[str] = set()
        for binding_index, binding in enumerate(source_bindings):
            binding_path = f"{slide_path}.source_bindings[{binding_index}]"
            if not isinstance(binding, dict):
                fail(f"{binding_path} must be an object")
            binding_id = require_string(binding.get("id"), f"{binding_path}.id")
            if binding_id in source_binding_ids:
                fail(f"invalid_source_or_intent: duplicate source binding id {binding_id}")
            source_binding_ids.add(binding_id)
            canonical_json_bytes(binding)
        content_objects = slide["content_objects"]
        if not isinstance(content_objects, list) or not content_objects:
            fail(f"{slide_path}.content_objects must be a non-empty array")
        content_ids: set[str] = set()
        for object_index, raw_object in enumerate(content_objects):
            object_path = f"{slide_path}.content_objects[{object_index}]"
            content_object = strict_object(
                raw_object, object_path, {"id", "text", "source_binding_ids"}
            )
            object_id = require_string(content_object["id"], f"{object_path}.id")
            if object_id in content_ids:
                fail(f"invalid_source_or_intent: duplicate content object id {object_id}")
            content_ids.add(object_id)
            if not isinstance(content_object["text"], str):
                fail(f"{object_path}.text must be a string")
            object_bindings = require_unique_strings(
                content_object["source_binding_ids"],
                f"{object_path}.source_binding_ids",
                nonempty=True,
            )
            if not set(object_bindings) <= source_binding_ids:
                fail(f"invalid_source_or_intent: {object_path} references an unknown source binding")
        primary_claim = strict_object(
            slide["primary_claim"], f"{slide_path}.primary_claim", {"text", "content_object_ids"}
        )
        require_string(primary_claim["text"], f"{slide_path}.primary_claim.text")
        claim_ids = require_unique_strings(
            primary_claim["content_object_ids"],
            f"{slide_path}.primary_claim.content_object_ids",
            nonempty=True,
        )
        if not set(claim_ids) <= content_ids:
            fail(f"invalid_source_or_intent: {slide_path}.primary_claim references an unknown content object")
        communication = strict_object(
            slide["communication_intent"],
            f"{slide_path}.communication_intent",
            {"communication_operation_enum", "content_object_ids"},
        )
        operation = require_string(
            communication["communication_operation_enum"],
            f"{slide_path}.communication_intent.communication_operation_enum",
        )
        intent_ids = require_unique_strings(
            communication["content_object_ids"],
            f"{slide_path}.communication_intent.content_object_ids",
            nonempty=True,
        )
        if not set(intent_ids) <= content_ids or not set(claim_ids) <= set(intent_ids):
            fail(f"invalid_source_or_intent: {slide_path}.communication_intent is not bound to the claim")
        director = strict_object(
            slide["director_visual_intent"],
            f"{slide_path}.director_visual_intent",
            {
                "communication_operation_enum", "primary_relationship",
                "secondary_relationships", "visual_encoding_enum", "render_mode",
                "primary_focus", "information_priority", "presentation_order",
                "visual_system_targets", "simplicity_rules", "final_frame_requirement",
                "source_bindings",
            },
        )
        if director["communication_operation_enum"] != operation:
            fail(f"invalid_source_or_intent: {slide_path} director operation differs from Communication Intent")
        visual_encoding = require_string(
            director["visual_encoding_enum"], f"{slide_path}.director_visual_intent.visual_encoding_enum"
        )
        director_render_mode = require_string(
            director["render_mode"], f"{slide_path}.director_visual_intent.render_mode"
        )
        if director_render_mode not in RENDER_MODES:
            fail(f"invalid_source_or_intent: {slide_path}.director_visual_intent.render_mode is unsupported")
        relationship_kind, relationship_direction, roles = validate_relationship(
            director["primary_relationship"],
            f"{slide_path}.director_visual_intent.primary_relationship",
            content_ids=content_ids,
        )
        _validate_source_bound_metric_relationship(
            slide,
            director["primary_relationship"],
            f"{slide_path}.director_visual_intent.primary_relationship",
        )
        _validate_source_bound_chronology_relationship(
            slide,
            director["primary_relationship"],
            operation,
            f"{slide_path}.director_visual_intent.primary_relationship",
        )
        _validate_source_bound_formal_relationship(
            slide,
            director["primary_relationship"],
            operation,
            f"{slide_path}.director_visual_intent.primary_relationship",
        )
        for field in ("primary_focus", "information_priority", "presentation_order"):
            ordered_ids = require_unique_strings(
                director[field], f"{slide_path}.director_visual_intent.{field}", nonempty=True
            )
            if not set(ordered_ids) <= content_ids:
                fail(f"invalid_source_or_intent: {slide_path}.director_visual_intent.{field} references an unknown content object")
        require_unique_strings(
            director["simplicity_rules"],
            f"{slide_path}.director_visual_intent.simplicity_rules",
            nonempty=True,
        )
        require_string(
            director["final_frame_requirement"],
            f"{slide_path}.director_visual_intent.final_frame_requirement",
        )
        director_source_bindings = require_unique_strings(
            director["source_bindings"],
            f"{slide_path}.director_visual_intent.source_bindings",
            nonempty=True,
        )
        if not set(director_source_bindings) <= source_binding_ids:
            fail(f"invalid_source_or_intent: {slide_path}.director_visual_intent.source_bindings references an unknown source binding")
        validate_target_intervals(
            director["visual_system_targets"],
            f"{slide_path}.director_visual_intent.visual_system_targets",
            required_metrics=required_metrics,
        )
        requested_grammar_id = require_string(slide["grammar_id"], f"{slide_path}.grammar_id")
        matches = []
        for grammar in grammars.get("items", []):
            for signature in grammar.get("semantic_signatures", []):
                if (
                    operation == grammar.get("communication_operation_enum")
                    and relationship_kind == signature.get("relationship_kind")
                    and relationship_direction == signature.get("relationship_direction")
                    and roles == signature.get("relationship_roles")
                    and visual_encoding == signature.get("visual_encoding_enum")
                ):
                    matches.append((grammar, signature))
        if len(matches) != 1:
            fail(
                f"coverage_gap_no_grammar: {slide_path} must match exactly one grammar by "
                "operation, relationship kind, direction, roles, and encoding"
            )
        if matches[0][0].get("id") != requested_grammar_id:
            fail(
                f"coverage_gap_no_grammar: {slide_path}.grammar_id does not equal the unique "
                "semantic match"
            )
        secondary = director["secondary_relationships"]
        if not isinstance(secondary, list):
            fail(f"{slide_path}.director_visual_intent.secondary_relationships must be an array")
        for secondary_index, raw_relationship in enumerate(secondary):
            secondary_path = f"{slide_path}.director_visual_intent.secondary_relationships[{secondary_index}]"
            kind, direction, secondary_roles = validate_relationship(
                raw_relationship,
                secondary_path,
                content_ids=content_ids,
                optional_control_fields=True,
            )
            _validate_source_bound_metric_relationship(
                slide, raw_relationship, secondary_path
            )
            secondary_operation = raw_relationship.get("communication_operation_enum", operation)
            _validate_source_bound_chronology_relationship(
                slide, raw_relationship, secondary_operation, secondary_path
            )
            _validate_source_bound_formal_relationship(
                slide, raw_relationship, secondary_operation, secondary_path
            )
            secondary_encoding = raw_relationship.get("visual_encoding_enum", visual_encoding)
            secondary_mode = raw_relationship.get("render_mode", director_render_mode)
            secondary_matches = [
                (grammar, signature)
                for grammar in grammars.get("items", [])
                for signature in grammar.get("semantic_signatures", [])
                if secondary_operation == grammar.get("communication_operation_enum")
                and kind == signature.get("relationship_kind")
                and direction == signature.get("relationship_direction")
                and secondary_roles == signature.get("relationship_roles")
                and secondary_encoding == signature.get("visual_encoding_enum")
            ]
            if len(secondary_matches) != 1:
                fail(f"coverage_gap_no_grammar: {secondary_path} must match exactly one approved signature")
        canonical_json_bytes(slide["source_data"])

    capabilities = set(require_unique_strings(
        selection["local_runtime_capabilities"],
        f"{path}.local_runtime_capabilities",
        nonempty=True,
    ))
    if not REQUIRED_SELECTOR_RUNTIME_CAPABILITIES <= capabilities:
        fail(f"unsupported_render_runtime: {path}.local_runtime_capabilities are incomplete")
    compatibility = selection["compatibility_results"]
    if not isinstance(compatibility, list) or not compatibility or any(
        item != "compatible" for item in compatibility
    ):
        fail(f"coverage_gap_no_prototype: {path}.compatibility_results must all be compatible")
    risks = selection["risk_results"]
    if not isinstance(risks, list) or any(item == "hard_boundary_conflict" for item in risks):
        fail(f"coverage_gap_no_prototype: {path}.risk_results contain a hard boundary conflict")
    for index, risk in enumerate(risks):
        require_string(risk, f"{path}.risk_results[{index}]")

    expected_intent = derive_visual_system_intent(
        brief, slides, required_metrics=required_metrics
    )
    if isinstance(brief["visual_tone"], dict) and "description" in brief["visual_tone"]:
        source_brief = deepcopy(brief)
        source_brief["visual_tone"] = brief["visual_tone"]["description"]
        source_slides = [semantic_slide_payload(slide) for slide in slides]
        semantic_profile = _semantic_design_profile(source_brief, source_slides)
        _, candidate_scores = _select_prototype_from_profile(semantic_profile, prototypes, path)
        expected_intent["selector_version"] = "2.0.0"
        expected_intent["semantic_design_profile"] = semantic_profile
        expected_intent["candidate_scores"] = candidate_scores
    if selection["visual_system_intent"] != expected_intent:
        fail(f"blocked_prototype_selection_mismatch: {path}.visual_system_intent is not derived from the complete Brief and Slide set")
    expected_prototype_id = select_prototype(expected_intent, prototypes, path)
    if (
        selection["prototype_id"] != expected_prototype_id
        or selection["decision"] != "unique_match"
    ):
        fail(f"blocked_prototype_selection_mismatch: {path} does not equal the system-derived unique selection")
    return selection


def validate_selection_provenance(
    value: Any,
    path: str,
    *,
    selection: dict[str, Any],
    selection_sha256: str,
    strategy: dict[str, Any],
) -> dict[str, Any]:
    required_fields = {
        "schema_id", "selection_sha256", "grammar_asset_sha256",
        "prototype_asset_sha256", "synthesis_asset_sha256", "brief_sha256", "semantic_slide_set_sha256",
        "visual_system_intent_sha256", "selector", "grammar_selections",
        "prototype", "design_strategy",
    }
    allowed_fields = required_fields
    if (
        not isinstance(value, dict)
        or not required_fields <= set(value)
        or not set(value) <= allowed_fields
    ):
        fail(f"selection_provenance_integrity_failed: {path} contract is invalid")
    provenance = strict_object(
        value,
        path,
        required_fields,
    )
    if provenance["schema_id"] != "smart-video.selection-provenance.v1":
        fail(f"selection_provenance_integrity_failed: {path}.schema_id is invalid")
    if provenance["selection_sha256"] != selection_sha256:
        fail(f"selection_provenance_integrity_failed: {path}.selection_sha256 does not match selection")
    knowledge = selection["visual_knowledge"]
    if (
        provenance["grammar_asset_sha256"] != knowledge["grammar_asset_sha256"]
        or provenance["prototype_asset_sha256"] != knowledge["prototype_asset_sha256"]
        or provenance["synthesis_asset_sha256"] != knowledge["synthesis_asset_sha256"]
    ):
        fail(f"selection_provenance_integrity_failed: {path} asset hashes do not match selection")
    if provenance["brief_sha256"] != sha256_bytes(canonical_json_bytes(selection["brief"])):
        fail(f"selection_provenance_integrity_failed: {path}.brief_sha256 does not match selection")
    semantic_slides = [semantic_slide_payload(slide) for slide in selection["slides"]]
    if provenance["semantic_slide_set_sha256"] != sha256_bytes(canonical_json_bytes(semantic_slides)):
        fail(f"selection_provenance_integrity_failed: {path}.semantic_slide_set_sha256 does not match selection")
    if provenance["visual_system_intent_sha256"] != sha256_bytes(canonical_json_bytes(selection["visual_system_intent"])):
        fail(f"selection_provenance_integrity_failed: {path}.visual_system_intent_sha256 does not match selection")
    if provenance["selector"] != {"id": "qualitative-semantic-prototype-selector", "version": "2.0.0"}:
        fail(f"selection_provenance_integrity_failed: {path}.selector is not authoritative")
    grammars = load_json(EXPRESSION_GRAMMARS_PATH, "expression grammar asset")
    expected_grammars = [
        select_grammar_for_slide(slide, grammars, f"selection.slides[{index}]")
        for index, slide in enumerate(selection["slides"])
    ]
    if provenance["grammar_selections"] != expected_grammars:
        fail(f"selection_provenance_integrity_failed: {path}.grammar_selections do not match selection")
    if provenance["prototype"] != {
        "id": selection["prototype_id"], "result": "selected", "source": "system_selector"
    }:
        fail(f"selection_provenance_integrity_failed: {path}.prototype does not match selection")
    if provenance["design_strategy"] != strategy:
        fail(f"selection_provenance_integrity_failed: {path}.design_strategy does not match request")
    return provenance


def _compile_visual_system_from_decision(
    *,
    compile_request_id: str,
    prototype_selection: Any,
    prototype_selection_sha256: str,
    selection_provenance: Any,
    selection_provenance_sha256: str,
    design_strategy: Any,
) -> dict[str, Any]:
    """Compile tokens from a system-generated, immutable selection decision."""
    require_string(compile_request_id, "compile_request_id")
    strategy = validate_strategy(
        design_strategy, "design_strategy", {"design_strategy": design_strategy}
    )
    selection = validate_prototype_selection(prototype_selection, "prototype_selection")
    supplied_selection_hash = require_sha256(
        prototype_selection_sha256,
        "prototype_selection_sha256",
    )
    if supplied_selection_hash != sha256_bytes(canonical_json_bytes(selection)):
        fail("blocked_stale_visual_selection: prototype_selection_sha256 does not match selection")
    supplied_provenance_hash = require_sha256(
        selection_provenance_sha256,
        "selection_provenance_sha256",
    )
    if supplied_provenance_hash != sha256_bytes(
        jcs_safe_bytes(selection_provenance, "selection_provenance")
    ):
        fail("selection_provenance_integrity_failed: selection_provenance_sha256 does not match provenance")
    provenance = validate_selection_provenance(
        selection_provenance,
        "selection_provenance",
        selection=selection,
        selection_sha256=supplied_selection_hash,
        strategy=strategy,
    )

    prototypes = load_json(VISUAL_PROTOTYPES_PATH, "visual prototype asset")
    synthesis = load_synthesis_knowledge()
    synthesis_sha256 = sha256_bytes(SYNTHESIS_TRAITS_PATH.read_bytes())
    prototype = next(
        item for item in prototypes["items"]
        if item["id"] == selection["prototype_id"]
    )
    traits = {trait["metric"]: trait for trait in prototype["traits"]}

    def preferred(metric: str) -> float:
        return traits[metric]["measured_interval"]["preferred"]

    def measured_value(metric: str, factor: float, *, reverse: bool = False) -> float:
        interval = traits[metric]["measured_interval"]
        position = 1.0 - factor if reverse else factor
        return interval["lower"] + (interval["upper"] - interval["lower"]) * position

    def count_interval(metric: str) -> list[int]:
        interval = traits[metric]["measured_interval"]
        group = "geometry" if metric in {"svg_geometry_count", "connector_count"} else "material"
        synthesis_lower, synthesis_upper = synthesis_metric_envelope(synthesis, group, metric)
        lower = max(float(interval["lower"]), synthesis_lower)
        upper = min(float(interval["upper"]), synthesis_upper)
        if lower > upper:
            fail(f"coverage_gap_no_prototype: no synthesis evidence overlap for {metric}")
        return [int(math.ceil(lower)), int(math.floor(upper))]

    intent_priors = prototype["intent_intervals"]

    def intent_preferred(metric: str) -> float:
        return intent_priors[metric]["preferred"]

    def intent_count_interval(metric: str) -> list[int]:
        interval = intent_priors[metric]
        synthesis_lower, synthesis_upper = synthesis_metric_envelope(synthesis, "material", metric)
        lower = max(float(interval["lower"]), synthesis_lower)
        upper = min(float(interval["upper"]), synthesis_upper)
        if lower > upper:
            fail(f"coverage_gap_no_prototype: no synthesis evidence overlap for {metric}")
        return [int(math.ceil(lower)), int(math.floor(upper))]

    def bounded_intent_interval(group: str, metric: str) -> tuple[float, float]:
        interval = intent_priors[metric]
        synthesis_lower, synthesis_upper = synthesis_metric_envelope(synthesis, group, metric)
        lower = max(float(interval["lower"]), synthesis_lower)
        upper = min(float(interval["upper"]), synthesis_upper)
        if lower > upper:
            fail(f"coverage_gap_no_prototype: no synthesis evidence overlap for {metric}")
        return lower, upper

    brief = selection["brief"]
    semantic_slides = [semantic_slide_payload(slide) for slide in selection["slides"]]
    input_hashes = {
        "brief": sha256_bytes(canonical_json_bytes(brief)),
        "semantic_slide_set": sha256_bytes(canonical_json_bytes(semantic_slides)),
        "visual_system_intent": sha256_bytes(canonical_json_bytes(selection["visual_system_intent"])),
        "prototype_selection": supplied_selection_hash,
        "selection_provenance": supplied_provenance_hash,
        "synthesis_knowledge": synthesis_sha256,
    }
    compiler_inputs = {
        "compile_request_id": compile_request_id,
        "design_strategy": strategy,
        "input_hashes": input_hashes,
    }
    input_hashes["compiler_inputs"] = sha256_bytes(canonical_json_bytes(compiler_inputs))

    semantic_profile = {
        "slide_count": len(selection["slides"]),
        "content_object_count": sum(
            len(slide["content_objects"]) for slide in selection["slides"]
        ),
        "relationship_count": sum(
            1 + len(slide["director_visual_intent"]["secondary_relationships"])
            for slide in selection["slides"]
        ),
        "information_priority_count": sum(
            len(slide["director_visual_intent"]["information_priority"])
            for slide in selection["slides"]
        ),
        "presentation_order_count": sum(
            len(slide["director_visual_intent"]["presentation_order"])
            for slide in selection["slides"]
        ),
    }
    structural_load = sum(
        semantic_profile[field] for field in (
            "content_object_count", "relationship_count",
            "information_priority_count", "presentation_order_count",
        )
    )
    bound_text_length = sum(
        len(slide["narration"])
        + len(slide["source_excerpt"])
        + len(slide["primary_claim"]["text"])
        + sum(len(item["text"]) for item in slide["content_objects"])
        for slide in selection["slides"]
    )
    semantic_profile["semantic_load"] = structural_load + max(1, math.ceil(bound_text_length / 80))
    minimum_declared_load = 4 * semantic_profile["slide_count"]
    continuous_semantic_load = structural_load + (bound_text_length / 80.0)
    semantic_factor = continuous_semantic_load / (
        continuous_semantic_load + minimum_declared_load
    )
    style_synthesis = select_style_traits(
        brief,
        selection["visual_system_intent"]["semantic_design_profile"],
        synthesis,
        selection["slides"],
        selection["qualitative_family_intent"],
    )
    style_values = {
        group: set(values)
        for group, values in style_synthesis["selected_qualitative_values"].items()
    }

    synthesis_seed = sha256_bytes(canonical_json_bytes({
        "brief": brief,
        "semantic_slides": semantic_slides,
        "design_strategy": strategy,
        "synthesis_asset_sha256": synthesis_sha256,
    }))
    seed_words = [int(synthesis_seed[index:index + 8], 16) for index in range(0, 40, 8)]
    design_factors = [word / 0xFFFFFFFF for word in seed_words]

    def bounded(metric_value: float, group: str, metric: str) -> float:
        lower, upper = synthesis_metric_envelope(synthesis, group, metric)
        return min(upper, max(lower, metric_value))

    def hsl_hex(hue: float, saturation: float, lightness: float) -> str:
        red, green, blue = colorsys.hls_to_rgb(hue % 1.0, lightness, saturation)
        return "#{:02X}{:02X}{:02X}".format(
            round(red * 255), round(green * 255), round(blue * 255)
        )

    role_count = int(round(bounded(
        preferred("dom_quantized_palette_count"), "palette", "dom_quantized_palette_count"
    )))
    palette_traits = style_values["palette"]
    dark_field = bool({
        "dark_field", "dark_opaque_field", "full_bleed_warm_cool_field",
        "dark_abyss_field", "dark_black_field", "dark_ink_field", "dark_navy_field",
    } & palette_traits)
    warm_field = bool({
        "light_warm_field", "light_warm_neutral_field", "muted_earth_accents",
        "light_warm_canvas", "light_linen_field",
    } & palette_traits)
    rose_field = "light_rose_field" in palette_traits
    base_hue = (
        0.94 + 0.05 * design_factors[0] if rose_field
        else 0.72 + 0.08 * design_factors[0] if "dark_abyss_field" in palette_traits
        else 0.23 + 0.08 * design_factors[0] if "dark_black_field" in palette_traits
        else 0.10 + 0.08 * design_factors[0] if "light_warm_canvas" in palette_traits
        else 0.06 + 0.07 * design_factors[0] if "light_linen_field" in palette_traits
        else 0.035 + 0.09 * design_factors[0] if warm_field
        else design_factors[0]
    )
    if "multiple_high_chroma_accents" in palette_traits:
        accent_saturation = 0.78 + 0.12 * design_factors[1]
    elif "low_chroma_metallic_accent" in palette_traits:
        accent_saturation = 0.24 + 0.10 * design_factors[1]
    elif "muted_earth_accents" in palette_traits:
        accent_saturation = 0.42 + 0.12 * design_factors[1]
    elif "soft_cool_warm_accents" in palette_traits:
        accent_saturation = 0.30 + 0.12 * design_factors[1]
    elif "bright_teaching_accents" in palette_traits:
        accent_saturation = 0.68 + 0.12 * design_factors[1]
    elif "full_bleed_warm_cool_field" in palette_traits:
        accent_saturation = 0.74 + 0.12 * design_factors[1]
    elif {
        "electric_violet_magenta_accents", "acid_lime_accent", "electric_cyan_accent",
        "multi_hue_geometric_accents",
    } & palette_traits:
        accent_saturation = 0.76 + 0.12 * design_factors[1]
    elif "muted_peach_sage_accents" in palette_traits:
        accent_saturation = 0.32 + 0.10 * design_factors[1]
    else:
        accent_saturation = 0.58 + 0.12 * design_factors[1]
    accent_lightness = 0.58 + 0.08 * design_factors[2] if dark_field else 0.34 + 0.10 * design_factors[2]
    series_offsets = (
        (0.0, 0.5, 0.04, 0.54)
        if "cool_warm_duotone" in palette_traits else
        (0.0, 0.19, 0.43, 0.67)
    )
    chart_series = [
        hsl_hex(
            base_hue + offset,
            min(0.9, accent_saturation + 0.04 * design_factors[3]),
            (0.60 if dark_field else 0.38) + 0.08 * design_factors[4],
        )
        for offset in series_offsets
    ]
    palette = {
        "background": hsl_hex(
            base_hue,
            0.16 + 0.08 * design_factors[2] if dark_field else 0.08 + 0.06 * design_factors[2],
            0.075 if dark_field else (0.94 if "light_paper_field" in palette_traits else 0.92),
        ),
        "surface": hsl_hex(base_hue, 0.10 if dark_field else 0.04, 0.13 if dark_field else 0.975),
        "primary_text": hsl_hex(base_hue + 0.5, 0.06 if dark_field else 0.12, 0.96 if dark_field else 0.09),
        "secondary_text": hsl_hex(base_hue + 0.5, 0.08, 0.78 if dark_field else 0.28),
        "accent": hsl_hex(base_hue, accent_saturation, accent_lightness),
        "positive": hsl_hex(0.34 + 0.03 * design_factors[1], 0.58, 0.31),
        "warning": hsl_hex(0.09 + 0.03 * design_factors[2], 0.70, 0.34),
        "negative": hsl_hex(0.98 + 0.03 * design_factors[3], 0.66, 0.38),
        "chart_series": chart_series,
    }
    palette.update({
        "visible_role_count_target": role_count,
        "dominant_color_area_ratio_target": round(bounded(
            preferred("dom_dominant_color_role_ratio"),
            "palette", "dom_dominant_color_role_ratio",
        ), 6),
    })
    dense = semantic_factor >= 0.75
    body_size = round(bounded(
        preferred("body_font_size_px"),
        "typography", "body_font_size_px",
    ), 2)
    display_ratio = bounded(
        preferred("display_to_body_size_ratio"),
        "typography", "display_to_body_size_ratio",
    )
    display_size = round(body_size * display_ratio, 2)
    title_size = round(body_size + (display_size - body_size) * 0.5, 2)
    caption_size = round(max(12.0, body_size - 4.0), 2)
    weight_interval = traits["font_weight_span"]["measured_interval"]
    weight_span = int(round(preferred("font_weight_span") / 100.0) * 100)
    weight_span = max(0, min(500, weight_span))
    if not weight_interval["lower"] <= weight_span <= weight_interval["upper"]:
        weight_span = int(math.ceil(weight_interval["lower"] / 100.0) * 100)
    low_weight = 400
    high_weight = low_weight + weight_span
    spacing_tokens = _spacing_tokens_for_semantic_load(
        semantic_profile["semantic_load"]
    )
    typography_traits = style_values["typography"]
    english = brief["language"].lower().startswith("en")
    sans_stack = ["Arial", "Helvetica", "sans-serif"] if english else ["PingFang SC", "Helvetica", "Arial", "sans-serif"]
    condensed_stack = ["Arial Narrow", "Arial", "sans-serif"] if english else ["Heiti SC", "PingFang SC", "sans-serif"]
    typewriter_stack = ["Courier New", "Courier", "monospace"] if english else ["STFangsong", "FangSong", "serif"]
    serif_stack = ["Georgia", "Times New Roman", "serif"] if english else ["Songti SC", "STSong", "serif"]
    handwritten_stack = ["Comic Sans MS", "cursive"] if english else ["Kaiti SC", "STKaiti", "serif"]
    display_stack = (
        typewriter_stack if "typewriter_display" in typography_traits
        else handwritten_stack if {"handwritten_display", "handwritten_heading"} & typography_traits
        else serif_stack if {
            "serif_display", "light_editorial_serif", "bold_italic_serif_display",
            "editorial_serif_display", "refined_serif_display",
        } & typography_traits
        else condensed_stack if {
            "oversized_condensed_display", "condensed_display", "condensed_hero_display",
            "ultra_bold_condensed_display", "monumental_condensed_display",
        } & typography_traits
        else sans_stack
    )
    body_stack = (
        typewriter_stack if {"typewriter_body", "monospace_system_labels"} & typography_traits
        else handwritten_stack if "handwritten_accent" in typography_traits
        else sans_stack
    )
    accent_stack = serif_stack if {
        "serif_italic_accent", "italic_accent", "editorial_serif_accent",
    } & typography_traits else (
        handwritten_stack if "handwritten_accent" in typography_traits else display_stack
    )
    evidence_ids = [
        evidence_id for trait in prototype["traits"] for evidence_id in trait["evidence_ids"]
    ]
    evidence_ids = sorted(set(evidence_ids) | set(prototype.get("selection_evidence_ids", [])))
    intent_token_bindings = {
        "dom_quantized_palette_count": ["palette.visible_role_count_target"],
        "dom_dominant_color_role_ratio": ["palette.dominant_color_area_ratio_target"],
        "median_effective_text_contrast_ratio": ["contrast.median_effective_text_contrast_ratio_target"],
        "display_to_body_size_ratio": ["typography.display.size_px", "typography.body.size_px"],
        "occupancy_ratio": ["composition.occupancy_ratio_target"],
        "text_area_ratio": ["composition.text_area_ratio_target"],
        "largest_non_background_area_ratio": ["composition.largest_object_area_ratio_target"],
        "left_alignment_reuse_ratio": ["composition.left_edge_reuse_ratio_target"],
        "top_alignment_reuse_ratio": ["composition.top_edge_reuse_ratio_target"],
        "shadow_layer_count": ["material.count_priors.shadow_layers"],
        "gradient_layer_count": ["material.count_priors.gradient_layers"],
        "filtered_layer_count": ["material.count_priors.filtered_layers"],
        "bounded_panel_count": ["material.count_priors.bounded_panels"],
        "bordered_element_count": ["material.count_priors.bordered_elements"],
        "svg_geometry_count": ["material.count_priors.svg_geometry"],
        "connector_count": ["material.count_priors.connectors"],
        "maximum_animation_duration_seconds": ["motion.transition_duration_seconds"],
        "maximum_animation_end_seconds": ["motion.sequence_end_seconds"],
        "final_to_hold_normalized_mean_absolute_difference": ["motion.final_to_hold_normalized_mean_absolute_difference_target"],
    }
    token_decisions = [
        {"token_group": "palette", "rule_id": "semantic-seeded-evidence-bounded-palette-v2", "input_paths": ["brief", "slides[]", "design_strategy", "prototype.traits.color_roles", "synthesis_knowledge.trait_groups.palette"]},
        {"token_group": "contrast", "rule_id": "measured-contrast-prior-v1", "input_paths": ["prototype.traits.contrast"]},
        {"token_group": "typography", "rule_id": "bounded-complete-semantic-load-type-scale-v2", "input_paths": ["brief.language", "slides[].narration", "slides[].content_objects", "slides[].director_visual_intent", "prototype.traits.typography_hierarchy", "synthesis_knowledge.trait_groups.typography"]},
        {"token_group": "spacing", "rule_id": "monotonic-clamped-semantic-load-density-v2", "input_paths": ["decision_trace.semantic_profile.semantic_load"]},
        {"token_group": "composition", "rule_id": "bounded-complete-semantic-load-composition-v2", "input_paths": ["slides[].content_objects", "slides[].director_visual_intent", "prototype.traits.spacing_density", "prototype.traits.alignment", "synthesis_knowledge.trait_groups.geometry"]},
        {"token_group": "material", "rule_id": "evidence-bounded-material-geometry-priors-v2", "input_paths": ["prototype.traits.material_depth", "prototype.traits.shape", "prototype.traits.connectors", "synthesis_knowledge.trait_groups.material", "synthesis_knowledge.trait_groups.geometry"]},
        {"token_group": "echarts", "rule_id": "palette-and-typography-adapter-v1", "input_paths": ["palette", "typography", "design_strategy"]},
        {"token_group": "motion", "rule_id": "evidence-bounded-motion-and-normative-hold-v2", "input_paths": ["prototype.traits.motion", "synthesis_knowledge.trait_groups.motion", "normative.final_hold_stability", "normative.maximum_slide_duration"]},
    ]
    slide_request_bindings = [
        {
            "slide_id": slide["slide_id"],
            "shot_type": slide["shot_type"],
            "render_mode": slide["director_visual_intent"]["render_mode"],
            "duration_seconds": slide["duration_seconds"],
            "source_content_sha256": sha256_bytes(canonical_json_bytes(
                source_content_for_slide(slide)
            )),
            "source_data_sha256": sha256_bytes(canonical_json_bytes(slide["source_data"])),
        }
        for slide in selection["slides"]
    ]
    system = {
        "schema_id": "smart-video.visual-system.v1",
        "id": f"visual-system-{input_hashes['compiler_inputs'][:16]}",
        "version": "1.0.0",
        "locked": True,
        "aspect_ratio": selection["aspect_ratio"],
        "design_strategy": strategy,
        "prototype_id": prototype["id"],
        "prototype_selection": {
            "id": prototype["id"],
            "immutable": True,
            "selection_sha256": supplied_selection_hash,
        },
        "selection_provenance": provenance,
        "selection_provenance_sha256": supplied_provenance_hash,
        "compilation": {
            "compiler_id": "smart-video.compile-visual-system",
            "compiler_version": "5.0.0",
            "compile_request_id": compile_request_id,
            "compiler_inputs_sha256": input_hashes["compiler_inputs"],
        },
        "decision_trace": {
            "brief_visual_tone_basis_refs": brief["visual_tone"]["basis_refs"],
            "complete_slide_ids": [slide["slide_id"] for slide in selection["slides"]],
            "slide_request_bindings": slide_request_bindings,
            "measured_prior_evidence_ids": evidence_ids,
            "local_runtime_capabilities": selection["local_runtime_capabilities"],
            "hard_quality_gate_ids": [
                "accessibility", "local_only_execution", "final_hold_stability",
                "source_fidelity", "non_overlap",
            ],
            "design_prior_departures": [],
            "generated_decisions_recorded": True,
            "source_token_copy": False,
            "semantic_profile": semantic_profile,
            "style_synthesis": style_synthesis,
            "synthesis_knowledge": {
                "asset_sha256": synthesis_sha256,
                "version": synthesis["version"],
                "role": synthesis["role"],
                "prototype_role": synthesis["prototype_role"],
                "trait_groups": sorted(synthesis["trait_groups"]),
                "source_coverage": {
                    "visual_system_catalog": {
                        key: synthesis["source_coverage"]["visual_system_catalog"][key]
                        for key in ("reviewed_count", "direct_trait_count", "coverage_gap_count")
                    },
                    "reference_layouts": {
                        "measured_count": synthesis["source_coverage"]["reference_layouts"]["measured_count"]
                    },
                    "scene_candidates": {
                        "measured_count": synthesis["source_coverage"]["scene_candidates"]["measured_count"]
                    },
                },
            },
            "input_hashes": input_hashes,
            "token_decisions": token_decisions,
            "intent_token_bindings": intent_token_bindings,
        },
        "palette": palette,
        "contrast": {
            "normal_text_min_ratio": 4.5, "large_text_min_ratio": 3.0,
            "non_text_min_ratio": 3.0,
            "median_effective_text_contrast_ratio_target": round(
                intent_preferred("median_effective_text_contrast_ratio"), 6
            ),
            "dominant_frame_to_text_target_ratio": round(
                bounded(
                    preferred("dominant_frame_to_median_text_contrast_ratio"),
                    "palette", "dominant_frame_to_median_text_contrast_ratio",
                ), 6,
            ),
        },
        "typography": {
            "display": {"font_stack": display_stack, "size_px": display_size, "weight": high_weight, "line_height": 1.05},
            "title": {"font_stack": display_stack, "size_px": title_size, "weight": high_weight, "line_height": 1.12},
            "body": {"font_stack": body_stack, "size_px": body_size, "weight": low_weight, "line_height": 1.4},
            "label": {"font_stack": accent_stack, "size_px": body_size, "weight": high_weight, "line_height": 1.25},
            "caption": {"font_stack": body_stack, "size_px": caption_size, "weight": low_weight, "line_height": 1.35},
            "data": {"font_stack": display_stack, "size_px": title_size, "weight": high_weight, "line_height": 1.1},
        },
        "spacing": spacing_tokens,
        "composition": {
            "occupancy_ratio_target": round(measured_value("occupancy_ratio", semantic_factor), 6),
            "text_area_ratio_target": round(measured_value("text_area_ratio", semantic_factor), 6),
            "largest_object_area_ratio_target": round(measured_value("largest_non_background_area_ratio", semantic_factor, reverse=True), 6),
            "left_edge_reuse_ratio_target": round(bounded(
                measured_value("left_alignment_reuse_ratio", semantic_factor),
                "geometry", "left_alignment_reuse_ratio",
            ), 6),
            "top_edge_reuse_ratio_target": round(bounded(
                measured_value("top_alignment_reuse_ratio", semantic_factor),
                "geometry", "top_alignment_reuse_ratio",
            ), 6),
            "density": "dense" if dense else ("sparse" if preferred("occupancy_ratio") < 0.4 else "moderate"),
            "alignment": "grid_with_repeated_edges",
        },
        "material": {
            "surface_style": (
                "liquid_aura_field" if "liquid_aura" in style_values["material"]
                else "technical_grid" if "six_zone_grid" in style_values["material"]
                else "geometric_collage" if "collage_blocks" in style_values["material"]
                else "organic_wash" if "organic_wash" in style_values["material"]
                else "print_texture" if "print_texture" in style_values["material"]
                else "paper_archive" if "paper_field" in style_values["material"]
                else "flat_editorial" if "flat_editorial_field" in style_values["material"]
                else "paint_wash" if "paint_wash" in style_values["material"]
                else "thermal_gradient" if "thermal_gradient" in style_values["material"]
                else "notebook_paper" if "grid_paper" in style_values["material"]
                else "doodle_marks" if "doodle_stars" in style_values["material"]
                else "deco_frame" if "deco_frame" in style_values["material"]
                else "flat_poster"
            ),
            "depth_strategy": (
                "blurred_luminous_layers" if "liquid_aura" in style_values["material"]
                else "outlined_modular_panels" if "six_zone_grid" in style_values["material"]
                else "overlapping_geometric_planes" if "collage_blocks" in style_values["material"]
                else "soft_radial_wash_layers" if "organic_wash" in style_values["material"]
                else "outlined_graphic_emphasis" if "outlined_headline" in style_values["material"]
                else "archival_border_layers" if "archive_border" in style_values["material"]
                else "rule_and_bar_emphasis" if "rule_emphasis" in style_values["material"]
                else "wash_layering" if "paint_wash" in style_values["material"]
                else "full_bleed_atmospheric_field" if "thermal_gradient" in style_values["material"]
                else "paper_and_marker_layers" if "grid_paper" in style_values["material"]
                else "rough_graphic_marks" if "doodle_stars" in style_values["material"]
                else "framed_plaque_layers" if "deco_frame" in style_values["material"]
                else "graphic_mark_emphasis"
            ),
            "corner_radius_px": {"min": 0, "max": 12 if {
                "pill_badge", "rounded_tags", "sticky_note",
            } & style_values["geometry"] else 2},
            "edge_style": (
                "soft_liquid_boundaries" if "blurred_liquid_fields" in style_values["geometry"]
                else "outlined_grid_cells" if "outlined_grid_cells" in style_values["geometry"]
                else "overlapping_polygon_edges" if "overlapping_polygons" in style_values["geometry"]
                else "fine_organic_rules" if "soft_radial_fields" in style_values["geometry"]
                else "hard_print_blocks" if "hard_print_blocks" in style_values["geometry"]
                else "archive_rules" if "rectangular_archive_rules" in style_values["geometry"]
                else "editorial_rules" if "editorial_rules" in style_values["geometry"]
                else "fine_watercolor_rules" if "fine_vertical_rule" in style_values["geometry"]
                else "minimal_full_bleed_rules" if "minimal_rules" in style_values["geometry"]
                else "marker_and_paper_edges" if "marker_strokes" in style_values["geometry"]
                else "rough_hand_drawn_edges" if "rough_outlines" in style_values["geometry"]
                else "double_line_deco_frame" if "double_line_frame" in style_values["geometry"]
                else "calligraphic_curves"
            ),
            "connector_style": (
                "phase_rail" if "phase_rail" in style_values["geometry"]
                else "neon_rails" if "neon_rails" in style_values["geometry"]
                else "angled_connectors" if "angled_connectors" in style_values["geometry"]
                else "fine_organic_rules" if "fine_rules" in style_values["geometry"]
                else "chronology_rail" if "chronology_rail" in style_values["geometry"]
                else "thin_timeline_rail" if "thin_timeline_rail" in style_values["geometry"]
                else "thin_process_rails" if "thin_process_rails" in style_values["geometry"]
                else "fine_ring_and_rule" if "segmented_ring" in style_values["geometry"]
                else "minimal_annotation_rules" if "corner_annotations" in style_values["geometry"]
                else "dashed_process_line" if "dashed_process_line" in style_values["geometry"]
                else "hand_drawn_connectors" if "hand_drawn_connectors" in style_values["geometry"]
                else "diamond_timeline" if "diamond_nodes" in style_values["geometry"]
                else "horizontal_rules"
            ),
            "geometry_language": sorted(style_values["geometry"]),
            "restraint_rule": "one_information_role_per_element",
            "count_priors": {
                "shadow_layers": count_interval("shadow_layer_count"),
                "gradient_layers": count_interval("gradient_layer_count"),
                "filtered_layers": intent_count_interval("filtered_layer_count"),
                "bordered_elements": count_interval("bordered_element_count"),
                "bounded_panels": count_interval("bounded_panel_count"),
                "svg_geometry": count_interval("svg_geometry_count"),
                "connectors": count_interval("connector_count"),
            },
        },
        "echarts": {
            "renderer": "canvas", "series_palette": palette["chart_series"],
            "text": {"font_family": body_stack[0], "color": palette["primary_text"], "font_size_px": body_size},
            "axes": {"line_color": "#6B7280", "label_color": "#374151", "split_line_color": "#D1D5DB"},
            "grid": {"left_px": 56, "right_px": 40, "top_px": 40, "bottom_px": 48, "contain_label": True},
            "marks": {"color": palette["negative"], "label_color": palette["primary_text"]},
            "labels": {"show": True, "position": "auto", "avoid_overlap": True},
        },
        "motion": {
            "easing": (
                "cubic-bezier(0.25, 0.8, 0.25, 1)" if "liquid_drift" in style_values["motion"]
                else "cubic-bezier(0.2, 0.9, 0.2, 1)" if "grid_snap" in style_values["motion"]
                else "cubic-bezier(0.34, 1.56, 0.64, 1)" if "shape_rotation" in style_values["motion"]
                else "cubic-bezier(0.22, 1, 0.36, 1)" if "soft_bloom" in style_values["motion"]
                else "cubic-bezier(0.34, 1.56, 0.64, 1)" if "spring_accent" in style_values["motion"]
                else "cubic-bezier(0.34, 1.56, 0.64, 1)" if "elastic_pop" in style_values["motion"]
                else "steps(4, end)" if "typewriter_reveal" in style_values["motion"]
                else "cubic-bezier(0.65, 0, 0.35, 1)" if "mechanical_print_assembly" in style_values["motion"]
                else "cubic-bezier(0.22, 1, 0.36, 1)" if "wash_dissolve" in style_values["motion"]
                else "cubic-bezier(0.16, 1, 0.3, 1)" if "grain_emergence" in style_values["motion"]
                else "cubic-bezier(0.2, 0.8, 0.2, 1)"
            ),
            "character": sorted(style_values["motion"]),
            "transition_duration_seconds": (
                {
                    "min": bounded_intent_interval(
                        "motion", "maximum_animation_duration_seconds"
                    )[0],
                    "preferred": min(
                        bounded_intent_interval("motion", "maximum_animation_duration_seconds")[1],
                        max(
                            bounded_intent_interval("motion", "maximum_animation_duration_seconds")[0],
                            intent_preferred("maximum_animation_duration_seconds"),
                        ),
                    ),
                    "max": bounded_intent_interval(
                        "motion", "maximum_animation_duration_seconds"
                    )[1],
                }
            ),
            "sequence_end_seconds": {
                "preferred": min(
                    bounded_intent_interval("motion", "maximum_animation_end_seconds")[1],
                    max(
                        bounded_intent_interval("motion", "maximum_animation_end_seconds")[0],
                        intent_preferred("maximum_animation_end_seconds"),
                    ),
                ),
                "max": bounded_intent_interval(
                    "motion", "maximum_animation_end_seconds"
                )[1],
            },
            "final_hold_policy": "positive_stable_hold_required",
            "final_to_hold_changed_pixel_ratio_target": (
                preferred("final_to_hold_changed_pixel_ratio")
                if "final_to_hold_changed_pixel_ratio" in traits else None
            ),
            "final_to_hold_normalized_mean_absolute_difference_target": round(
                intent_preferred("final_to_hold_normalized_mean_absolute_difference"), 9
            ),
            "maximum_total_duration_seconds": MAX_SLIDE_DURATION_SECONDS,
            "reduced_motion_strategy": "replace_transforms_with_opacity_and_preserve_final_hold",
        },
        "hard_quality_gates": {
            "accessibility": "required", "local_only_execution": "required",
            "final_hold_stability": "required", "source_fidelity": "required",
            "non_overlap": "required",
        },
    }
    return system


def _make_system_selection_provenance(
    selection: dict[str, Any], strategy: dict[str, Any]
) -> dict[str, Any]:
    grammars = load_json(EXPRESSION_GRAMMARS_PATH, "expression grammar asset")
    selection_sha256 = sha256_bytes(canonical_json_bytes(selection))
    provenance = {
        "schema_id": "smart-video.selection-provenance.v1",
        "selection_sha256": selection_sha256,
        "grammar_asset_sha256": selection["visual_knowledge"]["grammar_asset_sha256"],
        "prototype_asset_sha256": selection["visual_knowledge"]["prototype_asset_sha256"],
        "synthesis_asset_sha256": selection["visual_knowledge"]["synthesis_asset_sha256"],
        "brief_sha256": sha256_bytes(canonical_json_bytes(selection["brief"])),
        "semantic_slide_set_sha256": sha256_bytes(canonical_json_bytes([
            semantic_slide_payload(slide) for slide in selection["slides"]
        ])),
        "visual_system_intent_sha256": sha256_bytes(canonical_json_bytes(
            selection["visual_system_intent"]
        )),
        "selector": {
            "id": "qualitative-semantic-prototype-selector",
            "version": "2.0.0",
        },
        "grammar_selections": [
            select_grammar_for_slide(slide, grammars, f"selection.slides[{index}]")
            for index, slide in enumerate(selection["slides"])
        ],
        "prototype": {
            "id": selection["prototype_id"],
            "result": "selected",
            "source": "system_selector",
        },
        "design_strategy": deepcopy(strategy),
    }
    return provenance


def compile_visual_system(
    *,
    compile_request_id: str,
    visual_system_input: Any,
    visual_system_input_sha256: str,
    design_strategy: Any,
) -> dict[str, Any]:
    """Compile a locked Visual System from qualitative, source-bound production input."""
    if isinstance(visual_system_input, dict) and (
        "prototype_id" in visual_system_input
        or "visual_system_intent" in visual_system_input
    ):
        fail("visual_system_input contains unsupported caller-authored fields")
    strategy = validate_strategy(
        design_strategy, "design_strategy", {"design_strategy": design_strategy}
    )
    derived = validate_visual_system_input(visual_system_input, "visual_system_input")
    visual_input_hash = require_sha256(
        visual_system_input_sha256, "visual_system_input_sha256"
    )
    if visual_input_hash != sha256_bytes(canonical_json_bytes(derived["input"])):
        fail("blocked_stale_visual_selection: visual_system_input_sha256 does not match input")
    selection = derived["selection"]
    selection_sha256 = sha256_bytes(canonical_json_bytes(selection))
    provenance = _make_system_selection_provenance(selection, strategy)
    provenance_sha256 = sha256_bytes(jcs_safe_bytes(provenance, "selection_provenance"))
    system = _compile_visual_system_from_decision(
        compile_request_id=compile_request_id,
        prototype_selection=selection,
        prototype_selection_sha256=selection_sha256,
        selection_provenance=provenance,
        selection_provenance_sha256=provenance_sha256,
        design_strategy=strategy,
    )
    input_hashes = system["decision_trace"]["input_hashes"]
    input_hashes["visual_system_input"] = visual_input_hash
    compiler_inputs = {
        "compile_request_id": compile_request_id,
        "design_strategy": strategy,
        "input_hashes": {
            key: value for key, value in input_hashes.items()
            if key != "compiler_inputs"
        },
    }
    compiler_hash = sha256_bytes(canonical_json_bytes(compiler_inputs))
    input_hashes["compiler_inputs"] = compiler_hash
    system["id"] = f"visual-system-{compiler_hash[:16]}"
    system["compilation"]["compiler_inputs_sha256"] = compiler_hash
    intent = selection["visual_system_intent"]
    background_modes = intent["background_modes"]
    adaptation = background_modes[0] if len(background_modes) == 1 else "mixed_slide_backgrounds"
    system["composition"]["background_adaptation"] = adaptation
    system["decision_trace"]["background_adaptation"] = {
        "obligation_kind": "normative",
        "background_modes": background_modes,
        "rule_id": "slide-design-background-adaptation-v1",
    }
    system["decision_trace"]["system_design_intent"] = {
        "source": "system_decision",
        "semantic_design_profile": intent["semantic_design_profile"],
        "candidate_scores": intent["candidate_scores"],
    }
    return validate_visual_system(system, "visual_system", require_locked=True)


def validate_visual_system(value: Any, path: str, *, require_locked: bool) -> dict[str, Any]:
    if not require_locked:
        system = strict_object(value, path, {"id", "version"})
        require_string(system["id"], f"{path}.id")
        require_string(system["version"], f"{path}.version")
        return system

    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    schema = load_json(VISUAL_SYSTEM_SCHEMA_PATH, "Visual System v1 schema")
    try:
        Draft202012Validator(schema).validate(value)
    except JsonSchemaValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path)
        suffix = f".{location}" if location else ""
        fail(f"{path}{suffix} violates Visual System v1: {exc.message}")

    system = value
    strategy = validate_strategy(
        system["design_strategy"],
        f"{path}.design_strategy",
        {"design_strategy": system["design_strategy"]},
    )
    if system["aspect_ratio"] != "16:9":
        fail(f"{path}.aspect_ratio must be 16:9")
    provenance_hash = sha256_bytes(
        jcs_safe_bytes(system["selection_provenance"], f"{path}.selection_provenance")
    )
    if system["selection_provenance_sha256"] != provenance_hash:
        fail(f"{path}.selection_provenance_sha256 does not match provenance")
    if system["selection_provenance"]["design_strategy"] != strategy:
        fail(f"{path}.selection_provenance design strategy does not match")
    current_grammar_sha256 = sha256_bytes(EXPRESSION_GRAMMARS_PATH.read_bytes())
    if system["selection_provenance"]["grammar_asset_sha256"] != current_grammar_sha256:
        fail(f"{path}.selection_provenance grammar asset is not current")
    if system["prototype_selection"] != {
        "id": system["prototype_id"],
        "immutable": True,
        "selection_sha256": system["selection_provenance"]["selection_sha256"],
    }:
        fail(f"{path}.prototype_selection does not match prototype and provenance")
    input_hashes = system["decision_trace"]["input_hashes"]
    if input_hashes["prototype_selection"] != system["prototype_selection"]["selection_sha256"]:
        fail(f"{path}.decision_trace prototype selection hash does not match")
    if input_hashes["selection_provenance"] != system["selection_provenance_sha256"]:
        fail(f"{path}.decision_trace selection provenance hash does not match")
    if input_hashes["compiler_inputs"] != system["compilation"]["compiler_inputs_sha256"]:
        fail(f"{path}.compilation compiler input hash does not match decision trace")
    expected_compiler_hash = sha256_bytes(canonical_json_bytes({
        "compile_request_id": system["compilation"]["compile_request_id"],
        "design_strategy": strategy,
        "input_hashes": {
            key: value for key, value in input_hashes.items()
            if key != "compiler_inputs"
        },
    }))
    if system["compilation"]["compiler_inputs_sha256"] != expected_compiler_hash:
        fail(f"{path}.compilation compiler input hash is not derived from trace inputs")
    synthesis = load_synthesis_knowledge()
    synthesis_sha256 = sha256_bytes(SYNTHESIS_TRAITS_PATH.read_bytes())
    synthesis_trace = system["decision_trace"]["synthesis_knowledge"]
    if (
        input_hashes["synthesis_knowledge"] != synthesis_sha256
        or synthesis_trace["asset_sha256"] != synthesis_sha256
        or synthesis_trace["version"] != synthesis["version"]
        or synthesis_trace["prototype_role"] != "macro_structural_anchor_only"
        or set(synthesis_trace["trait_groups"]) != set(synthesis["trait_groups"])
    ):
        fail(f"{path}.decision_trace synthesis knowledge is not current")
    style_trace = system["decision_trace"]["style_synthesis"]
    library = synthesis["qualitative_trait_library"]
    traits_by_id = {
        trait["id"]: (bundle["id"], trait)
        for bundle in library["evidence_bundles"]
        for trait in bundle["traits"].values()
    }
    selected_ids = style_trace["selected_trait_ids"]
    expected_bundle_ids: dict[str, str] = {}
    expected_values: dict[str, list[str]] = {}
    expected_evidence: list[dict[str, Any]] = []
    for group in ("palette", "typography", "material", "geometry", "motion"):
        trait_id = selected_ids[group]
        if trait_id not in traits_by_id:
            fail(f"{path}.decision_trace.style_synthesis names an unknown trait")
        bundle_id, trait = traits_by_id[trait_id]
        expected_bundle_ids[group] = bundle_id
        expected_values[group] = trait["qualitative_values"]
        expected_evidence.extend(
            {"trait_id": trait_id, **evidence} for evidence in trait["evidence_refs"]
        )
    if (
        style_trace["prototype_role"] != "macro_structural_anchor_only"
        or style_trace["selected_bundle_ids"] != expected_bundle_ids
        or style_trace["selected_qualitative_values"] != expected_values
        or style_trace["evidence_refs"] != expected_evidence
        or style_trace["source_token_copy"] is not False
    ):
        fail(f"{path}.decision_trace.style_synthesis is not bound to current trait evidence")
    excluded_pairs = {
        frozenset((item["left_trait_id"], item["right_trait_id"]))
        for item in library["mutual_exclusions"]
    }
    selected_set = set(selected_ids.values())
    if any(pair <= selected_set for pair in excluded_pairs):
        fail(f"{path}.decision_trace.style_synthesis violates a trait exclusion")
    expected_token_groups = {
        "palette", "contrast", "typography", "spacing", "composition",
        "material", "echarts", "motion",
    }
    token_groups = [item["token_group"] for item in system["decision_trace"]["token_decisions"]]
    if set(token_groups) != expected_token_groups or len(token_groups) != len(expected_token_groups):
        fail(f"{path}.decision_trace.token_decisions must trace every token group exactly once")

    def relative_luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255.0 for index in (1, 3, 5)]
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast_ratio(left: str, right: str) -> float:
        lighter, darker = sorted(
            (relative_luminance(left), relative_luminance(right)), reverse=True
        )
        return (lighter + 0.05) / (darker + 0.05)

    actual_primary_contrast = contrast_ratio(
        system["palette"]["primary_text"], system["palette"]["surface"]
    )
    if actual_primary_contrast < system["contrast"]["normal_text_min_ratio"]:
        fail(f"{path} actual primary text contrast is below the declared normal-text gate")
    provenance_slide_ids = [
        item["slide_id"] for item in system["selection_provenance"]["grammar_selections"]
    ]
    if system["decision_trace"]["complete_slide_ids"] != provenance_slide_ids:
        fail(f"{path}.decision_trace.complete_slide_ids do not match provenance")
    slide_bindings = system["decision_trace"]["slide_request_bindings"]
    binding_slide_ids = [item["slide_id"] for item in slide_bindings]
    if (
        len(binding_slide_ids) != len(set(binding_slide_ids))
        or binding_slide_ids != provenance_slide_ids
    ):
        fail(f"{path}.decision_trace.slide_request_bindings do not match complete slides")
    for index, binding in enumerate(slide_bindings):
        binding_path = f"{path}.decision_trace.slide_request_bindings[{index}]"
        strict_object(
            binding,
            binding_path,
            {
                "slide_id", "shot_type", "render_mode", "duration_seconds",
                "source_content_sha256", "source_data_sha256",
            },
        )
        require_sha256(binding["source_content_sha256"], f"{binding_path}.source_content_sha256")
        require_sha256(binding["source_data_sha256"], f"{binding_path}.source_data_sha256")
    typography = system["typography"]
    if not (
        typography["display"]["size_px"] > typography["title"]["size_px"]
        > typography["body"]["size_px"] > typography["caption"]["size_px"]
    ):
        fail(f"{path}.typography must define a concrete display-title-body-caption hierarchy")
    for role, token in typography.items():
        stack = token["font_stack"]
        if any(
            "url(" in font.lower() or "://" in font or font.startswith(("/", "~"))
            for font in stack
        ):
            fail(f"{path}.typography.{role}.font_stack must be local-only")
    spacing = system["spacing"]
    if spacing["scale_px"] != sorted(spacing["scale_px"]):
        fail(f"{path}.spacing.scale_px must be ascending")
    if spacing["group_gap_px"] >= spacing["section_gap_px"]:
        fail(f"{path}.spacing group gap must be smaller than section gap")
    material = system["material"]
    if material["corner_radius_px"]["min"] > material["corner_radius_px"]["max"]:
        fail(f"{path}.material.corner_radius_px min must not exceed max")
    for name, interval in material["count_priors"].items():
        if interval[0] > interval[1]:
            fail(f"{path}.material.count_priors.{name} must be ascending")
    motion = system["motion"]
    transition = motion["transition_duration_seconds"]
    if transition is not None and not transition["min"] <= transition["preferred"] <= transition["max"]:
        fail(f"{path}.motion.transition_duration_seconds must be ordered")
    sequence = motion["sequence_end_seconds"]
    if sequence["preferred"] > sequence["max"]:
        fail(f"{path}.motion.sequence_end_seconds must be ordered")
    expected_gates = {
        "accessibility", "local_only_execution", "final_hold_stability",
        "source_fidelity", "non_overlap",
    }
    if set(system["decision_trace"]["hard_quality_gate_ids"]) != expected_gates:
        fail(f"{path}.decision_trace.hard_quality_gate_ids must name every hard gate")
    if set(system["hard_quality_gates"]) != expected_gates:
        fail(f"{path}.hard_quality_gates must contain every hard gate")

    role_weights = [token["weight"] for token in typography.values()]
    synthesis_observed = {
        "palette": {
            "dom_quantized_palette_count": (
                f"{path}.palette.visible_role_count_target",
                [system["palette"]["visible_role_count_target"]],
            ),
            "dom_dominant_color_role_ratio": (
                f"{path}.palette.dominant_color_area_ratio_target",
                [system["palette"]["dominant_color_area_ratio_target"]],
            ),
            "dominant_frame_to_median_text_contrast_ratio": (
                f"{path}.contrast.dominant_frame_to_text_target_ratio",
                [system["contrast"]["dominant_frame_to_text_target_ratio"]],
            ),
        },
        "typography": {
            "body_font_size_px": (
                f"{path}.typography.body.size_px",
                [typography["body"]["size_px"]],
            ),
            "display_to_body_size_ratio": (
                f"{path}.typography.display.size_px",
                [typography["display"]["size_px"] / typography["body"]["size_px"]],
            ),
            "font_weight_span": (
                f"{path}.typography",
                [max(role_weights) - min(role_weights)],
            ),
        },
        "material": {
            metric: (f"{path}.material.count_priors.{token}", material["count_priors"][token])
            for metric, token in {
                "shadow_layer_count": "shadow_layers",
                "gradient_layer_count": "gradient_layers",
                "filtered_layer_count": "filtered_layers",
                "bounded_panel_count": "bounded_panels",
                "bordered_element_count": "bordered_elements",
            }.items()
        },
        "geometry": {
            "svg_geometry_count": (
                f"{path}.material.count_priors.svg_geometry",
                material["count_priors"]["svg_geometry"],
            ),
            "connector_count": (
                f"{path}.material.count_priors.connectors",
                material["count_priors"]["connectors"],
            ),
            "left_alignment_reuse_ratio": (
                f"{path}.composition.left_edge_reuse_ratio_target",
                [system["composition"]["left_edge_reuse_ratio_target"]],
            ),
            "top_alignment_reuse_ratio": (
                f"{path}.composition.top_edge_reuse_ratio_target",
                [system["composition"]["top_edge_reuse_ratio_target"]],
            ),
        },
        "motion": {
            "maximum_animation_end_seconds": (
                f"{path}.motion.sequence_end_seconds",
                list(sequence.values()),
            ),
            "final_to_hold_normalized_mean_absolute_difference": (
                f"{path}.motion.final_to_hold_normalized_mean_absolute_difference_target",
                [motion["final_to_hold_normalized_mean_absolute_difference_target"]],
            ),
        },
    }
    if transition is not None:
        synthesis_observed["motion"]["maximum_animation_duration_seconds"] = (
            f"{path}.motion.transition_duration_seconds",
            list(transition.values()),
        )
    for group, metrics in synthesis_observed.items():
        for metric, (token_path, values) in metrics.items():
            lower, upper = synthesis_metric_envelope(synthesis, group, metric)
            if any(value < lower - 1.0e-6 or value > upper + 1.0e-6 for value in values):
                fail(f"{token_path} is outside synthesis evidence envelope")

    prototypes = load_json(VISUAL_PROTOTYPES_PATH, "visual prototype asset")
    prototype = next(
        (item for item in prototypes.get("items", []) if item.get("id") == system["prototype_id"]),
        None,
    )
    if prototype is None:
        fail(f"{path}.prototype_id is not a retained visual prototype")
    intent_priors = prototype["intent_intervals"]
    intent_bindings = system["decision_trace"]["intent_token_bindings"]
    if set(intent_bindings) != set(intent_priors) or any(
        not isinstance(paths, list)
        or not paths
        or any(not isinstance(token_path, str) or not token_path for token_path in paths)
        for paths in intent_bindings.values()
    ):
        fail(f"{path}.decision_trace.intent_token_bindings must bind every intent dimension")
    traits = {trait["metric"]: trait for trait in prototype["traits"]}
    traced_evidence = set(system["decision_trace"]["measured_prior_evidence_ids"])
    required_evidence = {
        evidence_id for trait in traits.values() for evidence_id in trait["evidence_ids"]
    }
    if not required_evidence <= traced_evidence:
        fail(f"{path}.decision_trace.measured_prior_evidence_ids is incomplete")
    departures = {
        item["metric"] for item in system["decision_trace"]["design_prior_departures"]
    }
    unknown_departures = departures - set(traits)
    if unknown_departures:
        fail(f"{path}.decision_trace.design_prior_departures names an unknown metric")
    observed_by_metric = {
        "dom_dominant_color_role_ratio": [system["palette"]["dominant_color_area_ratio_target"]],
        "dom_quantized_palette_count": [system["palette"]["visible_role_count_target"]],
        "dominant_frame_to_median_text_contrast_ratio": [system["contrast"]["dominant_frame_to_text_target_ratio"]],
        "body_font_size_px": [typography["body"]["size_px"]],
        "display_to_body_size_ratio": [typography["display"]["size_px"] / typography["body"]["size_px"]],
        "font_weight_span": [max(role_weights) - min(role_weights)],
        "occupancy_ratio": [system["composition"]["occupancy_ratio_target"]],
        "text_area_ratio": [system["composition"]["text_area_ratio_target"]],
        "largest_non_background_area_ratio": [system["composition"]["largest_object_area_ratio_target"]],
        "left_alignment_reuse_ratio": [system["composition"]["left_edge_reuse_ratio_target"]],
        "top_alignment_reuse_ratio": [system["composition"]["top_edge_reuse_ratio_target"]],
        "shadow_layer_count": system["material"]["count_priors"]["shadow_layers"],
        "gradient_layer_count": system["material"]["count_priors"]["gradient_layers"],
        "bordered_element_count": system["material"]["count_priors"]["bordered_elements"],
        "bounded_panel_count": system["material"]["count_priors"]["bounded_panels"],
        "svg_geometry_count": system["material"]["count_priors"]["svg_geometry"],
        "connector_count": system["material"]["count_priors"]["connectors"],
        "maximum_animation_end_seconds": list(sequence.values()),
    }
    if transition is not None:
        observed_by_metric["maximum_animation_duration_seconds"] = list(transition.values())
    final_hold_change = motion["final_to_hold_changed_pixel_ratio_target"]
    if final_hold_change is not None:
        observed_by_metric["final_to_hold_changed_pixel_ratio"] = [final_hold_change]
    missing_bindings = set(traits) - set(observed_by_metric)
    if missing_bindings:
        fail(f"{path} has no concrete token binding for measured priors")
    for metric, trait in traits.items():
        interval = trait["measured_interval"]
        outside = any(
            value < interval["lower"] or value > interval["upper"]
            for value in observed_by_metric[metric]
        )
        if outside and metric not in departures:
            fail(f"{path} departs from measured prior {metric} without a recorded rationale")

    intent_observed = {
        "dom_quantized_palette_count": [system["palette"]["visible_role_count_target"]],
        "dom_dominant_color_role_ratio": [system["palette"]["dominant_color_area_ratio_target"]],
        "median_effective_text_contrast_ratio": [system["contrast"]["median_effective_text_contrast_ratio_target"]],
        "display_to_body_size_ratio": [typography["display"]["size_px"] / typography["body"]["size_px"]],
        "occupancy_ratio": [system["composition"]["occupancy_ratio_target"]],
        "text_area_ratio": [system["composition"]["text_area_ratio_target"]],
        "largest_non_background_area_ratio": [system["composition"]["largest_object_area_ratio_target"]],
        "left_alignment_reuse_ratio": [system["composition"]["left_edge_reuse_ratio_target"]],
        "top_alignment_reuse_ratio": [system["composition"]["top_edge_reuse_ratio_target"]],
        "shadow_layer_count": material["count_priors"]["shadow_layers"],
        "gradient_layer_count": material["count_priors"]["gradient_layers"],
        "filtered_layer_count": material["count_priors"]["filtered_layers"],
        "bounded_panel_count": material["count_priors"]["bounded_panels"],
        "bordered_element_count": material["count_priors"]["bordered_elements"],
        "svg_geometry_count": material["count_priors"]["svg_geometry"],
        "connector_count": material["count_priors"]["connectors"],
        "maximum_animation_duration_seconds": list(transition.values()),
        "maximum_animation_end_seconds": list(sequence.values()),
        "final_to_hold_normalized_mean_absolute_difference": [
            motion["final_to_hold_normalized_mean_absolute_difference_target"]
        ],
    }
    for metric, interval in intent_priors.items():
        if any(
            observed < interval["lower"] - 1.0e-6 or observed > interval["upper"] + 1.0e-6
            for observed in intent_observed[metric]
        ):
            fail(f"{path} has a concrete token outside prototype intent interval {metric}")
    return system


def validate_source_content(value: Any) -> None:
    content = strict_object(value, "request.source_content", {"screen_content", "source_bindings"})
    if not isinstance(content["screen_content"], list) or not content["screen_content"]:
        fail("request.source_content.screen_content must be a non-empty array")
    if not isinstance(content["source_bindings"], list) or not content["source_bindings"]:
        fail("request.source_content.source_bindings must be a non-empty array")
    binding_ids: set[str] = set()
    for index, binding in enumerate(content["source_bindings"]):
        if not isinstance(binding, dict):
            fail(f"request.source_content.source_bindings[{index}] must be an object")
        binding_id = require_string(binding.get("id"), f"request.source_content.source_bindings[{index}].id")
        if binding_id in binding_ids:
            fail(f"duplicate source binding id {binding_id}")
        binding_ids.add(binding_id)
    content_ids: set[str] = set()
    for index, item in enumerate(content["screen_content"]):
        item_path = f"request.source_content.screen_content[{index}]"
        item = strict_object(item, item_path, {"content_id", "text", "source_binding_ids"})
        content_id = require_string(item["content_id"], f"{item_path}.content_id")
        if content_id in content_ids:
            fail(f"duplicate screen content_id {content_id}")
        content_ids.add(content_id)
        if not isinstance(item["text"], str):
            fail(f"{item_path}.text must be a string")
        if not isinstance(item["source_binding_ids"], list) or not item["source_binding_ids"]:
            fail(f"{item_path}.source_binding_ids must be a non-empty array")
        for binding_index, binding_id in enumerate(item["source_binding_ids"]):
            require_string(binding_id, f"{item_path}.source_binding_ids[{binding_index}]")
            if binding_id not in binding_ids:
                fail(f"screen content references unknown source binding {binding_id}")


def validate_html_data_bindings(value: Any) -> None:
    if not isinstance(value, list):
        fail("request.html_data_bindings must be an array")
    source_pointers: set[str] = set()
    targets: set[tuple[str, str]] = set()
    for index, raw in enumerate(value):
        path = f"request.html_data_bindings[{index}]"
        binding = strict_object(raw, path, {"source_pointer", "target_type", "target_id"})
        pointer = require_json_pointer(binding["source_pointer"], f"{path}.source_pointer")
        if pointer in source_pointers:
            fail(f"duplicate HTML source binding {pointer}")
        source_pointers.add(pointer)
        target_type = require_enum_string(binding["target_type"], f"{path}.target_type")
        if target_type not in {"content", "annotation"}:
            fail(f"{path}.target_type must be content or annotation")
        target_id = require_string(binding["target_id"], f"{path}.target_id")
        target = (target_type, target_id)
        if target in targets:
            fail(f"duplicate HTML data binding target {target_id}")
        targets.add(target)


def validate_request(
    value: Any,
    *,
    visual_system_artifact_bytes: bytes | None = None,
) -> dict[str, Any]:
    required = {
        "schema_id", "version", "request_id", "identity", "design_strategy",
        "visual_system", "aspect_ratio", "shot_type", "render_mode",
        "duration_seconds", "source_content", "source_content_sha256", "source_data",
        "source_data_sha256", "html_data_bindings", "final_frame_review_status",
    }
    request = strict_object(value, "request", required)
    reject_public_projection(request, "request")
    if request["schema_id"] != "smart-video.slide-generation-request.v1" or type(request["version"]) is not int or request["version"] != 1:
        fail("request schema/version must be smart-video.slide-generation-request.v1 version 1")
    require_string(request["request_id"], "request.request_id")
    identity = validate_identity(request["identity"], "request.identity")
    strategy = validate_strategy(request["design_strategy"], "request.design_strategy", request)
    if request["aspect_ratio"] != "16:9":
        fail("unsupported_aspect_ratio: request.aspect_ratio must be 16:9")
    shot_type = require_enum_string(request["shot_type"], "request.shot_type")
    if shot_type not in SLIDE_SHOT_TYPES:
        fail("request.shot_type must be html_only, avatar_html, or broll_html")
    render_mode = require_enum_string(request["render_mode"], "request.render_mode")
    if render_mode not in RENDER_MODES:
        fail("request.render_mode must be html_svg or echarts")
    duration = require_number(request["duration_seconds"], "request.duration_seconds", positive=True)
    if duration < MIN_SLIDE_DURATION_SECONDS:
        fail(
            "invalid_slide_environment: request.duration_seconds must be at least "
            f"{MIN_SLIDE_DURATION_SECONDS}"
        )
    system_ref = strict_object(
        request["visual_system"],
        "request.visual_system",
        {"id", "version", "sha256"},
    )
    require_string(system_ref["id"], "request.visual_system.id")
    require_string(system_ref["version"], "request.visual_system.version")
    expected_artifact_sha256 = require_sha256(
        system_ref["sha256"], "request.visual_system.sha256"
    )
    if visual_system_artifact_bytes is None:
        fail("blocked_missing_locked_visual_system: public validation requires a separate locked Visual System artifact")
    if type(visual_system_artifact_bytes) is not bytes:
        fail("locked Visual System artifact must be immutable raw bytes")
    actual_artifact_sha256 = sha256_bytes(visual_system_artifact_bytes)
    if actual_artifact_sha256 != expected_artifact_sha256:
        fail(
            "blocked_locked_visual_system_mismatch: request visual_system sha256 "
            "does not match artifact bytes"
        )
    try:
        visual_system_text = visual_system_artifact_bytes.decode("utf-8")
    except UnicodeError as exc:
        fail(f"locked Visual System artifact is not valid UTF-8: {exc}")
    visual_system_artifact = parse_json_text(
        visual_system_text, "locked Visual System artifact"
    )
    locked_system = validate_visual_system(
        visual_system_artifact, "locked_visual_system", require_locked=True
    )
    if (
        system_ref["id"] != locked_system["id"]
        or system_ref["version"] != locked_system["version"]
    ):
        fail("blocked_locked_visual_system_mismatch: request visual_system identity does not match artifact")
    if locked_system["design_strategy"] != strategy:
        fail("blocked_locked_visual_system_mismatch: request strategy does not match artifact")
    if locked_system["aspect_ratio"] != request["aspect_ratio"]:
        fail("blocked_locked_visual_system_mismatch: request aspect ratio does not match artifact")
    selected_bindings = [
        item for item in locked_system["decision_trace"]["slide_request_bindings"]
        if item["slide_id"] == identity["slide_id"]
    ]
    if len(selected_bindings) != 1:
        fail("blocked_stale_visual_selection: request slide is absent from locked Visual System")
    selected_binding = selected_bindings[0]
    for field in ("shot_type", "render_mode", "duration_seconds"):
        if request[field] != selected_binding[field]:
            fail(f"blocked_stale_visual_selection: request.{field} differs from locked Visual System")
    if request["final_frame_review_status"] != "pending_render":
        fail("request.final_frame_review_status must be pending_render")
    validate_source_content(request["source_content"])
    validate_html_data_bindings(request["html_data_bindings"])
    if request["render_mode"] == "echarts" and request["html_data_bindings"]:
        fail("request.html_data_bindings must be empty for echarts")
    for field in ("source_content", "source_data"):
        hash_field = f"{field}_sha256"
        supplied = require_sha256(request[hash_field], f"request.{hash_field}")
        actual = sha256_bytes(canonical_json_bytes(request[field]))
        if supplied != actual:
            fail(f"request.{hash_field} does not match canonical {field}")
        if supplied != selected_binding[hash_field]:
            fail(
                f"blocked_semantic_binding_mismatch: request.{hash_field} "
                "differs from locked Visual System"
            )
    validated = deepcopy(request)
    validated["_locked_visual_system"] = deepcopy(locked_system)
    return validated


def validate_artifact(value: Any, path: str, expected_stage: str) -> dict[str, Any]:
    artifact = strict_object(value, path, {"stage", "media_type", "path", "sha256"})
    stage = require_enum_string(artifact["stage"], f"{path}.stage")
    if stage != expected_stage:
        fail(f"{path}.stage must be {expected_stage}")
    media_type = require_enum_string(artifact["media_type"], f"{path}.media_type")
    if media_type not in {"text/html", "application/json"}:
        fail(f"{path}.media_type is unsupported")
    relative = Path(require_string(artifact["path"], f"{path}.path"))
    if relative.is_absolute() or len(relative.parts) != 1 or relative.name in {".", ".."}:
        fail(f"{path}.path must be one local filename")
    require_sha256(artifact["sha256"], f"{path}.sha256")
    return artifact


def validate_echarts_action(value: Any, path: str) -> str:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    if "type" not in value:
        fail(f"{path} is missing required field type")
    action_type = require_enum_string(value["type"], f"{path}.type")
    if action_type not in ECHARTS_ACTION_TYPES:
        fail(f"unsupported ECharts action {action_type}")
    required_by_type = {
        "establish_chart": {"type"},
        "reveal_series": {"type", "series_ids"},
        "highlight_data": {"type", "series_id", "data_indices"},
        "show_annotation": {"type", "series_id", "annotation"},
        "hold_conclusion": {"type"},
    }
    action = strict_object(value, path, required_by_type[action_type])
    if action_type == "reveal_series":
        series_ids = action["series_ids"]
        if not isinstance(series_ids, list) or not series_ids:
            fail("reveal_series.series_ids must be a non-empty array")
        normalized_ids = [
            require_string(item, f"reveal_series.series_ids[{index}]")
            for index, item in enumerate(series_ids)
        ]
        if len(set(normalized_ids)) != len(normalized_ids):
            fail("reveal_series.series_ids must contain unique values")
    elif action_type == "highlight_data":
        require_string(action["series_id"], "highlight_data.series_id")
        indices = action["data_indices"]
        if not isinstance(indices, list) or not indices:
            fail("highlight_data.data_indices must be a non-empty array")
        for index, item in enumerate(indices):
            if type(item) is not int or item < 0:
                fail(f"highlight_data.data_indices[{index}] must be a nonnegative integer")
        if len(set(indices)) != len(indices):
            fail("highlight_data.data_indices must contain unique values")
    elif action_type == "show_annotation":
        require_string(action["series_id"], "show_annotation.series_id")
        annotation = require_enum_string(action["annotation"], "show_annotation.annotation")
        if annotation not in {"markPoint", "markLine", "markArea"}:
            fail("show_annotation.annotation must be markPoint, markLine, or markArea")
    return action_type


def validate_timeline(phases: Any, duration: float, render_mode: str) -> None:
    if not isinstance(phases, list) or not phases:
        fail("manifest.motion_phases must be a non-empty array")
    if render_mode == "echarts" and len(phases) < 2:
        fail("ECharts motion phases must include establish_chart and hold_conclusion")
    previous_end = 0.0
    ids: set[str] = set()
    action_types: list[str | None] = []
    for index, raw in enumerate(phases):
        phase_path = f"manifest.motion_phases[{index}]"
        phase = strict_object(
            raw,
            phase_path,
            {"id", "start_seconds", "end_seconds", "state", "animation_name", "echarts_action"},
        )
        phase_id = require_string(phase["id"], f"manifest.motion_phases[{index}].id")
        if phase_id in ids:
            fail(f"duplicate motion phase id {phase_id}")
        ids.add(phase_id)
        start = require_number(phase["start_seconds"], f"manifest.motion_phases[{index}].start_seconds")
        end = require_number(phase["end_seconds"], f"manifest.motion_phases[{index}].end_seconds")
        if start < 0 or end <= start or end > duration:
            fail("motion phases must be ordered, positive intervals within duration")
        if not math.isclose(start, previous_end, abs_tol=1e-9):
            fail("motion phases must be contiguous")
        state = require_enum_string(phase["state"], f"manifest.motion_phases[{index}].state")
        if state not in {"active", "stable_hold"}:
            fail(f"manifest.motion_phases[{index}].state is invalid")
        if render_mode == "html_svg":
            if phase["echarts_action"] is not None:
                fail(f"{phase_path}.echarts_action must be null for html_svg")
            if state == "active":
                require_string(phase["animation_name"], f"{phase_path}.animation_name")
            elif phase["animation_name"] is not None:
                fail(f"{phase_path}.animation_name must be null for stable_hold")
            if index < len(phases) - 1 and state == "stable_hold":
                fail("only the final motion phase may be stable_hold")
            action_types.append(None)
        else:
            if phase["animation_name"] is not None:
                fail(f"{phase_path}.animation_name must be null for echarts")
            action_types.append(validate_echarts_action(phase["echarts_action"], f"{phase_path}.echarts_action"))
        previous_end = end
    if not math.isclose(previous_end, duration, abs_tol=1e-9):
        fail("motion phases must end at duration_seconds")
    if render_mode == "echarts":
        if phases[0]["state"] != "active" or action_types[0] != "establish_chart":
            fail("first ECharts motion phase must be active establish_chart")
        if phases[-1]["state"] != "stable_hold" or action_types[-1] != "hold_conclusion":
            fail("final ECharts motion phase must be stable_hold hold_conclusion")
        for index in range(1, len(phases) - 1):
            if phases[index]["state"] != "active" or action_types[index] not in {
                "reveal_series", "highlight_data", "show_annotation",
            }:
                fail("intermediate ECharts motion phase must use reveal_series, highlight_data, or show_annotation")
    elif phases[-1]["state"] != "stable_hold" or phases[-1]["end_seconds"] <= phases[-1]["start_seconds"]:
        fail("motion phases must end in a positive stable hold")


def validate_manifest(value: Any, request: dict[str, Any], phase: str) -> dict[str, Any]:
    required = {
        "schema_id", "version", "manifest_id", "request_id", "identity",
        "design_strategy", "visual_system", "aspect_ratio", "shot_type",
        "render_mode", "expression_grammar_version", "selection_provenance_sha256", "source_content_sha256",
        "source_data_sha256", "author_spec_sha256", "duration_seconds", "motion_phases",
        "final_frame_review_status", "artifacts",
    }
    manifest = strict_object(value, "manifest", required)
    reject_public_projection(manifest, "manifest")
    if manifest["schema_id"] != "smart-video.generation-manifest.v1" or type(manifest["version"]) is not int or manifest["version"] != 1:
        fail("manifest schema/version must be smart-video.generation-manifest.v1 version 1")
    require_string(manifest["manifest_id"], "manifest.manifest_id")
    if manifest["request_id"] != request["request_id"]:
        fail("manifest.request_id does not match request")
    validate_identity(manifest["identity"], "manifest.identity")
    validate_strategy(manifest["design_strategy"], "manifest.design_strategy", manifest)
    validate_visual_system(manifest["visual_system"], "manifest.visual_system", require_locked=False)
    manifest_shot_type = require_enum_string(manifest["shot_type"], "manifest.shot_type")
    if manifest_shot_type not in SLIDE_SHOT_TYPES:
        fail("manifest.shot_type must be html_only, avatar_html, or broll_html")
    manifest_render_mode = require_enum_string(manifest["render_mode"], "manifest.render_mode")
    if manifest_render_mode not in RENDER_MODES:
        fail("manifest.render_mode must be html_svg or echarts")
    grammar_version = load_json(EXPRESSION_GRAMMARS_PATH, "expression grammar asset").get("version")
    locked_system = request.get("_locked_visual_system")
    if not isinstance(locked_system, dict):
        fail("blocked_missing_locked_visual_system: request was not validated with its artifact")
    if manifest["expression_grammar_version"] != grammar_version:
        fail(
            "manifest.expression_grammar_version does not match request selection and current "
            "grammar asset"
        )
    agreements = (
        "identity", "design_strategy", "aspect_ratio", "shot_type", "render_mode",
        "source_content_sha256", "source_data_sha256",
        "duration_seconds",
    )
    for field in agreements:
        if manifest[field] != request[field]:
            fail(f"manifest.{field} does not match request")
    if manifest["selection_provenance_sha256"] != locked_system["selection_provenance_sha256"]:
        fail("manifest.selection_provenance_sha256 does not match compiled Visual System")
    expected_system = {key: request["visual_system"][key] for key in ("id", "version")}
    if manifest["visual_system"] != expected_system:
        fail("manifest.visual_system does not match request")
    if manifest["final_frame_review_status"] != "pending_render":
        fail("manifest.final_frame_review_status must be pending_render")
    duration = require_number(manifest["duration_seconds"], "manifest.duration_seconds", positive=True)
    validate_timeline(manifest["motion_phases"], duration, manifest_render_mode)
    artifacts = strict_object(manifest["artifacts"], "manifest.artifacts", {"author"}, {"adapter"})
    author = validate_artifact(artifacts["author"], "manifest.artifacts.author", "llm_author")
    if request["render_mode"] == "echarts":
        if require_sha256(manifest["author_spec_sha256"], "manifest.author_spec_sha256") != author["sha256"]:
            fail("manifest.author_spec_sha256 must match the ECharts author artifact")
    elif manifest["author_spec_sha256"] is not None:
        fail("manifest.author_spec_sha256 must be null for html_svg")
    adapter = artifacts.get("adapter")
    if phase == "pre-adapter":
        if adapter is not None:
            fail("pre-adapter requires manifest.artifacts.adapter to be null")
    else:
        if adapter is None:
            fail("manifest.artifacts.adapter is required after adaptation")
        validate_artifact(adapter, "manifest.artifacts.adapter", "trusted_local_adapter")
    return manifest
