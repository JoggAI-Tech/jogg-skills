# Video Studio Planning Contracts

Source: `backend/services/video_studio_planner.py` at Podcastor commit `1d154ee8b5f9c3198018c1cb410295b0164db346`.

Use these existing contracts when Codex prepares `--planning-file`. Keep the project topic literal and keep `target_duration_seconds` between 60 and 1800.

## Producer Analysis

`producer_analysis` contains:

- `input_assessment`: `input_type`, confidence, and a production summary.
- `topic_blocks[]`: title, description, and production value.
- `key_data_scenes[]`: label, value, and scene hint. Mark uncertain values `待核验`.
- `asset_availability`: local material check, open-asset keywords, and risks.
- at least the original A/B production options: `broll` and recommended `broll_html`.

This is not a script or storyboard. Its density must match the requested runtime.

## Production Requirement

`production_requirement_document` contains title, summary, background, production strategy, duration, reference style, and:

- `material_requirements`: types, recommended sources, preferences, timeliness, regions, and named entities.
- `html_mg_direction`: render strategy, template policy, palette, typography, icon style, and motion principles.
- `audio_avatar`: BGM, avatar, and voice-tone guidance.
- `ratio_plan`: B-roll, HTML/MG, and avatar proportions.
- `risk_notes`.

For `broll_html`, use `llm_bespoke_html` with `templates_as_fallback`, unless the user explicitly requests template-first output.

## Script Director And Script

`script_director` defines topic understanding, audience question, hook, ordered structure, tone, and writing notes. It must not contain final shots or asset instructions.

`script` is complete narration, not an outline. Write for spoken delivery with a restrained causal progression. Its length must match the target duration.

## Creative Plan

Split the script into scenes. Podcastor's existing density guidance is:

- 1-2 minutes: about 6-8 scenes.
- 3-5 minutes: about 8-14 scenes.
- more than 5 minutes: about 12-20 scenes.

Each scene must have non-empty `voiceover_units[]` with stable IDs, text, and duration. Mark a scene as `视频素材 + HTML信息层` only when its data, cause, time, comparison, route, or reveal benefits from an information layer.

For each scene, provide:

```json
{
  "asset_search_plan": {
    "summary": "single scene material intent",
    "search_queries": ["Tokyo cityscape 1980s"],
    "material_types": ["城市", "档案"],
    "named_entities": [],
    "duration_seconds": 8
  },
  "mg_director": {
    "version": "mg_director_v1",
    "enabled": true,
    "render_strategy": "llm_bespoke_html",
    "scope": "single_shot",
    "bound_voiceover_unit_ids": ["script-01"],
    "story_goal": "",
    "core_question": "",
    "one_learning_point": "",
    "visual_system": "causal",
    "main_visual_metaphor": "",
    "visual_recipe": {
      "composition_id": "causal_spine",
      "hero_device_id": "semantic_icon_cluster",
      "material_id": "editorial_color_field",
      "motion_id": "directional_build_lock",
      "originality_note": "content-specific original translation"
    },
    "composition": {
      "animation_type": "self_contained_html",
      "layout": "directional_path",
      "hero_frame": {"kind": "large semantic subject", "x": 72, "y": 96, "w": 1776, "h": 760},
      "typography": {"headline_scale": "display", "headline_min_px": 64, "supporting_min_px": 28},
      "visual_primitives": ["path", "node", "icon"],
      "icon_semantics": ["concept A", "concept B"],
      "motion_choreography": "establish the subject, build the relationship, lock the conclusion"
    },
    "visual_fx": {"fx_pack_id": "none", "intensity": "low", "opacity": 0.18, "usage": ""},
    "logic_chain": [],
    "supporting_metric": {},
    "screen_slots": [],
    "timeline": [],
    "html_brief": ""
  }
}
```

Search queries are for Pexels/Pixabay: one visible scene, 3-8 words, no narration sentences, no causal explanation, and distinct shot semantics. Adjacent shots must use different visible actions/subjects and cannot reuse a provider asset selected by another shot. Each candidate must cover the shot's `duration_seconds`; a short clip is not looped to fill narration time.

Use one visual system from `metric`, `causal`, `route`, `timeline`, `comparison`, or `reveal`; one main visual metaphor; one learning point; and no more than three visible text blocks. Select the PPT-derived `visual_recipe` and full-frame `composition` here in the MG director layer, following [mg-director-visual-contract.md](mg-director-visual-contract.md). `visual_fx` adds texture only and never carries meaning.

## Storyboard

`scene_groups[].shots[]` keeps the existing IDs and includes at least:

- `title`, `narration`, and `duration_seconds`.
- `broll_prompt` and `asset_search_plan`.
- `scene_role`: `broll_backdrop_overlay` or `full_broll`.
- `visual_role`, `information_layer`, and the exact director-selected `mg_director.visual_recipe` and `mg_director.composition`.
- `html_render_strategy` and `html_design` for information-layer shots.

The local API runs the extracted `normalize_scene_groups()` and `build_render_contract_package()` when `scene_groups` is patched. Do not manually fabricate `render_manifest`, `director_timeline`, or derived layers when the normalizer can produce them.
