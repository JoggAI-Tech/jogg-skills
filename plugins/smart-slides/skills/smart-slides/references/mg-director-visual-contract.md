# MG Director Visual Contract

Source: `backend/services/video_studio_ppt_visual_assets.py` and `backend/services/video_studio_planner.py` at Podcastor commit `1d154ee8b5f9c3198018c1cb410295b0164db346`.

Apply this contract while authoring `creative_plan.scenes[].mg_director` and storyboard `shots[].mg_director`. The MG director selects the visual grammar and spatial composition before HTML generation. The HTML layer executes this exact decision; it must not select another recipe or recreate a PPT page.

## Required Director Output

For every enabled `mg_director`, provide:

```json
{
  "visual_system": "causal",
  "main_visual_metaphor": "资本沿芯片和云计算路径向核心收紧",
  "visual_recipe": {
    "composition_id": "causal_spine",
    "hero_device_id": "semantic_icon_cluster",
    "material_id": "luminous_data",
    "motion_id": "directional_build_lock",
    "originality_note": "把公司、芯片和资本原创为向核心收紧的折返路径"
  },
  "composition": {
    "animation_type": "self_contained_html",
    "layout": "directional_path",
    "hero_frame": {"kind": "资本流向图标路径", "x": 72, "y": 96, "w": 1776, "h": 760},
    "typography": {"headline_scale": "display", "headline_min_px": 64, "supporting_min_px": 28},
    "visual_primitives": ["path", "node", "icon"],
    "icon_semantics": ["云计算", "芯片", "资金"],
    "motion_choreography": "先建立方向，再沿路径推进节点，最后锁定资金集中"
  }
}
```

`animation_type` and `content_mode` normalize to `self_contained_html`. `hero_frame` uses 1920x1080 coordinates and must occupy at least 52% of the frame after normalization. Use `layout` from `single_focus`, `asymmetric_split`, `editorial_timeline`, `directional_path`, `evidence_frame`, or `contrast_stage`.

## PPT-Derived Visual Grammar

This is a grammar library, not a template library. Select exactly one ID from each dimension and recombine it around the shot's meaning.

### Compositions

- `asymmetric_split`: asymmetric full-frame regions with an explicit hierarchy; no external-media window.
- `causal_spine`: a large central causal spine with a few uneven nodes and a dominant result.
- `editorial_timeline`: a timeline through the middle with an oversized turning point, never a thin footer line.
- `directional_route`: a broad directional route across the frame with only a few anchors.
- `comparison_stage`: two states of one object in a visible conflict using a cut, wipe, turn, or scale difference.
- `depth_reveal`: foreground/background, section, level, or mask reveals a hidden structure.
- `hero_metric`: one core number and one semantic graphic form the subject; evidence remains secondary.
- `evidence_orbit`: a core judgment with a few pieces of evidence on incomplete arcs.
- `document_focus`: an enlarged document or evidence crop with one decisive annotation.
- `layered_cascade`: stacked fields, steps, or falling structures express accumulation or transmission.
- `radial_convergence`: multiple sources converge on or radiate from one dominant center.
- `typographic_monument`: a keyword, number, or short conclusion becomes the oversized typographic subject.

### Hero Devices

- `semantic_icon_cluster`: two to four large recognizable SVG icons form one relationship, never an icon menu.
- `oversized_number`: a core number occupies major visual area and relates to a trend, ratio, or silhouette.
- `symbolic_silhouette`: a person, institution, factory, chip, country, or similar silhouette carries the abstraction.
- `wide_flow_band`: a broad directional color band carries flow or transmission; never use a hairline.
- `cropped_evidence`: an enlarged document, map, ticket, or chart fragment acts as the evidence subject.
- `before_after_object`: the same object shares coordinates or outline across two states.
- `scale_contrast`: extreme size, distance, or ratio expresses power, cost, scale, or imbalance.
- `stacked_layers`: a few large stacked planes express strata, debt, supply chain, or accumulation.
- `kinetic_wordmark`: one short word or conclusion becomes an object through cutting, compression, or expansion.
- `focus_frame`: a large finder, scan window, or focus ring targets an internally drawn evidence object.

### Materials

- `editorial_color_field`: high-contrast solid fields and hard cuts, like documentary packaging rather than cards.
- `archival_paper`: restrained paper, print, typewriter, and archive wear.
- `ink_wash`: ink diffusion, dry/wet edges, or mask reveal supporting the main structure.
- `cinematic_gradient`: a cinematic gradient with a clear light direction, never decorative gradient blobs.
- `satellite_scan`: satellite texture, scan bands, and geographic coordinates for map or environmental evidence.
- `technical_blueprint`: engineering linework, sections, and measurements supporting a large subject.
- `film_grain`: low-intensity film grain and exposure texture for historic or human evidence.
- `luminous_data`: restrained data glow and energy edges for technology, capital, or networks.

### Motion Rhythms

- `directional_build_lock`: establish direction, advance the subject along it, then lock the conclusion.
- `mask_reveal_focus`: reveal the subject with a large mask, then hold a focus frame on decisive evidence.
- `scale_punch_settle`: establish scale with a fast punch, settle, then introduce supporting information.
- `progressive_cascade`: advance nodes or layers in causal order and give the endpoint the greatest weight.
- `split_transform`: split one frame into two states and hold on the difference.
- `route_trace_arrival`: grow the primary route continuously, then reveal the conclusion on arrival.
- `evidence_accumulation`: introduce evidence one item at a time and converge around the core.
- `hold_then_disrupt`: establish a stable composition before one visible rupture, drop, or reversal.

## Selection Rules

- Choose the recipe from the narration's meaning, not from decorative preference.
- Let `composition_id` define the spatial skeleton and `hero_device_id` define the first-read subject. Do not substitute one for the other.
- Let `material_id` control finish only and `motion_id` control timing only.
- Explain the content-specific transformation in `originality_note`; do not restate the IDs.
- Make the HTML frame self-contained. Do not reserve an aperture, black box, transparent evidence window, or half-frame blank for B-roll or another track.
- Use one main visual structure. Do not combine a second comparison, path, timeline, causal chain, map, or metric as a competing composition.
- Use large semantic objects and relationships. Do not reduce the result to a dashboard, card grid, tiny labels, decorative dots, or thin lines.
