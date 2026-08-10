"""visual reference selection and pending HTML authoring-context contracts."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


from smartvideo_test_runtime import NPM_ROOT, PLUGIN_ROOT, RUNTIME_ROOT  # noqa: F401

from backend.services.video_content_pipeline.smart_video_adapter import (  # noqa: E402
    SemanticVisualDecision,
    build_pending_html_authoring_contexts,
    build_smart_video_mg_director,
    resolve_visual_reference_decision,
)
from backend.services.video_content_pipeline.contracts import HtmlGenerationRequest  # noqa: E402
from backend.services import (  # noqa: E402
    video_studio_mg_templates,
    video_studio_planner,
    video_studio_reference_patch,
)


class SmartVideoVisualReferenceDecisionTests(unittest.TestCase):
    def test_matching_scene_within_capacity_uses_strong_reference(self) -> None:
        decision = resolve_visual_reference_decision(
            scene_id="before_after_transform",
            template_id="before_after_transform--duel",
            ratio="16:9",
            required_objects=["before", "after"],
            relations=[{"type": "contrast"}],
            screen_slots=[{"role": "headline", "text": "改造前后发生了明确变化"}],
            duration_seconds=5,
        )

        self.assertEqual(decision["reference_mode"], "strong_reference")
        self.assertEqual(decision["template_id"], "before_after_transform--duel")
        self.assertFalse(decision["template_changed"])
        self.assertTrue(decision["capacity_analysis"]["fits"])

    def test_matching_scene_over_capacity_uses_visual_recompose(self) -> None:
        decision = resolve_visual_reference_decision(
            scene_id="before_after_transform",
            template_id="before_after_transform--duel",
            ratio="9:16",
            required_objects=[f"object-{index}" for index in range(12)],
            relations=[{"type": "contrast"} for _ in range(8)],
            screen_slots=[{"role": "headline", "text": "很长的上屏文字" * 40}],
            duration_seconds=2,
        )

        self.assertEqual(decision["reference_mode"], "visual_recompose")
        self.assertEqual(decision["template_id"], "before_after_transform--duel")
        self.assertFalse(decision["template_changed"])
        self.assertFalse(decision["capacity_analysis"]["fits"])
        self.assertTrue(decision["capacity_analysis"]["overflow_reasons"])

    def test_matching_scene_retries_a_fitting_reference_before_recompose(self) -> None:
        decision = resolve_visual_reference_decision(
            scene_id="feature_matrix",
            template_id="feature_matrix--duel",
            ratio="16:9",
            required_objects=["left", "right"],
            relations=[{"type": "contrast"}],
            screen_slots=[{"role": "headline", "text": "X" * 100}],
            duration_seconds=5,
        )

        self.assertEqual(decision["reference_mode"], "strong_reference")
        self.assertEqual(decision["template_id"], "feature_matrix--evidence")
        self.assertTrue(decision["template_changed"])
        self.assertTrue(decision["capacity_analysis"]["fits"])
        self.assertFalse(decision["fallback_automatic"])

    def test_mismatched_scene_prefers_same_visual_id_and_records_switch(self) -> None:
        decision = resolve_visual_reference_decision(
            scene_id="countdown_schedule",
            template_id="case_study--analysis",
            ratio="16:9",
            required_objects=["deadline"],
            relations=[{"type": "sequence"}],
            screen_slots=[{"role": "headline", "text": "距离发布还有三天"}],
            duration_seconds=5,
        )

        self.assertEqual(decision["reference_mode"], "scene_reselected_reference")
        self.assertEqual(decision["original_template_id"], "case_study--analysis")
        self.assertEqual(decision["template_id"], "countdown_schedule--inflection")
        self.assertTrue(decision["template_changed"])
        self.assertIn("visual_id", decision["template_change_reason"])

    def test_director_normalization_preserves_template_switch_audit(self) -> None:
        request = HtmlGenerationRequest(
            request_id="request-01",
            shot_id="shot-01",
            segment_id="segment-01",
            start_seconds=0,
            end_seconds=5,
            information_task="timeline",
            production_story_input={
                "topic": "产品发布倒计时",
                "audience": "general audience",
                "script": "距离发布还有三天。",
                "claims": [{"id": "claim-01", "statement": "距离发布还有三天"}],
                "entities": [
                    {"id": "today", "label": "今天"},
                    {"id": "deadline", "label": "发布日"},
                ],
                "relations": [{"type": "sequence", "from": "today", "to": "deadline"}],
                "source_status": "untrusted",
            },
        )
        visual = SemanticVisualDecision(
            scene_id="countdown_schedule",
            template_id="case_study--analysis",
            selection_reason="用户原先选择档案视觉",
        )

        director = build_smart_video_mg_director(request, visual)
        reference = director["visual_reference"]

        self.assertEqual(reference["template_id"], "countdown_schedule--inflection")
        self.assertEqual(reference["original_template_id"], "case_study--analysis")
        self.assertEqual(reference["reference_mode"], "scene_reselected_reference")
        self.assertTrue(reference["template_changed"])
        self.assertTrue(reference["template_change_reason"])

        explicit_free = build_smart_video_mg_director(
            request,
            SemanticVisualDecision(
                scene_id="countdown_schedule",
                template_id="countdown_schedule--inflection",
                selection_reason="用户明确选择自由生成",
                free_generation_selected=True,
            ),
        )["visual_reference"]
        self.assertEqual(explicit_free["reference_mode"], "visual_recompose")
        self.assertFalse(explicit_free["fallback_automatic"])
        self.assertTrue(explicit_free["free_generation_selected"])


class SmartVideoVisualReferenceAuthoringContextTests(unittest.TestCase):
    def test_extracted_model_prompt_contains_complete_reference_and_trace(self) -> None:
        reference = video_studio_mg_templates.get_semantic_reference_template(
            "before_after_transform--duel",
            "16:9",
        )
        clip = {
            "id": "mg:shot-01",
            "bound_shots": ["shot-01"],
            "mg_director": {
                "version": "semantic_mg_director",
                "enabled": True,
                "render_mode": "html",
                "scene_id": "before_after_transform",
                "visual_system": "comparison",
                "visual_reference": {
                    **reference,
                    "selection_reason": "对照关系清晰",
                    "fidelity": "normal",
                    "usage": ["style", "layout", "motion", "component"],
                },
                "presentation_weight": "explain",
                "mg_priority": 70,
                "active_window": {"start_s": 0.5, "end_s": 4.5},
                "screen_slots": [{"role": "headline", "text": "改造前后"}],
            },
        }
        shot = {
            "id": "shot-01",
            "title": "改造前后",
            "duration_seconds": 5,
            "mg_director": clip["mg_director"],
        }
        reference_with_html = video_studio_mg_templates.get_semantic_reference_template(
            "before_after_transform--duel",
            "16:9",
            include_html=True,
        )
        reference_html = reference_with_html["reference_html"]
        reference_hash = hashlib.sha256(reference_html.encode("utf-8")).hexdigest()

        prompt = video_studio_planner._bespoke_html_asset_prompt("改造案例", clip, [shot])

        self.assertIn(reference_html, prompt)
        self.assertIn('template_id="before_after_transform--duel"', prompt)
        self.assertIn('ratio="16:9"', prompt)
        self.assertIn(f'sha256="{reference_hash}"', prompt)
        self.assertIn(f'"reference_html_sha256": "{reference_hash}"', prompt)

    def test_lifecycle_initializes_and_returns_authoring_context(self) -> None:
        runner = (
            NPM_ROOT / "packages" / "smartvideo" / "bin" / "smartvideo-runtime.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("build_pending_html_authoring_contexts", runner)
        planning_function = runner.split("planning_html_clips() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("python_bin=$(host_python)", planning_function)
        self.assertNotIn("ensure_python_runtime", planning_function)
        self.assertIn('"authoring_context": contexts.get(clip_id, {})', runner)
        self.assertIn("authoring_context:($clip.authoring_context // {})", runner)
        self.assertIn("html_clip_checkpoints,pending_clip_ids", runner)

    def test_pending_context_contains_complete_selected_reference(self) -> None:
        planning = {
            "visual_style_profile": {"id": "editorial_tech_news"},
            "scene_groups": [{
                "id": "section-01",
                "shots": [{
                    "id": "shot-01",
                    "duration_seconds": 5,
                    "scene_role": "broll_backdrop_overlay",
                    "information_layer": {"enabled": True},
                    "html_render_strategy": "llm_bespoke_html",
                    "html_design": {"clip_id": "mg:shot-01"},
                    "mg_director": {
                        "version": "semantic_mg_director",
                        "enabled": True,
                        "clip_id": "mg:shot-01",
                        "render_strategy": "llm_bespoke_html",
                        "render_mode": "html",
                        "scene_id": "before_after_transform",
                        "story_contract": {"script": "改造后效率更高"},
                        "information_object_plan": {
                            "required_objects": ["before", "after"],
                            "reading_order": ["before", "after"],
                            "object_content_bindings": [],
                        },
                        "visual_reference": {
                            "template_id": "before_after_transform--duel",
                            "ratio": "16:9",
                            "selection_reason": "对照关系清晰",
                            "reference_mode": "strong_reference",
                            "original_template_id": "before_after_transform--duel",
                            "template_changed": False,
                            "template_change_reason": "",
                        },
                        "active_window": {"start_s": 0.5, "end_s": 4.5},
                        "screen_slots": [{"role": "headline", "text": "改造前后"}],
                    },
                }],
            }],
        }

        contexts = build_pending_html_authoring_contexts(planning)
        context = contexts["mg:shot-01"]

        self.assertEqual(context["template_id"], "before_after_transform--duel")
        self.assertEqual(context["ratio"], "16:9")
        self.assertIn("<", context["reference_html"])
        self.assertIsInstance(context["contract"], dict)
        self.assertIsInstance(context["composition"], dict)
        self.assertTrue(context["prompt"])
        self.assertEqual(
            context["reference_html_sha256"],
            hashlib.sha256(context["reference_html"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(context["bound_shot_ids"], ["shot-01"])
        self.assertEqual(context["reference_mode"], "strong_reference")
        self.assertEqual(context["free_generation_style"], {})

    def test_automatic_recompose_does_not_receive_free_generation_style(self) -> None:
        shot = self._shot("shot-01", "before_after_transform--duel")
        shot["html_design"] = {"clip_id": "mg:adaptive"}
        director = shot["mg_director"]
        director["clip_id"] = "mg:adaptive"
        director["story_contract"] = {"content_shape": {"primary_encoding": "timeline"}}
        director["visual_reference"]["reference_mode"] = "visual_recompose"
        director["visual_reference"]["fallback_automatic"] = True
        planning = {"scene_groups": [{"shots": [shot]}]}

        context = build_pending_html_authoring_contexts(planning)["mg:adaptive"]

        self.assertEqual(context["fidelity"], "adaptive")
        self.assertEqual(context["free_generation_style"], {})
        self.assertTrue(context["fallback_automatic"])
        self.assertIn("semantic_unit_structure", context["reference_edit_policy"]["allowed_changes"])

    def test_adaptive_context_without_automatic_fallback_still_has_no_free_style(self) -> None:
        shot = self._shot("shot-01", "before_after_transform--duel")
        shot["html_design"] = {"clip_id": "mg:legacy-adaptive"}
        director = shot["mg_director"]
        director["clip_id"] = "mg:legacy-adaptive"
        director["visual_reference"]["reference_mode"] = "visual_recompose"
        director["visual_reference"].pop("fallback_automatic", None)
        planning = {"scene_groups": [{"shots": [shot]}]}

        context = build_pending_html_authoring_contexts(planning)["mg:legacy-adaptive"]

        self.assertEqual(context["fidelity"], "adaptive")
        self.assertEqual(context["free_generation_style"], {})

    def test_explicit_free_generation_receives_information_task_style(self) -> None:
        shot = self._shot("shot-01", "before_after_transform--duel")
        shot["html_design"] = {"clip_id": "mg:explicit-free"}
        director = shot["mg_director"]
        director["clip_id"] = "mg:explicit-free"
        director["story_contract"] = {"content_shape": {"primary_encoding": "timeline"}}
        director["visual_reference"]["reference_mode"] = "visual_recompose"
        director["visual_reference"]["fallback_automatic"] = False
        director["visual_reference"]["free_generation_selected"] = True
        planning = {"scene_groups": [{"shots": [shot]}]}

        context = build_pending_html_authoring_contexts(planning)["mg:explicit-free"]

        self.assertEqual(context["fidelity"], "adaptive")
        self.assertEqual(context["free_generation_style"]["id"], "material_collage")
        self.assertFalse(context["fallback_automatic"])

    def test_conflicting_directors_cannot_share_one_clip(self) -> None:
        planning = {
            "scene_groups": [{
                "shots": [
                    self._shot("shot-01", "before_after_transform--duel"),
                    self._shot("shot-02", "before_after_transform--evidence"),
                ],
            }],
        }

        with self.assertRaisesRegex(ValueError, "conflicting visual references"):
            build_pending_html_authoring_contexts(planning)

    def test_strong_reference_contract_exposes_semantic_roles_and_groups(self) -> None:
        contract = video_studio_reference_patch.build_strong_reference_contract(
            """<!doctype html><html><head><title>Accessible title</title></head><body>
            <main class="mg-content"><h1>Primary claim</h1>
            <div class="proof-item"><b>42%</b><span>Growth</span></div></main>
            </body></html>"""
        )

        targets = {target["current_text"]: target for target in contract["text_targets"]}
        self.assertEqual(targets["Primary claim"]["semantic_role"], "headline")
        self.assertEqual(targets["42%"]["semantic_role"], "support_value")
        self.assertEqual(targets["42%"]["semantic_group"], "proof_item")
        self.assertEqual(targets["Growth"]["semantic_role"], "support_label")
        self.assertNotIn("css_override", contract["patch_schema"]["optional"])
        with self.assertRaisesRegex(
            video_studio_reference_patch.StrongReferenceError,
            "do not allow CSS overrides",
        ):
            video_studio_reference_patch._validate_css_override(".ai-mg-layer{color:red}")

    @staticmethod
    def _shot(shot_id: str, template_id: str) -> dict[str, object]:
        return {
            "id": shot_id,
            "duration_seconds": 5,
            "scene_role": "broll_backdrop_overlay",
            "information_layer": {"enabled": True},
            "html_render_strategy": "llm_bespoke_html",
            "html_design": {"clip_id": "mg:shared"},
            "mg_director": {
                "version": "semantic_mg_director",
                "enabled": True,
                "clip_id": "mg:shared",
                "render_strategy": "llm_bespoke_html",
                "render_mode": "html",
                "scene_id": "before_after_transform",
                "story_contract": {},
                "information_object_plan": {"required_objects": ["before", "after"]},
                "visual_reference": {
                    "template_id": template_id,
                    "ratio": "16:9",
                    "selection_reason": "test",
                },
                "screen_slots": [{"role": "headline", "text": "改造前后"}],
            },
        }


if __name__ == "__main__":
    unittest.main()
