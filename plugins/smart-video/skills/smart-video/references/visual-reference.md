# Visual Reference

This is the semantic-to-visual contract for new Smart Video HTML. The semantic
director decides what the scene means; the bundled reference catalog supplies
visual grammar. Internal schema identifiers are not user-facing modes.

## Planning Sequence

For each HTML segment:

1. Build one story contract from authorized narration and semantic payload.
2. Choose one scene ID by information shape.
3. Build the information-object plan and reading order.
4. Inspect only the three candidates mapped to that scene.
5. Select one candidate and record a content-specific reason.
6. Resolve one ratio-specific reference against content capacity.
7. Compile the complete `authoring_context` before authoring.

Use the plugin-root-relative catalog helper when discovery is needed:

```bash
python3 "<plugin-root>/skills/smart-video/scripts/find_mg_templates.py" search "timeline milestones" --limit 3 --json
```

Scene selection is semantic. Never select a scene because its color or sample
copy looks attractive. Reference sample copy and facts are never authorized
visible content.

## Reference Resolution

The local resolver returns one of three modes:

- `strong_reference`: preserve the complete reference composition, component
  relationships, hierarchy, SVG geometry, tokens, and motion. The author supplies
  authorized replacements through `strong_reference_patch_v1`; the runtime owns
  deterministic materialization.
- `visual_recompose`: automatically retain the closest reference's visual
  language, dominant components, and motion character while reflowing content
  after every candidate in the semantic scene exceeds capacity.
- `scene_reselected_reference`: replace a semantic mismatch with a stable
  candidate under the correct scene and disclose the original template, selected
  template, and reason.

Automatic fallback does not require user confirmation. It first tries every
candidate in the selected semantic scene, then uses `visual_recompose` when none
fits. Automatic `visual_recompose` stays anchored to that reference and does not
receive a free-generation style prompt. Free generation is a separate path used
only after the user explicitly selects it; runtime records that consent privately
as `free_generation_selected:true`. It is never entered because template
selection or capacity handling failed. Compile visible content from the shot's
story contract,
information-object plan, screen slots, reading order, and timing rather than
sending raw narration as layout copy.

## Authoring Context

After resolution, `authoring_context` is the only visual input. It contains:

- effective template ID, ratio, reference mode, hash, and local path;
- visual contract, `authoring_context.composition`, prompt, and `screen_slots`;
- story contract, information-object plan, timing, layer order, and background
  rule;
- compact `strong_reference_patch_v1` contract for strict references;
- template-switch audit fields and single-frame QA recommendation.

Full `reference_html` and semantic adaptation records remain private run state.
Do not publish them through status responses, frontend state, stdout, or stderr.
`apply-html` loads the trusted local source and materializes the compact patch.

Do not reselect scene, template, palette, typography, composition, or motion after
the context is compiled. Do not add a generic card grid, page zones, unrelated
slide layout, or a second visual reference. In strict mode, project-wide style
metadata cannot override reference tokens or visual language.

## Capacity And Text Fit

The capacity resolver uses object count, relations, screen-copy length, duration,
and ratio. It keeps the selected strict reference when it fits, otherwise checks
the other candidates owned by the same semantic scene. Strict references may
hide only complete optional semantic units declared by the trusted catalog.
When no strict candidate fits, routing switches automatically to
`visual_recompose`; capacity is not diagnostic-only and no user confirmation is
requested.

Local Chromium measures the materialized copy. Wrap before shrinking and change
only measured targets. Do not truncate, hide overflow, or invoke another model.

## Background

For `broll_html`, keep the evidence footage recognizable and apply the resolved
opacity only to the full-canvas backdrop. For `avatar_html` and `html_only`, use
an effectively opaque backdrop. Never apply backdrop opacity to content, the
generated root, or the whole canvas.

## ECharts

ECharts is an implementation mode inside the selected scene. Use it only when
the chosen reference supports it and a deterministic chart expresses authorized
information faithfully. Continue with [echarts-authoring.md](echarts-authoring.md).
ECharts does not create a parallel planner or visual style system.
