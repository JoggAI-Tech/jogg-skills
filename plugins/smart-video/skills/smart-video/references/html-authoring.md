# HTML Slide Authoring

Use this path for a Slide whose preserved render mode is `html_svg`.

## Checkpoint

Read the pending clip's complete `authoring_context`. A new Slide must have:

```text
authoring_mode: direct_slide_html_v1
fidelity: adaptive
reference_mode: visual_recompose
fallback_automatic: false
free_generation_selected: true
```

The checkpoint must not contain `template_id`, `reference_html`,
`reference_html_path`, `reference_html_sha256`, `contract`, `composition`, or
`prompt`. Stop and correct planning if any template-derived field is present.

## Asset

Submit one JSON object:

```json
{
  "custom_html": "<main class=\"ai-mg-layer\" data-ai-generated-html=\"true\"><div class=\"mg-backdrop\"></div><div class=\"mg-content\">...</div></main>",
  "custom_css": ".ai-mg-layer{position:absolute;inset:0}.mg-backdrop{position:absolute;inset:0}.mg-content{position:relative}",
  "layout_summary": "One source-bound sentence describing the composition",
  "edit_schema": {"version": "edit_schema_v2", "editable_blocks": []}
}
```

Use one `main.ai-mg-layer` root, one sibling `.mg-backdrop`, and one sibling
`.mg-content`. Keep all visible information inside `.mg-content`. Use stable
`data-ai-edit-block` markers only for meaningful editable objects.

## MASTER Application

- Read the locked MASTER before writing the asset.
- Execute the current shot's exact Art Direction embedded in the MASTER. Do not
  replace it with a named style, template, generic card layout, or new semantic
  interpretation.
- Use its visual hierarchy, material, spacing, and motion character.
- Use only `var(--mg-surface)`, `var(--mg-surface-recessed)`, `var(--mg-ink)`,
  `var(--mg-muted)`, `var(--mg-primary)`, `var(--mg-highlight)`,
  `var(--mg-danger)`, and `var(--mg-outline)` for colors.
- Use only `var(--mg-font-display)`, `var(--mg-font-body)`, or
  `var(--mg-font-mono)` for font families.
- Do not redefine `--mg-*` variables or hardcode colors.
- Use the locked MASTER safe area: for `16:9`, keep essential content at least
  `64px` from top/bottom and `96px` from left/right; for `9:16`, keep it at least
  `96px` from top/bottom and `54px` from left/right.
- For `avatar_html`, treat the final Avatar region as authoring guidance and keep
  essential information clear of it. Do not make this a hard post-authoring
  rejection gate.

## Safety

Use HTML, CSS, and optional inline SVG only. Do not include `html`, `head`, `body`,
`style`, `script`, canvas, iframe, form, media, external SVG, image, font import,
URL, event handler, interaction, or remote resource. Do not use inline style
attributes. Keep SVG self-contained and decorative SVG content semantically inert.

Visible copy and values come only from source-authorized screen content. Do not
copy sample words or facts from any reference. Do not put raw narration on screen.

Apply the current shot's backdrop opacity only to `.mg-backdrop`; keep content
fully opaque. Use finite CSS animation and end with a complete stable state. Never
use infinite animation or meaning that exists only during motion.

Author CSS timing from the Visual Intent's `semantic_timeline`. Bind every
animated semantic group to its exact `narration_anchor` and calculate:

```text
delay_seconds = start_ratio * duration_seconds
```

Verify that the projected `mg_director.timeline` has exactly the same cue count,
order, targets, and calculated times, then use its `start_s` values as CSS delays.
Stop on a mismatch or missing timeline. Preserve cue order. A later
`visual_target` must not appear before its anchor.
Complete all transitions by `stable_hold_start_ratio * duration_seconds`, then
hold the complete final frame. Do not compress the full reading sequence into the
first seconds of a longer narration.

## Submit And Inspect

```bash
bash "<plugin-root>/scripts/smart-video.sh" apply-html \
  --run-id "sv-..." \
  --clip-id "mg:shot-04" \
  --html-file "/absolute/path/to/slide.json"
```

Inspect the generated capture for visible content, hierarchy, clipping, overlap,
source fidelity, safe-area compliance, correct backdrop behavior, and a stable
final frame. Repair only that asset and resubmit. Preserve approved clips.
