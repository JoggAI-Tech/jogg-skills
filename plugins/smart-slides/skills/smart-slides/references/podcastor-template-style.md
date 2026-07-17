# Podcastor Template Surface Style

Source: `backend/services/video_studio_planner.py`, the original Podcastor MG template and MG-director CSS around `_mg_template_css()` at commit `1d154ee8b5f9c3198018c1cb410295b0164db346`.

This reference supplies the finishing system for a director-selected bespoke HTML composition. It does not select composition, replace `mg_director`, or turn a frame into a template.

## Surface Tokens

The original template values below are a legacy fallback, not the current project palette. Current output takes colors, type, line weights, glow, and timing from [visual-style-profiles.md](visual-style-profiles.md). Map the original roles to `--mg-surface`, `--mg-surface-recessed`, `--mg-outline`, `--mg-ink`, `--mg-primary`, and `--mg-highlight`; do not copy the navy/cyan values into authored HTML.

The extracted fallback values were:

- Main localized surface: `rgba(2,6,23,.34)`.
- Recessed or texture surface: `rgba(2,6,23,.24)`.
- Fine outline: `rgba(255,255,255,.14)`; secondary outline: `rgba(255,255,255,.12)`.
- Text ink: `#F8FAFC`; the historical accent came from the visual system. Current accents come only from the project profile and remain within its accent budget.
- When a local text surface floats above B-roll, use `backdrop-filter: blur(10px)` plus the fine outline. Do not use it to build an unrelated card grid.

Legacy imports may convert inherited `#07111f` / `#020617` / `#0f172a` SVG rectangles to a translucent source-derived surface. Newly authored assets must use profile variables and cannot contain those literals. Preserve a genuinely opaque field only with `data-mg-opaque="true"` and an explicit compatible material.

## Original Patterns

Use only the pattern that the selected `visual_recipe` already calls for:

- `route`: broad route shadow, continuous accent trace, then endpoint labels.
- `timeline`: one center rail with progressively revealed steps, not a thin footer strip.
- `causal`: a small number of directional nodes, glow only on the active link or conclusion.
- `metric`: one oversized metric with one chart or measured comparison; evidence stays secondary.
- `comparison`: two aligned evidence lanes, one highlighted difference, no duplicate dashboard chrome.
- `document` or `evidence`: one enlarged surface with a focused highlight and restrained source label.

## Layering And Motion

The original template system introduces the visual skeleton first, then the headline/L1, then L2 in a stagger, and finally L3. A final hold keeps the conclusion readable. Use a single 450-550ms upward entrance for localized panels and labels; do not loop decorative animation or animate every element at once.

## Prohibited Treatments

- Full-frame 70-90% opaque dark mats when B-roll is intended to remain visible.
- Several unrelated translucent cards spread across empty space.
- Strong glow, gradients, or texture that compete with the director's hero object.
- Replacing bespoke SVG structure with the template's card markup.
