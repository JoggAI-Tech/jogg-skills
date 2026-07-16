# HTML/MG Contract

Source: Podcastor Video Studio planner and MG design services at commit `57317cb688139c5336d51126fe624cb984b65d28`.

HTML/MG is a transparent documentary information layer over real B-roll. It is not a webpage, dashboard, card grid, split-screen SaaS layout, or slide deck.

## Semantic Source

`mg_director` is the only semantic director. The render contract controls canvas, safe areas, selectors, and output shape; it must not add facts. `visual_fx` controls only atmosphere such as grain, scan, particles, ink, or localized glow.

Each overlay has:

- one visual system;
- one learning point;
- one central visual metaphor;
- no more than three short visible text blocks;
- an entrance/build/lock timeline tied to shot seconds.

## Output Shape

Store generated content in the shot's `html_design` or an editor override:

```json
{
  "custom_html": "<div class=\"metric\">...</div>",
  "custom_css": ".metric { ... }",
  "layout_summary": "",
  "edit_schema": {},
  "render_strategy": "llm_bespoke_html"
}
```

Editor overrides use:

```json
{
  "html_design_overrides": {
    "shot-01": {
      "scene_design_spec": {
        "custom_html": "...",
        "custom_css": "..."
      }
    }
  }
}
```

## Canvas And Safety

- Fixed render canvas: 1920x1080, landscape 16:9.
- Use percentage, `vw`, `vh`, `vmin`, or `clamp()` for responsive placement inside the preview iframe.
- Keep the bottom caption zone clear.
- Keep only the small configured avatar rectangle and 16-24px buffer clear; do not reserve the whole right side.
- The overlay may use the full remaining frame and should not collapse into the upper-left corner.
- Prefer transparent and semi-transparent layers; do not cover B-roll with a large opaque block.

## Content And Motion

- Visible text comes from `screen_slots`, not from production instructions.
- Use HTML/CSS/SVG for diagrams and labels.
- Build timelines synchronously and deterministically.
- Use short entrance, build, and conclusion-lock phases.
- Do not use external scripts, external fonts, iframes, `@import`, HTTP assets, random values, or infinite animation.
- Text must fit its allocated rectangle at 1920x1080.

The local renderer sanitizes scripts, iframes, event handlers, remote `src`/`href`, CSS imports, and remote CSS URLs before rendering.
