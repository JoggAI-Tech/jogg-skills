#!/usr/bin/env python3
from __future__ import annotations

import unittest

from backend.services import video_studio_planner as planner
from backend.services import video_studio_visual_styles as visual_styles


class VisualStyleProfileSelectionTest(unittest.TestCase):
    def test_news_topic_selects_editorial_profile(self) -> None:
        profile = visual_styles.resolve_visual_style_profile(topic="AI 科技热点新闻")

        self.assertEqual(profile["id"], "editorial_tech_news")
        self.assertLessEqual(profile["accent_budget_percent"], 12)
        self.assertGreaterEqual(profile["contrast"]["ink_on_surface"], 4.5)

    def test_explicit_profile_wins_over_topic_inference(self) -> None:
        profile = visual_styles.resolve_visual_style_profile(
            topic="AI 科技热点新闻",
            requested="technical_blueprint",
        )

        self.assertEqual(profile["id"], "technical_blueprint")
        self.assertEqual(profile["glow_policy"], "none")

    def test_legacy_palette_maps_to_semantic_roles(self) -> None:
        profile = visual_styles.resolve_visual_style_profile(
            topic="AI 科技热点新闻",
            requested="editorial_tech_news",
            legacy_palette=["#0B0F14", "#E7F0F7", "#2DD4BF", "#F4C95D", "#E35D6A"],
        )

        self.assertEqual(profile["palette"]["surface"], "#0B0F14")
        self.assertEqual(profile["palette"]["ink"], "#E7F0F7")
        self.assertEqual(profile["palette"]["primary"], "#2DD4BF")
        self.assertEqual(profile["palette"]["highlight"], "#F4C95D")
        self.assertEqual(profile["palette"]["danger"], "#E35D6A")
        self.assertGreaterEqual(profile["contrast"]["ink_on_surface"], 4.5)

    def test_profile_color_normalizes_to_semantic_token(self) -> None:
        profile = visual_styles.resolve_visual_style_profile(topic="AI 科技热点新闻")

        self.assertEqual(
            visual_styles.semantic_color_token(profile, profile["palette"]["primary"]),
            "var(--mg-primary)",
        )
        self.assertEqual(visual_styles.semantic_color_token(profile, "#22D3EE"), "")


class VisualStylePlannerContractTest(unittest.TestCase):
    def _director(self, profile: dict | None = None) -> dict:
        director = {
            "version": "mg_director_v1",
            "enabled": True,
            "render_strategy": "llm_bespoke_html",
            "visual_system": "causal",
            "story_goal": "解释芯片需求如何传导到算力建设。",
            "one_learning_point": "应用需求最终落到基础设施。",
            "main_visual_metaphor": "一条从应用流向芯片与机房的宽路径。",
            "visual_recipe": {
                "composition_id": "causal_spine",
                "hero_device_id": "semantic_icon_cluster",
                "material_id": "editorial_color_field",
                "motion_id": "directional_build_lock",
                "originality_note": "把需求传导原创为一条宽幅折返路径。",
            },
            "composition": {
                "animation_type": "self_contained_html",
                "layout": "directional_path",
                "hero_frame": {"kind": "需求传导路径", "x": 90, "y": 110, "w": 1740, "h": 760},
                "typography": {"headline_scale": "display", "headline_min_px": 72, "supporting_min_px": 30},
                "visual_primitives": ["path", "node", "icon"],
                "icon_semantics": ["应用", "芯片", "机房"],
                "motion_choreography": "路径建立，节点依次进入，最后锁定机房。",
            },
            "screen_slots": [
                {"role": "headline", "text": "需求向基础设施传导"},
                {"role": "takeaway", "text": "芯片与算力成为落点"},
            ],
        }
        if profile:
            director["visual_style_profile"] = profile
        return director

    def test_requirement_document_persists_selected_profile(self) -> None:
        requirement = planner.normalize_requirement_document(
            {
                "html_mg_direction": {
                    "visual_style_profile_id": "technical_blueprint",
                    "palette": ["#F1F4F2", "#172127", "#2A6F97", "#C75133", "#B23A48"],
                }
            },
            "芯片架构",
            "broll_html",
        )

        direction = requirement["html_mg_direction"]
        self.assertEqual(direction["visual_style_profile_id"], "technical_blueprint")
        self.assertEqual(direction["visual_style_profile"]["id"], "technical_blueprint")
        self.assertEqual(direction["palette"], ["#F1F4F2", "#172127", "#2A6F97", "#C75133", "#B23A48"])

    def test_overlay_contract_exposes_profile_tokens_and_material_override(self) -> None:
        profile = visual_styles.resolve_visual_style_profile(topic="AI 科技热点新闻")
        director = self._director(profile)
        shot = {
            "id": "shot-01",
            "duration_seconds": 8,
            "mg_director": director,
        }
        clip = {"id": "mg:shot-01", "mg_director": director}

        contract = planner._html_overlay_contract_for_clip("AI 科技热点新闻", clip, [shot])

        self.assertEqual(contract["visual_style_profile"]["id"], "editorial_tech_news")
        self.assertEqual(contract["style_tokens"]["css_variables"]["--mg-ink"], profile["palette"]["ink"])
        self.assertEqual(contract["material_style_override"]["material_id"], "editorial_color_field")
        self.assertIn("no_undeclared_color_literals", contract["visual_quality_rules"])


class AuthoredStyleValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = visual_styles.resolve_visual_style_profile(topic="AI 科技热点新闻")

    def test_rejects_undeclared_literal_color(self) -> None:
        report = visual_styles.validate_authored_style(
            '<main class="ai-mg-layer"><h1 class="hero">热点</h1></main>',
            ".hero{color:#22d3ee}",
            self.profile,
            material_id="editorial_color_field",
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("硬编码颜色" in error for error in report["errors"]))

    def test_accepts_semantic_color_and_font_variables(self) -> None:
        report = visual_styles.validate_authored_style(
            '<main class="ai-mg-layer"><h1 class="hero">热点</h1><p class="copy">变化</p></main>',
            ".hero{color:var(--mg-ink);font-family:var(--mg-font-display)}"
            ".copy{color:var(--mg-primary);font-family:var(--mg-font-body)}",
            self.profile,
            material_id="editorial_color_field",
        )

        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["metrics"]["semantic_color_roles"], 2)

    def test_endpoint_glow_is_bounded_by_material(self) -> None:
        report = visual_styles.validate_authored_style(
            '<main class="ai-mg-layer"><i class="mg-endpoint"></i></main>',
            ".mg-endpoint{color:var(--mg-primary);filter:drop-shadow(0 0 8px var(--mg-primary))}",
            self.profile,
            material_id="luminous_data",
        )

        self.assertTrue(report["ok"], report["errors"])

    def test_rejects_glow_on_generic_selector(self) -> None:
        report = visual_styles.validate_authored_style(
            '<main class="ai-mg-layer"><div class="hero"></div></main>',
            ".hero{color:var(--mg-primary);filter:drop-shadow(0 0 24px var(--mg-primary))}",
            self.profile,
            material_id="luminous_data",
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("发光" in error for error in report["errors"]))

    def test_rejects_redefinition_of_project_color_tokens(self) -> None:
        report = visual_styles.validate_authored_style(
            '<main class="ai-mg-layer"><h1 class="hero">热点</h1></main>',
            ".ai-mg-layer{--mg-primary:var(--mg-highlight)}.hero{color:var(--mg-primary)}",
            self.profile,
            material_id="editorial_color_field",
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("重定义" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
