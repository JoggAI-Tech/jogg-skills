# HTML Slide Authoring

Use this path for a Slide whose preserved render mode is `html_svg`.

## Checkpoint

Read the pending clip's complete `authoring_context`. A new Slide must have:

```text
authoring_mode: full_html_recompose_v1
fidelity: adaptive
reference_mode: visual_recompose
fallback_automatic: false
free_generation_selected: true
```

If the checkpoint is strict, stop and correct planning. Do not author a
`strong_reference_patch_v1` and do not use the reference HTML as visual input.
The semantic scene and template remain runtime locators only.

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
- Before writing CSS, copy the design's closed color-role budget of no more than
  five semantic color roles. Count every token used by the background, inherited
  text, borders, and SVG; use no color role outside that set. Reusing a token does
  not increase the role count.
- Use only `var(--mg-font-display)`, `var(--mg-font-body)`, or
  `var(--mg-font-mono)` for font families.
- Do not redefine `--mg-*` variables or hardcode colors.
- Unless the MASTER material explicitly permits glow, do not use `box-shadow`,
  `text-shadow`, or `drop-shadow`, including inset shadow used as a border. Use
  borders or nested geometry instead.
- Keep essential content inside the locked MASTER safe area: `64px` top/bottom
  and `96px` left/right for `1920x1080`; `96px` top/bottom and `54px` left/right
  for `1080x1920`.
- For `avatar_html`, keep essential information outside the shot's resolved
  Avatar region. Missing `avatar_placement` means default lower-right; a
  conversational user override replaces it. Treat avoidance as authoring
  guidance, not a hard post-authoring rejection gate.

## Safety

Use HTML, CSS, and optional inline SVG only. Do not include `html`, `head`, `body`,
`style`, `script`, canvas, iframe, form, media, external SVG, image, font import,
URL, event handler, interaction, or remote resource. Do not use inline style
attributes. Keep SVG self-contained and decorative SVG content semantically inert.
Do not use numeric HTML character references such as `&#8594;`; the runtime color
scanner treats their `#` prefix as a hardcoded color candidate. Draw symbols with
CSS or inline SVG geometry.

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

Put the source cue's exact ID in `data-cue-id` and the calculated value in
`data-delay-seconds` on every semantic cue group. These attributes are required
even when CSS selectors or animation delays already contain the same values.

Verify that the projected `mg_director.timeline` has exactly the same cue count,
order, targets, and calculated times, then use its `start_s` values as CSS delays.
Stop on a mismatch or missing timeline. Preserve cue order. A later
`visual_target` must not appear before its anchor.
Complete all transitions by `stable_hold_start_ratio * duration_seconds`, then
hold the complete final frame. Do not compress the full reading sequence into the
first seconds of a longer narration.

## Preflight And Repair

Before submission, apply the same color, structure, safety, and timeline checks as
the npm authoring gate. Do not submit a known failure and rely on npm to direct the
design.

Mechanically collect every `var(--mg-*)` color reference from `custom_html` and
`custom_css`. Confirm that its unique color-role set equals or is a subset of the
closed color-role budget and contains at most five roles.

Repair only the failed asset. Keep the locked MASTER, source meaning,
Communication Intent, Visual Intent, Art Direction, composition intent, and
semantic timeline unchanged. Do not return to directing, revise the whole-video
MASTER, or regenerate approved Slides. Do not enable a template or Free Style as a
repair path. Do not patch generated code with string replacement; author the
failed asset again from the preserved inputs and the reported violation.

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
