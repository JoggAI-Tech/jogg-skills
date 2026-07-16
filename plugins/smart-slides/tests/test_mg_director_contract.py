#!/usr/bin/env python3
from __future__ import annotations

import unittest

from backend.services import video_studio_planner
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
