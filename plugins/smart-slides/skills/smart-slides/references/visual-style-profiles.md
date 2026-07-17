# Visual Style Profiles

Smart Slides uses one executable visual style profile per project. The MG director still selects the composition, hero device, material, and motion grammar. The profile controls how every clip looks: semantic colors, typography roles, line weights, accent budget, glow policy, and motion personality.

This is a style system, not a page-template library. Do not import website templates, copy a slide page, or add runtime packages/CDNs.

## Profile Selection

Select one ID in `production_requirement_document.html_mg_direction.visual_style_profile_id`:

| ID | Use for | Character | Default glow |
| --- | --- | --- | --- |
| `editorial_tech_news` | news, current affairs, AI/technology hotspots | charcoal editorial stage, serif/sans hierarchy, decisive warm signals | endpoint only |
| `technical_blueprint` | mechanisms, engineering, architecture, chips, scientific explanation | light drafting field, measured geometry, one engineering signal color | none |
| `archival_documentary` | history, biography, evidence, retrospectives | film-black field, paper ink, oxblood evidence marks, restrained grain | none |

An explicit user choice wins. Otherwise infer once from the project topic and keep it for every clip. Do not choose a different profile per scene.

When the user supplies a custom five-color palette, use this exact order:

```json
["surface", "ink", "primary", "highlight", "danger"]
```

The runtime accepts it only when `ink` on `surface` reaches WCAG AA 4.5:1. It derives `surface_recessed`, `muted`, and `outline`; do not invent extra colors.

## Semantic CSS Contract

The runtime injects these immutable variables:

```css
var(--mg-surface)
var(--mg-surface-recessed)
var(--mg-ink)
var(--mg-muted)
var(--mg-primary)
var(--mg-highlight)
var(--mg-danger)
var(--mg-outline)
var(--mg-font-display)
var(--mg-font-body)
var(--mg-font-mono)
var(--mg-line-hairline)
var(--mg-line-structural)
var(--mg-line-hero)
var(--mg-enter-ms)
var(--mg-stagger-ms)
var(--mg-settle-ms)
var(--mg-easing)
```

Use them directly in CSS and SVG attributes:

```html
<path stroke="var(--mg-primary)" fill="none" />
<text fill="var(--mg-ink)">关键结论</text>
```

```css
.headline { color: var(--mg-ink); font-family: var(--mg-font-display); }
.evidence { color: var(--mg-muted); border: var(--mg-line-hairline) solid var(--mg-outline); }
```

Authored HTML/CSS must not contain hex, RGB/HSL, named colors, custom font stacks, or redefinitions of core `--mg-*` tokens. Use no more than five semantic color roles in one clip. Start neutral, then spend `primary`, `highlight`, or `danger` only on the focal relationship or conclusion.

## Material Overrides

`visual_recipe.material_id` changes texture within the project profile. It never selects another palette.

- `editorial_color_field`: permits one hard-edged surface field; accent coverage remains bounded.
- `technical_blueprint`: permits measured auxiliary linework; it does not turn every profile blue.
- `archival_paper` / `film_grain`: permit restrained print/grain texture; they do not introduce beige page templates.
- `luminous_data`: permits one endpoint or active edge glow when the project profile also allows it. Use `.mg-endpoint` or `data-mg-emphasis="endpoint"`; maximum blur is 12px.
- Other materials keep glow off and use the selected profile's semantic colors.

Profile accent budgets are 8%-12% of the paused frame. Large shapes use `surface` or `surface_recessed`; accent colors cannot fill the root canvas. Color is not the only signal: pair it with scale, position, label, stroke pattern, or motion order.

## Motion Hierarchy

Motion communicates hierarchy rather than decorating every element:

1. Establish the hero structure.
2. Introduce the L1 headline or focal metric.
3. Build the relation or evidence in causal order.
4. Lock one conclusion and hold.

Use the profile timing variables and the director-selected `motion_id`. Never loop decorative motion. `material_id` does not alter timing.

## Validation

`apply-html` fails with `qa_failed` for undeclared colors, token redefinition, unsupported fonts, too many color roles, root-sized accent fills, profile/material glow violations, or profile contrast below 4.5:1. These checks run before the existing Podcastor sanitizer, canvas-fit report, composition report, and Chrome keyframe inspection.

Visual inspection must still confirm the accent-area budget, hierarchy, transparency over B-roll, and a distinct entry/build/hold sequence.

## Research Basis

The profile rules synthesize UIUX Pro Max's editorial-grid and exaggerated-minimalism guidance with public data-visualization and motion-system guidance:

- [Urban Institute Data Visualization Style Guide](https://urbaninstitute.github.io/graphics-styleguide/): stable palette order and consistent visual grammar.
- [Datawrapper Color Style Guide](https://www.datawrapper.de/blog/colors-for-data-vis-style-guides): begin with neutrals and use color selectively for focus.
- [Building color palettes in data visualization style guides](https://pmc.ncbi.nlm.nih.gov/articles/PMC10797256/): separate categorical, sequential, diverging, neutral, and accent roles.
- [CMU Data Visualization Guidelines](https://www.cmu.edu/brand/brand-guidelines/data-viz.html): accessibility and restrained highlighting.
- [Motion in Design Systems](https://www.designsystems.com/5-steps-for-including-motion-design-in-your-system/): encode hierarchy, purpose, and brand personality in reusable motion rules.

Avoid the UIUX Pro Max HUD/Sci-Fi FUI anti-pattern for general technology content: neon cyan, low-contrast fine lines, repeated grids, and glow are not a substitute for editorial hierarchy.
