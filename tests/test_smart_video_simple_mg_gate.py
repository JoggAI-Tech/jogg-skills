"""Post-planning MG validation should stay lightweight and render-focused."""

from __future__ import annotations

import unittest
from pathlib import Path


from smartvideo_test_runtime import NPM_ROOT, PLUGIN_ROOT, RUNTIME_ROOT  # noqa: F401

from backend.services import video_studio_bespoke_html, video_studio_planner  # noqa: E402


class SmartVideoSimpleMgGateTests(unittest.TestCase):
    def test_planned_aesthetic_diagnostics_do_not_block_html(self) -> None:
        validation = video_studio_planner._validate_bespoke_html_asset(
            custom_html=(
                '<main class="ai-mg-layer" data-ai-generated-html="true" '
                'data-mg-opaque="true"><div>未授权文案</div><div>第二块文字</div></main>'
            ),
            custom_css=".ai-mg-layer{position:absolute;inset:0}",
            edit_schema={},
            overlay_contract={
                "duration_seconds": 5,
                "bound_shots": [{"id": "shot-01"}],
                "slots": [{"role": "headline", "text": "规划授权文案"}],
                "output_limits": {"max_visible_text_blocks": 1},
                "mg_director": {
                    "version": "semantic_mg_director",
                    "presentation_weight": "explain",
                },
                "composition": {
                    "layout": "single_focus",
                    "motion_choreography": "先建立主体，再揭示结论",
                    "visual_primitives": ["icon"],
                },
            },
        )

        self.assertTrue(validation["ok"])
        self.assertEqual(validation["errors"], [])
        warning_text = "\n".join(validation["warnings"])
        self.assertIn("可见文字块", warning_text)
        self.assertIn("未获 content brief 授权", warning_text)
        self.assertIn("不透明全屏底板", warning_text)
        self.assertIn("动效", warning_text)
        self.assertFalse(validation["composition_execution"]["ok"])

    def test_unsafe_html_and_css_remain_blocking(self) -> None:
        validation = video_studio_planner._validate_bespoke_html_asset(
            custom_html=(
                '<main class="ai-mg-layer" data-ai-generated-html="true">'
                '<script>alert(1)</script></main>'
            ),
            custom_css="@import 'https://example.com/unsafe.css';",
            edit_schema={},
            overlay_contract={},
        )

        self.assertFalse(validation["ok"])
        self.assertTrue(any("禁用标签" in item for item in validation["errors"]))
        self.assertTrue(any("外链或脚本风险" in item for item in validation["errors"]))

    def test_style_policy_failures_are_attached_as_warnings(self) -> None:
        validation = {"errors": [], "warnings": ["原有诊断"], "metrics": {}}
        style_validation = {
            "ok": False,
            "errors": ["HTML/CSS 存在硬编码颜色"],
            "warnings": ["强调色引用占比偏高"],
            "metrics": {"hardcoded_colors": ["#fff"]},
        }

        merged = video_studio_bespoke_html._attach_style_validation_diagnostics(
            validation,
            style_validation,
        )

        self.assertEqual(merged["errors"], [])
        self.assertTrue(merged["ok"])
        self.assertIn("视觉风格诊断：HTML/CSS 存在硬编码颜色", merged["warnings"])
        self.assertIn("强调色引用占比偏高", merged["warnings"])
        self.assertIs(merged["style_profile"], style_validation)

    def test_lifecycle_requires_one_renderable_capture_only(self) -> None:
        runner = (
            NPM_ROOT / "packages" / "smartvideo" / "bin" / "smartvideo-runtime.sh"
        ).read_text(encoding="utf-8")
        capture = runner.split("capture_html_asset() {", 1)[1].split("\n}\n\napprove_html_asset()", 1)[0]
        approve = runner.split("approve_html_asset() {", 1)[1].split("\n}\n\nbuild_effective_planning_file()", 1)[0]

        self.assertNotIn("outside the lightweight MG active_window", capture)
        self.assertNotIn("three visually distinct", approve)
        self.assertNotIn("alpha_min", approve)
        self.assertNotIn("alpha_max", approve)
        self.assertIn("at least one non-transparent keyframe", approve)
        self.assertIn("alpha_coverage_percent", approve)

    def test_broll_html_plan_requires_a_renderable_html_shot(self) -> None:
        with self.assertRaisesRegex(
            video_studio_planner.VideoStudioGenerationError,
            "requires at least one renderable HTML/MG shot",
        ):
            video_studio_planner.validate_planning_media_contract(
                [{"id": "group-01", "shots": [{"id": "shot-01", "scene_role": "full_broll"}]}],
                "broll_html",
            )

    def test_broll_plan_does_not_require_html(self) -> None:
        video_studio_planner.validate_planning_media_contract(
            [{"id": "group-01", "shots": [{"id": "shot-01", "scene_role": "full_broll"}]}],
            "broll",
        )

    def test_broll_html_plan_accepts_an_enabled_html_shot(self) -> None:
        video_studio_planner.validate_planning_media_contract(
            [{
                "id": "group-01",
                "shots": [{
                    "id": "shot-01",
                    "scene_role": "broll_backdrop_overlay",
                    "information_layer": {"enabled": True},
                    "mg_director": {"version": "semantic_mg_director", "enabled": True},
                }],
            }],
            "broll_html",
        )


if __name__ == "__main__":
    unittest.main()
