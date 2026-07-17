#!/usr/bin/env python3
from __future__ import annotations

import unittest

from backend.services import video_studio_planner
from backend.services import video_studio_bespoke_html
from backend.services.video_studio_ppt_visual_assets import (
    PPT_VISUAL_LANGUAGE,
    ppt_visual_contract_art_direction,
    ppt_visual_language_catalog_prompt,
)


class PptVisualLanguageTest(unittest.TestCase):
    def test_catalog_is_composable_grammar_not_fixed_ppt_templates(self) -> None:
        self.assertEqual(len(PPT_VISUAL_LANGUAGE["compositions"]), 12)
        self.assertEqual(len(PPT_VISUAL_LANGUAGE["hero_devices"]), 10)
        self.assertEqual(len(PPT_VISUAL_LANGUAGE["materials"]), 8)
        self.assertEqual(len(PPT_VISUAL_LANGUAGE["motion_rhythms"]), 8)
        self.assertNotIn("broll_relations", PPT_VISUAL_LANGUAGE)

        catalog = ppt_visual_language_catalog_prompt()
        self.assertIn("视觉语法库，不是 PPT 模板库", catalog)
        self.assertIn("不得照抄任何单页 PPT", catalog)
        self.assertIn("originality_note", catalog)

    def test_html_art_direction_executes_only_the_director_selection(self) -> None:
        direction = ppt_visual_contract_art_direction(
            {
                "composition_id": "causal_spine",
                "hero_device_id": "semantic_icon_cluster",
                "material_id": "editorial_color_field",
                "motion_id": "directional_build_lock",
                "originality_note": "把资本传导原创为一条折返的巨型路径。",
            }
        )

        self.assertIn("MG_VISUAL_RECIPE_CONTRACT", direction)
        self.assertIn("composition_id: causal_spine", direction)
        self.assertIn("hero_device_id: semantic_icon_cluster", direction)
        self.assertIn("把资本传导原创为一条折返的巨型路径", direction)
        self.assertNotIn("comparison_stage", direction)
        self.assertIn("HTML 层只执行", direction)


class MgDirectorNormalizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recipe = {
            "composition_id": "causal_spine",
            "hero_device_id": "semantic_icon_cluster",
            "material_id": "luminous_data",
            "motion_id": "directional_build_lock",
            "originality_note": "把公司、芯片和资本原创为向核心收紧的折返路径。",
        }
        self.composition = {
            "animation_type": "self_contained_html",
            "layout": "directional_path",
            "hero_frame": {
                "kind": "资本流向图标路径",
                "x": 100,
                "y": 150,
                "w": 1320,
                "h": 620,
            },
            "typography": {
                "headline_scale": "display",
                "headline_min_px": 72,
                "supporting_min_px": 30,
            },
            "visual_primitives": ["icon", "path", "node"],
            "icon_semantics": ["云计算", "芯片", "资金"],
            "motion_choreography": "图标沿资本路径依次点亮，最后锁定资金集中。",
        }

    def _mg_director(self) -> dict:
        return {
            "version": "mg_director_v1",
            "enabled": True,
            "render_strategy": "llm_bespoke_html",
            "visual_system": "causal",
            "story_goal": "解释资本向算力基础设施集中。",
            "one_learning_point": "资本正在从应用层转向基础设施。",
            "main_visual_metaphor": "资本沿芯片和云计算路径向核心收紧。",
            "visual_recipe": self.recipe,
            "composition": self.composition,
            "screen_slots": [
                {"role": "headline", "text": "资本流向"},
                {"role": "takeaway", "text": "基础设施成为重心"},
            ],
        }

    def test_creative_plan_preserves_director_visual_recipe_and_composition(self) -> None:
        plan = video_studio_planner.normalize_creative_plan(
            {
                "script": "资本正在从应用层流向芯片和云计算基础设施。",
                "scenes": [
                    {
                        "id": "scene-01",
                        "title": "资本流向",
                        "scene_type": "视频素材 + HTML信息层",
                        "voiceover_units": [
                            {
                                "id": "script-01",
                                "text": "资本正在从应用层流向芯片和云计算基础设施。",
                                "duration_seconds": 8,
                            }
                        ],
                        "mg_director": self._mg_director(),
                    }
                ],
            },
            "AI 科技热点",
            None,
            {"production_format": "broll_html"},
        )

        director = plan["scenes"][0]["mg_director"]
        self.assertEqual(director["visual_recipe"], self.recipe)
        self.assertEqual(director["composition"]["layout"], "directional_path")
        self.assertEqual(director["composition"]["typography"], self.composition["typography"])
        self.assertEqual(director["composition"]["visual_primitives"], ["icon", "path", "node"])
        self.assertEqual(director["composition"]["motion_choreography"], self.composition["motion_choreography"])
        self.assertGreaterEqual(director["composition"]["hero_frame"]["coverage_percent"], 52)

    def test_storyboard_preserves_the_same_director_contract_for_html(self) -> None:
        groups = video_studio_planner.normalize_scene_groups(
            [
                {
                    "title": "资本流向",
                    "shots": [
                        {
                            "title": "基础设施重估",
                            "narration": "资本正在从应用层流向芯片和云计算基础设施。",
                            "duration_seconds": 8,
                            "broll_prompt": "AI data center infrastructure",
                            "scene_role": "broll_backdrop_overlay",
                            "mg_director": self._mg_director(),
                        }
                    ],
                    "html_layers": [{"title": "资本流向", "shot_indexes": [1]}],
                }
            ],
            "broll_html",
        )

        director = groups[0]["shots"][0]["mg_director"]
        self.assertEqual(director["visual_recipe"], self.recipe)
        self.assertEqual(director["composition"]["hero_frame"]["kind"], "资本流向图标路径")
        self.assertEqual(director["composition"]["typography"], self.composition["typography"])
        self.assertEqual(director["composition"]["icon_semantics"], ["云计算", "芯片", "资金"])


class BespokeHtmlContractTest(unittest.TestCase):
    def _director(self) -> dict:
        return {
            "version": "mg_director_v1",
            "enabled": True,
            "render_strategy": "llm_bespoke_html",
            "visual_system": "causal",
            "story_goal": "说明资本从应用层转向基础设施。",
            "one_learning_point": "资本正在向算力基础设施集中。",
            "main_visual_metaphor": "资本沿芯片和云计算路径向核心收紧。",
            "visual_recipe": {
                "composition_id": "causal_spine",
                "hero_device_id": "semantic_icon_cluster",
                "material_id": "luminous_data",
                "motion_id": "directional_build_lock",
                "originality_note": "把公司、芯片和资本原创为向核心收紧的折返路径。",
            },
            "composition": {
                "animation_type": "self_contained_html",
                "layout": "directional_path",
                "hero_frame": {"kind": "资本路径", "x": 100, "y": 150, "w": 1320, "h": 620},
                "typography": {"headline_scale": "display", "headline_min_px": 72, "supporting_min_px": 30},
                "visual_primitives": ["path", "node", "icon"],
                "icon_semantics": ["云计算", "芯片", "资金"],
                "motion_choreography": "路径先出现，节点依次点亮，最后锁定基础设施。",
            },
            "screen_slots": [
                {"role": "headline", "text": "资本流向"},
                {"role": "takeaway", "text": "基础设施成为重心"},
            ],
        }

    def _source_groups(self, custom_html: str) -> list[dict]:
        return [{
            "title": "资本流向",
            "shots": [{
                "id": "shot-bespoke",
                "title": "基础设施重估",
                "narration": "资本正在从应用层流向芯片和云计算基础设施。",
                "duration_seconds": 8,
                "broll_prompt": "AI data center infrastructure",
                "scene_role": "broll_backdrop_overlay",
                "mg_director": self._director(),
                "html_design": {
                    "custom_html": custom_html,
                    "custom_css": ".ai-mg-layer{position:absolute;inset:0;color:#fff}.title{font-size:64px}",
                    "edit_schema": {"editable_text_selectors": [".title"]},
                },
            }],
            "html_layers": [{"title": "资本流向", "shot_indexes": [1]}],
        }]

    def _groups(self, custom_html: str) -> list[dict]:
        source = self._source_groups(custom_html)
        normalized = video_studio_planner.normalize_scene_groups(source, "broll_html")
        return video_studio_bespoke_html.restore_bespoke_html_from_planning_input(source, normalized)

    def test_css_minifier_preserves_calc_operator_whitespace(self) -> None:
        css = (
            ".scene + .scene { animation-delay: calc(19.54s + var(--shot-offset)); "
            "width: calc(var(--frame-width) - 24px); }"
        )
        minified = video_studio_planner._minify_custom_css(css)

        self.assertIn("calc(19.54s + var(--shot-offset))", minified)
        self.assertIn("calc(var(--frame-width) - 24px)", minified)
        self.assertIn(".scene + .scene", minified)

    def test_codex_html_uses_the_extracted_source_contract_not_a_template(self) -> None:
        html = (
            '<main class="ai-mg-layer" data-ai-generated-html="true"><svg viewBox="0 0 1920 1080">'
            '<path data-ai-edit-block="capital-path" data-ai-edit-kind="visual" d="M180 520 L880 280 L1440 620" stroke="#a3e635" stroke-width="28" fill="none"/>'
            '<g data-ai-edit-block="icon-chip" data-ai-edit-kind="visual"><rect x="700" y="180" width="180" height="180" fill="#67e8f9"/></g>'
            '<g data-ai-edit-block="icon-cloud" data-ai-edit-kind="visual"><circle cx="1360" cy="620" r="90" fill="#a3e635"/></g>'
            '<text class="title" x="140" y="120" font-size="72">资本流向</text>'
            '<text x="140" y="780" font-size="36">基础设施成为重心</text></svg></main>'
        )
        groups = video_studio_bespoke_html.prepare_bespoke_html_scene_groups("AI 科技热点", self._groups(html))
        design = groups[0]["shots"][0]["html_design"]
        self.assertEqual(design["render_strategy"], "llm_bespoke_html")
        self.assertEqual(design["ai_html_generation"]["source"], "codex_local_bespoke_html")
        self.assertEqual(design["ai_html_generation"]["validation"]["version"], "bespoke_html_validation_v2")
        self.assertIn("position:absolute!important", design["custom_css"])
        self.assertIn("data-ai-generated-html=\"true\"", design["custom_html"])
        preview = video_studio_planner.build_composition_preview_html({"topic": "AI 科技热点", "scene_groups": groups, "editor_state": {}})
        self.assertIn("custom-html-frame", preview)
        self.assertNotIn("MG视觉系统", preview)

    def test_bespoke_html_inherits_source_template_transparent_surfaces(self) -> None:
        html = (
            '<main class="ai-mg-layer" data-ai-generated-html="true"><svg viewBox="0 0 1920 1080">'
            '<rect x="72" y="84" width="1776" height="820" rx="28" fill="#07111f" fill-opacity=".8"/>'
            '<rect x="0" y="0" width="960" height="1080" fill="#0c2840" fill-opacity=".86"/>'
            '<path data-ai-edit-block="capital-path" data-ai-edit-kind="visual" d="M180 520 L880 280 L1440 620" stroke="#a3e635" stroke-width="28" fill="none"/>'
            '<g data-ai-edit-block="icon-chip" data-ai-edit-kind="visual"><rect x="700" y="180" width="180" height="180" fill="#67e8f9"/></g>'
            '<g data-ai-edit-block="icon-cloud" data-ai-edit-kind="visual"><circle cx="1360" cy="620" r="90" fill="#a3e635"/></g>'
            '<text class="title" x="140" y="120" font-size="72">资本流向</text>'
            '<text x="140" y="780" font-size="36">基础设施成为重心</text></svg></main>'
        )
        design = video_studio_bespoke_html.prepare_bespoke_html_scene_groups("AI 科技热点", self._groups(html))[0]["shots"][0]["html_design"]
        self.assertIn('fill-opacity=".42"', design["custom_html"])
        self.assertIn('fill-opacity=".38"', design["custom_html"])
        self.assertIn('data-mg-surface="source-translucent"', design["custom_html"])
        self.assertIn("--mg-surface: rgba(2,6,23,.34)", design["custom_css"])

    def test_missing_bespoke_html_is_a_blocking_contract_failure(self) -> None:
        with self.assertRaises(video_studio_bespoke_html.BespokeHtmlContractError):
            video_studio_bespoke_html.prepare_bespoke_html_scene_groups("AI 科技热点", self._groups(""))

    def test_source_bespoke_prompt_is_extracted_for_codex_authoring(self) -> None:
        groups = self._groups('<main class="ai-mg-layer" data-ai-generated-html="true"></main>')
        shot = groups[0]["shots"][0]
        prompt = video_studio_planner._bespoke_html_asset_prompt(
            "AI 科技热点", video_studio_planner._mg_clip_for_shot(shot), [shot]
        )
        self.assertIn("MG 构图执行合同", prompt)
        self.assertIn("AIGC 主路径", prompt)
        self.assertIn("模板只允许作为失败兜底", prompt)

    def test_semantic_edit_schema_marks_only_declared_blocks(self) -> None:
        custom_html = (
            '<main class="ai-mg-layer" data-ai-generated-html="true">'
            '<svg viewBox="0 0 1920 1080">'
            '<g class="hero"><path data-ai-edit-block="legacy-path" d="M0 0L100 100"/></g>'
            '<text class="headline">标题</text>'
            '</svg></main>'
        )
        normalized_html, normalized_schema = video_studio_bespoke_html.normalize_edit_schema(
            custom_html,
            {
                "editable_blocks": [
                    {
                        "id": "headline",
                        "name": "主标题",
                        "kind": "text",
                        "selector": ".headline",
                        "allowed": ["text", "x", "fontSize"],
                    },
                    {
                        "id": "hero",
                        "name": "主视觉",
                        "kind": "group",
                        "selector": ".hero",
                        "allowed": ["x", "scale", "color"],
                        "colorMode": "descendants",
                    },
                ]
            },
        )

        self.assertIn('data-ai-edit-block="headline"', normalized_html)
        self.assertIn('data-ai-edit-block="hero"', normalized_html)
        self.assertNotIn('data-ai-edit-block="legacy-path"', normalized_html)
        self.assertEqual(normalized_schema["version"], "edit_schema_v2")
        self.assertEqual(normalized_schema["editable_blocks"][1]["colorMode"], "descendants")
        edited_html = video_studio_bespoke_html.apply_edit_text_overrides(
            normalized_html,
            normalized_schema,
            {"headline": {"text": "芯片 < 算力"}},
        )
        self.assertIn("芯片 &lt; 算力", edited_html)
        self.assertIn('<path d="M0 0L100 100"/>', edited_html)
        group_css = video_studio_bespoke_html.build_edit_override_css(
            normalized_schema,
            {"hero": {"color": "#22d3ee"}},
        )
        self.assertIn(".hero,.hero *", group_css)
        self.assertIn("fill:#22d3ee", group_css)

    def test_semantic_edit_schema_rejects_ambiguous_or_nested_blocks(self) -> None:
        duplicate_id = {
            "editable_blocks": [
                {"id": "same", "name": "一", "kind": "text", "selector": ".one", "allowed": ["text"]},
                {"id": "same", "name": "二", "kind": "text", "selector": ".two", "allowed": ["text"]},
            ]
        }
        with self.assertRaisesRegex(video_studio_bespoke_html.BespokeHtmlContractError, "重复"):
            video_studio_bespoke_html.normalize_edit_schema(
                '<main><span class="one">一</span><span class="two">二</span></main>',
                duplicate_id,
            )

        with self.assertRaisesRegex(video_studio_bespoke_html.BespokeHtmlContractError, "简单 selector"):
            video_studio_bespoke_html.normalize_edit_schema(
                '<main><g class="hero"><path class="line"/></g></main>',
                {"editable_blocks": [{"id": "line", "name": "线", "kind": "visual", "selector": ".hero .line", "allowed": ["color"]}]},
            )

        for custom_html in (
            '<main><span>没有标题</span></main>',
            '<main><span class="headline">一</span><span class="headline">二</span></main>',
        ):
            with self.assertRaisesRegex(video_studio_bespoke_html.BespokeHtmlContractError, "必须唯一命中"):
                video_studio_bespoke_html.normalize_edit_schema(
                    custom_html,
                    {"editable_blocks": [{"id": "headline", "name": "标题", "kind": "text", "selector": ".headline", "allowed": ["text"]}]},
                )

        with self.assertRaisesRegex(video_studio_bespoke_html.BespokeHtmlContractError, "子块"):
            video_studio_bespoke_html.normalize_edit_schema(
                '<main><g class="hero"><path class="line"/></g></main>',
                {
                    "editable_blocks": [
                        {"id": "hero", "name": "视觉组", "kind": "group", "selector": ".hero", "allowed": ["scale"]},
                        {"id": "line", "name": "子路径", "kind": "visual", "selector": ".line", "allowed": ["color"]},
                    ]
                },
            )

    def test_edit_override_css_is_sparse_and_scoped(self) -> None:
        schema = {
            "version": "edit_schema_v2",
            "editable_blocks": [
                {
                    "id": "headline",
                    "name": "主标题",
                    "kind": "text",
                    "selector": "[data-ai-edit-block='headline']",
                    "allowed": ["text", "x", "fontSize", "color"],
                }
            ],
        }
        css = video_studio_bespoke_html.build_edit_override_css(schema, {"headline": {"x": 120}})
        self.assertIn("[data-ai-edit-block='headline']", css)
        self.assertIn("--smart-slides-edit-x:120px", css)
        self.assertNotIn("color", css)
        self.assertNotIn("opacity", css)
        self.assertNotIn("animation", css)
        self.assertNotIn("width", css)
        self.assertNotIn("height", css)

        with self.assertRaisesRegex(video_studio_bespoke_html.BespokeHtmlContractError, "不允许编辑 opacity"):
            video_studio_bespoke_html.build_edit_override_css(schema, {"headline": {"opacity": 0.5}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
