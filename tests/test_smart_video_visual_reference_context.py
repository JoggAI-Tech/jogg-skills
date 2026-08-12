"""Template-free ordinary Slides and compact ECharts-reference contracts."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

from smartvideo_test_runtime import (  # noqa: F401
    AGGREGATE_PACKAGE_ROOT,
    PLUGIN_ROOT,
    RUNTIME_ROOT,
)

source_runtime = os.environ.get("SMARTVIDEO_RUNTIME_SOURCE_ROOT", "").strip()
if source_runtime:
    sys.path.insert(0, str(Path(source_runtime).expanduser().resolve()))

from backend.services import video_studio_mg_templates, video_studio_reference_patch  # noqa: E402
from backend.services.video_content_pipeline.contracts import HtmlGenerationRequest  # noqa: E402
from backend.services.video_content_pipeline.smart_video_adapter import (  # noqa: E402
    SemanticVisualDecision,
    build_pending_html_authoring_contexts,
    build_smart_video_mg_director,
)


class SmartVideoDirectSlideTests(unittest.TestCase):
    def test_html_director_does_not_require_or_emit_template_id(self) -> None:
        request = self._request()
        director = build_smart_video_mg_director(
            request,
            SemanticVisualDecision(
                scene_id="before_after_transform",
                selection_reason="The information is a before-and-after comparison",
            ),
        )

        reference = director["visual_reference"]
        self.assertNotIn("template_id", reference)
        self.assertEqual(reference["reference_mode"], "visual_recompose")
        self.assertFalse(reference["fallback_automatic"])
        self.assertTrue(reference["free_generation_selected"])

    def test_pending_html_context_contains_no_template_derived_fields(self) -> None:
        planning = {"scene_groups": [{"shots": [self._html_shot("shot-01", "mg:shot-01")]}]}

        context = build_pending_html_authoring_contexts(planning)["mg:shot-01"]

        self.assertEqual(context["authoring_mode"], "direct_slide_html_v1")
        self.assertEqual(context["scene_id"], "before_after_transform")
        self.assertEqual(context["fidelity"], "adaptive")
        for field in (
            "template_id",
            "original_template_id",
            "reference_html",
            "reference_html_path",
            "reference_html_sha256",
            "strong_reference_contract",
            "semantic_adaptation",
            "contract",
            "composition",
            "prompt",
        ):
            self.assertNotIn(field, context)

    def test_html_context_rejects_a_template_locator(self) -> None:
        shot = self._html_shot("shot-01", "mg:shot-01")
        shot["mg_director"]["visual_reference"]["template_id"] = "before_after_transform--duel"

        with self.assertRaisesRegex(ValueError, "must not depend on a visual template"):
            build_pending_html_authoring_contexts({"scene_groups": [{"shots": [shot]}]})

    def test_same_clip_requires_one_scene_and_ratio(self) -> None:
        first = self._html_shot("shot-01", "mg:shared")
        second = self._html_shot("shot-02", "mg:shared")
        second["mg_director"]["scene_id"] = "benchmark_gap"

        with self.assertRaisesRegex(ValueError, "conflicting semantic scenes or ratios"):
            build_pending_html_authoring_contexts({"scene_groups": [{"shots": [first, second]}]})

    def test_lifecycle_returns_private_authoring_context(self) -> None:
        runner = (AGGREGATE_PACKAGE_ROOT / "bin" / "smartvideo-runtime.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("build_pending_html_authoring_contexts", runner)
        self.assertIn('"authoring_context": contexts.get(clip_id, {})', runner)
        self.assertIn("authoring_context:($clip.authoring_context // {})", runner)

    def test_historical_strong_reference_parser_remains_available(self) -> None:
        contract = video_studio_reference_patch.build_strong_reference_contract(
            '<main class="mg-content"><h1>Primary claim</h1></main>'
        )
        self.assertEqual(contract["version"], "strong_reference_contract_v1")

    @staticmethod
    def _request() -> HtmlGenerationRequest:
        return HtmlGenerationRequest(
            request_id="request-01",
            shot_id="shot-01",
            segment_id="segment-01",
            start_seconds=0,
            end_seconds=5,
            information_task="compare",
            production_story_input={
                "topic": "Factory modernization",
                "audience": "general audience",
                "script": "Efficiency improved after modernization.",
                "claims": [{"id": "claim-01", "statement": "Efficiency improved"}],
                "entities": [
                    {"id": "before", "label": "Before"},
                    {"id": "after", "label": "After"},
                ],
                "relations": [{"type": "contrast", "from": "before", "to": "after"}],
                "source_status": "untrusted",
            },
        )

    @staticmethod
    def _html_shot(shot_id: str, clip_id: str) -> dict[str, object]:
        return {
            "id": shot_id,
            "duration_seconds": 5,
            "scene_role": "broll_backdrop_overlay",
            "information_layer": {"enabled": True},
            "html_render_strategy": "llm_bespoke_html",
            "html_design": {"clip_id": clip_id},
            "mg_director": {
                "version": "semantic_mg_director",
                "enabled": True,
                "clip_id": clip_id,
                "render_strategy": "llm_bespoke_html",
                "render_mode": "html",
                "scene_id": "before_after_transform",
                "story_contract": {"content_shape": {"primary_encoding": "compare"}},
                "information_object_plan": {"required_objects": ["before", "after"]},
                "visual_reference": {
                    "ratio": "16:9",
                    "selection_reason": "Before-and-after information shape",
                    "reference_mode": "visual_recompose",
                    "fallback_automatic": False,
                    "free_generation_selected": True,
                },
                "screen_slots": [{"role": "headline", "text": "Before and after"}],
            },
        }


class SmartVideoCompactEchartsReferenceTests(unittest.TestCase):
    def test_catalog_has_no_template_assets_and_at_most_two_candidates(self) -> None:
        root = PLUGIN_ROOT / "skills" / "smart-video" / "assets" / "semantic-mg-references"
        files = [path for path in root.rglob("*") if path.is_file()]
        self.assertEqual([path.name for path in files], ["scene-template-map.json"])

        catalog = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(catalog["version"], "semantic_scene_catalog")
        self.assertEqual(catalog["scene_count"], 72)
        self.assertEqual(catalog["template_count"], 54)
        for scene in catalog["mappings"]:
            candidates = scene["candidates"]
            self.assertLessEqual(len(candidates), 2)
            if scene["echarts_supported"]:
                self.assertGreaterEqual(len(candidates), 1)
            else:
                self.assertEqual(candidates, [])

    def test_retained_reference_is_metadata_only(self) -> None:
        reference = video_studio_mg_templates.get_semantic_reference_template(
            "single_kpi--chart", "16:9"
        )
        self.assertEqual(reference["implementation_modes"], ["echarts"])
        self.assertFalse(reference["html_available"])
        self.assertIn("composition", reference)
        for field in ("reference_html", "reference_html_path", "contract", "prompt"):
            self.assertNotIn(field, reference)
        with self.assertRaisesRegex(ValueError, "do not include template HTML"):
            video_studio_mg_templates.get_semantic_reference_template(
                "single_kpi--chart", "16:9", include_html=True
            )


if __name__ == "__main__":
    unittest.main()
