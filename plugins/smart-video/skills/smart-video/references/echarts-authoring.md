# New Slide ECharts Authoring

Use this workflow only for a new Slide whose authoritative design contract already
selects `render_mode: echarts`. Read [html-authoring.md](html-authoring.md) for the
shared request, manifest, provenance, stage, and post-render rules, then read
[echarts-options.md](echarts-options.md). Imported chart clips use
[legacy-echarts-authoring.md](legacy-echarts-authoring.md).

An ECharts validation failure never changes the strategy or render mode. Stop with
the precise validation error. Do not generate HTML/SVG as a fallback and do not use
legacy recipes or `apply-echarts` for a new Slide.

## LLM Author Output

Write exactly one UTF-8 JSON object conforming to
`assets/contracts/echarts-author-spec.v1.schema.json`:

```json
{
  "schema_id": "smart-video.echarts-author-spec.v1",
  "version": 1,
  "stage": "llm_author",
  "identity": {
    "video_id": "video-001",
    "shot_id": "shot-001",
    "segment_id": "segment-001",
    "slide_id": "slide-001",
    "clip_id": "clip-001"
  },
  "design_strategy": {
    "id": "smart_video_slide_design",
    "version": "1.0.0",
    "selection_source": "production_default"
  },
  "visual_system": {"id": "visual-system-001", "version": "1.0.0"},
  "render_mode": "echarts",
  "source_data": {"labels": ["Q1", "Q2"], "values": [20, 42]},
  "source_data_sha256": "<scoped-canonical-json-sha256>",
  "final_frame_review_status": "pending_render",
  "data_bindings": [
    {"source_pointer": "/labels", "option_pointer": "/xAxis/data"},
    {"source_pointer": "/values", "option_pointer": "/series/0/data"}
  ],
  "option": {
    "xAxis": {"type": "category", "data": ["Q1", "Q2"]},
    "yAxis": {"type": "value"},
    "series": [{"id": "values", "type": "line", "data": [20, 42]}]
  }
}
```

Copy identity, strategy, Visual System identity/version, source data, and source
hash from the request. Preserve structured data exactly, including labels, values,
units, nulls, uncertainty, attribution, ordering, nodes, links, and coordinates.
Use the option only to encode that data; do not invent or silently normalize it.
Each `data_bindings` entry maps one RFC 6901 `source_pointer` subtree to one
`option_pointer` subtree with exact deep structural equality. Arrays, objects,
nulls, types, and order must match. Bind a whole array, never remap its scalar
members by index. Bindings must cover every scalar source leaf and every factual
leaf in a recognized rendered option data surface. Arbitrary storage paths and
nonrendered stashes are not binding destinations.

Recognized destinations are consumed `dataset.source`/`dimensions`; axis
`data`/`name`; type-appropriate series data surfaces and `name`; radar indicators;
legend data; title text/subtext; markPoint/markLine/markArea data; visualMap
categories/pieces; and calendar ranges, including subtrees beneath those surfaces.
Standard direct series data is an array. Graph and Sankey choose exactly one node
collection alias, `data` or `nodes`, and never provide both; they choose at most
one link alias, `links` or `edges`, and Sankey requires one. Nodes have stable,
unique IDs or unambiguous names. Every link endpoint resolves to exactly one
declared node identity; dangling or ambiguous endpoints fail. Hierarchy data is an
array of identified nodes whose optional `children` recursively follow the same
shape. Graph-only surfaces remain invalid on line, bar, and unrelated types.

Validate direct family shapes without converting source values: candlestick items
contain exactly four OHLC values, boxplot items exactly five values, heatmap items
at least x/y/value, scatter/effectScatter items at least two coordinates, and lines
items a `coords` path with at least two coordinate pairs. Where ECharts supports a
data-item object, its `value` array follows the same rule. Preserve every item and
its order through exact subtree binding.

A dataset is consumed only when a supported series has no explicit `data` key
(including no `data: []`), explicitly selects it with exactly one valid
`datasetIndex` or unique matching `datasetId`, supplies a nonempty declarative
`encode`, and every encoded dimension resolves against a nonempty local source or
explicit dimensions. Encode channels are a closed, series- and coordinate-aware
static allowlist: Cartesian `x`/`y`; polar `radius`/`angle`; calendar
`time`/`value`; geographic `lng`/`lat` and type-appropriate `value`; pie, funnel,
radar, and map `itemName`/`value`; theme river `single`/`value`/`itemName`; and
parallel `dimN`. Unsupported channels fail, and `tooltip` is interaction-only and
never proves final-frame rendering. Each ordinary channel consumes exactly one
dimension; candlestick `y` consumes exactly four and boxplot `y` exactly five.
Radar `value` may consume multiple dimensions. Extra values in a one-dimension
channel do not make hidden facts visible.

Across all series consuming a dataset, every factual dimension must reach an
allowed static channel or be source-authorized through an exact binding to another
recognized static rendered surface. A `show: true` series/end/mark label may use a
pure `{@dimension}` formatter to make that dimension visible, but only when the
series consumes that dataset and the mark has rendered data. A `visualMap.dimension`
counts only when it resolves against and applies to a consumed dataset series and
its controller or `inRange` encoding is static. A whole `dataset.source` binding
proves source equality, not visibility of unencoded columns. Every dataset
component must be consumed by at least one valid series, and every factual dataset
leaf must remain covered by a source binding; unused or invented datasets fail. At least one binding
must reach consumed direct series data or a consumed dataset source. Axis, title,
legend, series-name, and other supplemental bindings cannot replace that core
rendered relationship.
The closed dataset-capable set is line, bar, pie, scatter, effectScatter, radar,
funnel, pictorialBar, themeRiver, boxplot, candlestick, heatmap, map, and parallel.
Other standard series remain supported through their direct type-appropriate data.

Visual styling remains subject to the locked Visual System and is not a source
fact. Overlapping source or destination bindings fail. Exact duplicate display is
allowed only when every duplicate carries the same
`duplicate_display_authorization_id` and the matching request source binding has
`allow_duplicate_display: true`. Unbound, invented, reordered, or drifted labels,
values, units, nulls, attribution, nodes, links, or coordinates fail.

Treat visible series/end labels, axis labels, mark labels, gauge detail/axis labels,
legend formatters, and visualMap formatters as rendered content. An unbound
formatter may contain only built-in placeholders such as `{b}`, `{value}`, or
`{@dimension}` that are valid for that component, plus whitespace. Ignore a
placeholder-adjacent segment only when `str.strip()` makes it empty. Every other
static fragment outside placeholders, including punctuation and symbols, requires
an existing `data_bindings` entry whose `option_pointer` identifies the formatter
and whose `source_pointer` resolves to that exact source literal. Each binding
authorizes only its matching occurrence; it does not authorize another symbol or
additional text. Every non-formatter binding still requires exact value or subtree
equality. A formatter does not become safe merely because it is declarative rather
than executable.

Validate every mark data item and item-level label. Accept only `min`, `max`,
`average`, and `median` statistical types or a locator compatible with the series
coordinate system. Cartesian `coord` contains exactly two non-null scalar values;
Cartesian axis locators use only `xAxis`/`yAxis`. Polar locators use only
`radiusAxis`/`angleAxis`; geo, radar, and calendar marks use a two-value `coord`.
Reject incompatible fields and mixed locator forms. `markLine` and `markArea`
endpoint pairs follow the same rules. Empty data, empty items, and name/value/style
without a locator fail. A dataset placeholder inside an item-level mark label
counts as static rendering only when a binding reaches that item's locator, not
merely its name, label, value, or style.

Dataset objects use only `id`, `source`, `dimensions`, and `sourceHeader`; dimension
descriptors use only `name`, `type`, and `displayName`. Series use the documented
built-in identity, data, coordinate, mark, animation, and presentation option
fields. Reject every unknown dataset or series field, including scalar, array, and
object stashes; never treat ignored custom storage as harmless styling.
Treat the complete option surface as closed: every admitted component must have
its documented object or object-array shape, and every component uses a recursive
field allowlist. Reject malformed component values and unknown fields rather than
skipping them. The JSON Schema establishes the v1 outer author-object contract;
the stdlib validator enforces these detailed ECharts component constraints with
depth and node budgets. Dynamic `textStyle.rich` token names form a wildcard map,
but every token value is validated as a closed text-style object. Unlisted nested
API fields fail closed. Dataset source/dimensions, series data collections and
encode, and mark data use their existing source-binding and type-specific
validators only after the dataset, series, or mark parent has passed its closed
field profile. Dimension descriptors, encode channels, direct data-item objects,
graph nodes/links/categories, hierarchy nodes, and lines items also use closed
type-specific profiles. Delegation never creates an open parent or item object.

The output is JSON only. Do not emit HTML, CSS, script text, imports, JavaScript,
functions, generators, `yield`, function-like strings, callbacks, event handlers, actions, `graphic`,
relative or external resources, remote/data/blob/file/JavaScript URLs, external
maps, plugins, any `*3D`/`*GL` component or series, `custom`, or `renderItem`.
Formatter template strings such as `"{b}: {c}"` are declarative only when they
also satisfy the visible-source rule above. Executable formatters are forbidden.
Normalize JavaScript block/line comments before
executable detection so comments cannot split `async`, `function`, `*`, a name,
an argument list, `yield`, or an arrow. The static final state must communicate the complete
meaning without tooltip, hover, zoom, brush, toolbox, or other interaction.

## Declarative Breadth

Use the built-in 2D ECharts surface available to the local runtime: standard line,
bar, pie, scatter, radar, boxplot, candlestick, heatmap, map/lines, parallel,
graph, tree, treemap, sunburst, Sankey, funnel, gauge, pictorial bar, theme river,
datasets, axes, grids, polar/radar coordinates, calendars, legends, labels,
visualMap, and built-in marks. Use only the bundled `USA` map when a local map is
required. Keep 1-8 series and the canonical option below 64 KiB.

Use one primary visual anchor and a restrained reveal. The manifest, not ad hoc
code, owns exact deterministic motion phases and the final stable hold. Every
ECharts phase has `animation_name: null` and one closed `echarts_action` object:

- Start with an active `{"type":"establish_chart"}`.
- Use zero or more active intermediate actions:
  `{"type":"reveal_series","series_ids":["stable-series-id"]}`;
  `{"type":"highlight_data","series_id":"stable-series-id","data_indices":[0]}`;
  or `{"type":"show_annotation","series_id":"stable-series-id","annotation":"markPoint|markLine|markArea"}`.
- End with a `stable_hold` `{"type":"hold_conclusion"}`.

Action objects reject every extra field. Series IDs and data indices are nonempty
and unique. Referenced series IDs must resolve uniquely in the validated author
option. `highlight_data` accepts only in-range indices into that series' direct
`data` array; v1 rejects dataset-backed or otherwise data-less targets instead of
guessing row semantics. `show_annotation` requires the selected series to contain
the selected mark component with nonempty `data`. Do not use generic action names,
payload bags, target strings, inferred targets, automatic action selection, or a
render-mode fallback.

## Trusted Adapter Output

The LLM never writes adapter HTML or scripts. A trusted local adapter may create
HTML, carry the same root attributes and backdrop/content structure defined in
[html-authoring.md](html-authoring.md), and inject exactly these bundled local
scripts in this order:

```html
<script src="runtime/vendor/echarts.min.js"></script>
<script src="runtime/vendor/gsap.min.js"></script>
<script src="runtime/vendor/smart-video-echarts-timeline.js"></script>
```

No other script, inline script body, URL, asset, or executable extension is
allowed. Record the resulting HTML as `trusted_local_adapter` in the manifest,
then validate with `--phase pre-render`. The controlled runtime creates this output
through the dedicated `echarts-author` endpoint; it never converts the author JSON
to a legacy recipe.

Hash the exact authored JSON file bytes and record the digest as both the author
artifact SHA-256 and manifest `author_spec_sha256`. The adapter root and its unique
`#echarts-root` carry `data-author-spec-sha256` with that exact digest. The adapter
also embeds the complete declarative JSON in one inert
`<template id="echarts-author-spec" data-author-spec-sha256="...">`; validation
parses it and requires exact semantic equality with the author artifact. An empty
chart root plus scripts, a stripped template, or changed embedded option cannot
pass.

Post-render status and trusted evidence follow [html-authoring.md](html-authoring.md).
Keep author output, manifest, and report status `pending_render`. Post-render
validation additionally requires `trusted-ready`, the observed
`hold_conclusion`, a nonzero ECharts canvas, complete ECharts text measurement,
zero clipped or overlapping ECharts text, zero browser failures, and exact
approved runtime hashes. No caller-authored report can substitute for that
attestation.
