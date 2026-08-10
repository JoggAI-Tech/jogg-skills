# Legacy HTML Authoring

This is the imported-legacy authoring and approval workflow for information-layer HTML. It
starts at `waiting_html` and ends at HTML approval. It does not alter TTS,
Avatar, B-roll acquisition, subtitles, or video rendering.

## Checkpoint Boundary

The initial plan contains scripts, shot strategies, stable clip bindings, and
semantic directors, but no generated `custom_html` or `custom_css`. `run` returns
`waiting_html` with `pending_clip_ids` before project creation or paid media
submission.

For each pending clip, read only:

```text
html_clip_checkpoints[clip_id].authoring_context
```

Do not supplement it with another template, deprecated visual document, or
project-specific style guide.

## Authority

Use constraints in this order:

1. The current clip's `authoring_context`.
2. This output, safety, and checkpoint contract.
3. General implementation knowledge.

The context has fixed meaning, composition, reference, timing, background, and
layer order. Only `screen_slots` and bound information objects authorize visible
copy. Never copy sample words, names, values, dates, sources, or facts.

For a strict reference, use each target's `semantic_role` and `semantic_group`
before assigning copy. Map headline to headline, entities/examples to diagram
labels, metrics to value/label pairs, and questions or evidence to supporting
surfaces. One authorized slot may be split into a short label and value, but do
not repeat one claim across unrelated targets merely to fill the template. Keep
intentional repetitions only when the same semantic object appears more than
once in the reference composition.

## Asset Shape

For `authoring_mode: strong_reference_patch_v1`, submit:

```json
{
  "version": "strong_reference_patch_v1",
  "reference_html_sha256": "checksum from context",
  "text_replacements": {"text-001": "authorized copy"},
  "attribute_replacements": {"attr-001": "authorized description"},
  "hidden_semantic_units": ["timeline-step-4"],
  "css_override": "",
  "layout_summary": "Preserve the selected composition."
}
```

Replacement objects cover every visible target in the compact contract. A
target may be omitted only when it belongs to an optional semantic unit listed
in `hidden_semantic_units`. Keep `css_override` empty for text fit; local
Chromium performs wrap-and-shrink after materialization. The runtime rejects
model-authored hiding CSS, remote assets, and selectors outside the reference.

For `visual_recompose`, submit one complete local asset:

```json
{
  "custom_html": "<main class=\"ai-mg-layer\" data-ai-generated-html=\"true\"><div class=\"mg-backdrop\"></div><div class=\"mg-content\">...</div></main>",
  "custom_css": ".ai-mg-layer{position:absolute;inset:0}.mg-backdrop{position:absolute;inset:0}.mg-content{position:relative}",
  "layout_summary": "one sentence",
  "edit_schema": {"version": "edit_schema_v2", "editable_blocks": []}
}
```

This adaptive fallback is automatic and does not require user confirmation.
When `fallback_automatic` is true, keep the selected reference's visual language
and do not expect or invent a free-generation style prompt. Only an explicit
`free_generation_selected:true` path may read the single
`free_generation_style.prompt` from the current authoring context. Never infer
that selection from a missing field or a failed template. Compile visible copy
from `story_contract`,
`information_object_plan`, `screen_slots`, reading order, and segment timing. Do
not place raw narration on screen and do not load another style reference.

Use local HTML/CSS and inline SVG only. Include one generated root and sibling
backdrop/content layers. Never set opacity on the root. Apply the background
rule only to `.mg-backdrop`; content remains fully opaque. Preserve the existing
composition profiles: `html_only` uses `0.95-0.99` with `0.99` as default,
`avatar_html` uses `0.95-0.99` only on information backplates while the remaining
area stays transparent, and `broll_html` uses `0.20-0.55` with `0.35` as default.
No composited background may use `1`, `1.0`, or `100%`. Do not use scripts,
iframes, media elements, forms, handlers, external assets, `@import`, network
URLs, random timing, or infinite animation.

Preserve the selected composition's primary visual, component relationships,
hierarchy, and motion character when the fallback is `visual_recompose`. The
single English style prompt refines finish but does not authorize a new theme or
sample content. Use finite deterministic motion: establish the hero, reveal in
reading order, lock the conclusion, and hold. Do not add generic card arrays,
fixed page zones, unrelated palettes, or decorative loops.

Expose stable `data-ai-edit-block` markers only for meaningful editable objects.
Selectors must be unique and simple. Do not expose nested child blocks under an
editable group.

## Generate And Inspect

For each `pending_clip_id`:

1. Read the current context and verify template ID, ratio, hash, reference mode,
   and any template-change reason.
2. Author only from authorized objects and reading order.
3. Use `apply-html`, or [legacy-echarts-authoring.md](legacy-echarts-authoring.md) plus
   `apply-echarts` for a validated chart spec.
4. Stop on `qa_failed`, read the checkpoint error, and repair only that asset.
5. Capture the strict reference at `frame_qa.recommended_at_seconds`. Inspect
   entry/build/hold frames for an adaptive recompose when layout or motion changed.
6. Inspect the PNG for primary visual, readable copy, clipping, overlap, blank
   regions, placeholders, and motion progression.
7. Reapply when needed; this clears only that clip's old captures.
8. Use `approve-html` only after a non-empty, non-transparent capture exists.

Preserve approved clips. A changed planning fingerprint resets affected
checkpoints; normal resume does not regenerate approved assets.

## Validation Boundary

After planning, only these failures block a clip:

- missing or empty HTML after normalization;
- unsafe or malformed HTML/CSS, remote/script risk, or missing generated root;
- renderer failure, missing/empty PNG, blank capture, or no visible alpha;
- missing approval for a required clip.

Copy, composition, style, fit, edit schema, alpha amount, capture timing, and
motion findings remain warnings for inspection. The post-generation gate does
not repeat semantic or aesthetic planning.

## Resume

Checkpoint status is `pending`, `generated`, `qa_failed`, or `approved`. Calling
`resume` while clips remain pending returns `waiting_html` without paid work.
After every required clip is approved, call `resume` once to continue the saved
media, editor, and render lifecycle.
