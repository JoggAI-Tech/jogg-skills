# HTML/MG Contract

Source: Podcastor Video Studio planner, PPT visual assets, and MG design services at commit `1d154ee8b5f9c3198018c1cb410295b0164db346`.

HTML/MG is a self-contained 1920x1080 documentary composition. It may be composited with B-roll, but it must not depend on a B-roll aperture or another external media track to complete its visual meaning. It is not a webpage, dashboard, card grid, split-screen SaaS layout, or copied slide deck.

## Semantic Source

`mg_director` is the only semantic and visual director. It has already selected `visual_recipe`, `composition`, and the central metaphor. The HTML layer executes that exact contract and must not choose another PPT grammar, template, layout, or competing main structure. The render contract controls canvas, safe areas, selectors, and output shape; it must not add facts. `visual_fx` controls only atmosphere such as grain, scan, particles, ink, or localized glow.

Each overlay has:

- one visual system;
- one learning point;
- one central visual metaphor;
- no more than three short visible text blocks;
- an entrance/build/lock timeline tied to shot seconds.

Before authoring HTML, read [mg-director-visual-contract.md](mg-director-visual-contract.md). Implement its selected IDs and the normalized `composition.animation_type`, `layout`, `hero_frame`, `typography`, `visual_primitives`, `icon_semantics`, and `motion_choreography` literally. Do not reselect from the catalog at this stage.

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
- Allow transparent treatment or a 45%-70% solid editorial field when required by the selected material. The complete composition must still read correctly without B-roll.

## Content And Motion

- Visible text comes from `screen_slots`, not from production instructions.
- Use HTML/CSS/SVG for diagrams and labels.
- Draw the main relationship inside `hero_frame` with large semantic objects, broad paths, contrast fields, or evidence surfaces. Thin lines, grids, particles, and scan effects are supporting texture only.
- Build timelines synchronously and deterministically.
- Use short entrance, build, and conclusion-lock phases.
- Do not use external scripts, external fonts, iframes, `@import`, HTTP assets, random values, or infinite animation.
- Text must fit its allocated rectangle at 1920x1080.

The local renderer sanitizes scripts, iframes, event handlers, remote `src`/`href`, CSS imports, and remote CSS URLs before rendering.
