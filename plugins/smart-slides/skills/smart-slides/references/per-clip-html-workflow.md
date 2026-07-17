# Per-Clip HTML Workflow

Use this workflow after the director-only planning JSON is complete. Keep planning, HTML production, visual QA, and paid Jogg generation as separate checkpoints. Use only the bundled Podcastor-derived validator, local Chrome, and local FFmpeg; do not invoke HyperFrames or another renderer.

## Planning Boundary

In the initial planning JSON, include scripts, shots, B-roll intent, full `mg_director`, and stable clip bindings. For every bespoke information-layer shot:

```json
{
  "id": "shot-01",
  "scene_role": "broll_backdrop_overlay",
  "information_layer": {"enabled": true},
  "html_render_strategy": "llm_bespoke_html",
  "html_design": {"clip_id": "mg:capital-flow"},
  "mg_director": {
    "version": "mg_director_v1",
    "enabled": true,
    "render_strategy": "llm_bespoke_html",
    "screen_slots": [],
    "visual_recipe": {},
    "composition": {},
    "visual_fx": {}
  }
}
```

Use the same `html_design.clip_id` for shots sharing one continuous MG clip. Do not include `custom_html` or `custom_css` in the initial planning file. `run` must return `waiting_html` and `pending_clip_ids` before project creation, Jogg submission, B-roll download, preview, or final render.

## Asset Shape

Author one local JSON file per clip:

```json
{
  "custom_html": "<main class=\"ai-mg-layer\" data-ai-generated-html=\"true\">...</main>",
  "custom_css": ".ai-mg-layer{position:absolute;inset:0}",
  "layout_summary": "one sentence",
  "edit_schema": {
    "version": "edit_schema_v2",
    "editable_blocks": []
  }
}
```

For a multi-shot clip that needs different authored fragments, use `html_design_by_shot`. Otherwise the runner applies the single design to all bound shots. Keep the asset file outside run state: state stores only IDs, status, attempts, and local asset/keyframe paths.

## Generate And Inspect

For each ID returned in `pending_clip_ids`:

1. Read that clip's exact `mg_director`, `screen_slots`, shot durations, and [html-mg-contract.md](html-mg-contract.md). Do not select another visual grammar.
2. Author one asset JSON. Make `visual_fx` visibly present but subordinate in at least one sampled frame when its `fx_pack_id` is not `none`.
3. Apply it:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" apply-html \
  --run-id "ss-..." --clip-id "mg:capital-flow" \
  --html-file "/absolute/path/to/mg-capital-flow.json"
```

4. Stop on `qa_failed`. Read the checkpoint error, repair only this asset, and apply it again. Do not approve an asset that failed sanitizer, contract, canvas-fit, semantic edit-schema, or composition checks.
5. Capture at least entry, build, and hold frames at content-relevant seconds:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" capture-html --run-id "ss-..." --clip-id "mg:capital-flow" --at-seconds 0.2
bash "<plugin-root>/scripts/smart-slides.sh" capture-html --run-id "ss-..." --clip-id "mg:capital-flow" --at-seconds 1.8
bash "<plugin-root>/scripts/smart-slides.sh" capture-html --run-id "ss-..." --clip-id "mg:capital-flow" --at-seconds 4.8
```

6. Inspect every returned PNG. Require a clear primary visual, readable text, visible progression between entry/build/hold, correct transparency over B-roll, and no clipping, overlap, empty region, placeholder, or generic card grid. An unchanged frame sequence is a failure even when the HTML is valid.
7. Reapply a repaired asset when any frame fails. Reapply clears the old keyframes and increments `attempt`.
8. Approve only after inspection:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" approve-html \
  --run-id "ss-..." --clip-id "mg:capital-flow"
```

`approve-html` requires a locally validated asset and at least one non-empty captured keyframe. Codex must still inspect entry/build/hold; the CLI cannot make the aesthetic judgment.

## Resume Rules

Use `html-status` to retrieve checkpoints. Status values are:

- `pending`: no validated asset exists.
- `generated`: the asset passed structural validation but still needs visual inspection and approval.
- `qa_failed`: generation, capture, or visual QA failed; repair only this clip.
- `approved`: preserve the asset and keyframes; never regenerate it during resume.

Call `resume` while clips remain pending only to confirm the checkpoint; it must return `waiting_html` without starting paid work. After every required clip is `approved`, call `resume` once. The runner injects approved assets into a temporary planning payload, creates the local project, then proceeds to Jogg, B-roll, preview, and local rendering.

A changed planning file resets HTML checkpoints because clip contracts may have changed. A normal resume with the same planning file preserves approved assets and does not recreate Jogg or render jobs.

## Blocking QA

Treat these as render-blocking:

- missing `edit_schema_v2` for newly authored assets;
- missing or ambiguous semantic selectors;
- missing primary visual or screen-slot text copied from outside the director contract;
- unsafe HTML/CSS or remote assets;
- empty transparent output;
- unchanged entry/build/hold frames when motion is required;
- invisible requested `visual_fx`;
- any required clip not approved.

Treat minor stylistic alternatives as warnings only. Never replace a failed bespoke clip with a template unless the operator explicitly selects template recovery.
