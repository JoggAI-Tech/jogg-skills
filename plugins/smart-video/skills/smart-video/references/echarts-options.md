# New Slide ECharts Options

Build declarative JSON from the authoritative source relationship. Use an official
example only as structural guidance; never copy its sample data, controls, URLs,
scripts, theme, or colors.

## Relationship Mapping

| Source relationship | Built-in option surface |
| --- | --- |
| trend or time series | line, area, calendar |
| category comparison or ranking | bar, pictorial bar |
| parts of a whole | pie or ring |
| numeric relationship or distribution | scatter, boxplot, heatmap |
| multi-metric profile | radar, parallel |
| hierarchy | tree, treemap, sunburst |
| network or route | graph, map, lines |
| flow | Sankey |
| stages or state | funnel, gauge |
| OHLC | candlestick |

Do not change a preserved `render_mode` because a preferred family is unavailable.
Return the validation failure without fallback.

## Data Forms

Use direct `series.data` for a small independent series. Use `dataset` and
`encode` when multiple series share the same table:

```json
{
  "dataset": {
    "id": "facts",
    "source": [
      ["month", "sales", "profit"],
      ["Jan", 120, 32],
      ["Feb", null, 48],
      ["Mar", 150, 41]
    ]
  },
  "xAxis": {"type": "category"},
  "yAxis": {"type": "value"},
  "series": [
    {"id": "sales", "type": "bar", "name": "Sales", "datasetId": "facts", "encode": {"x": "month", "y": "sales"}},
    {"id": "profit", "type": "line", "name": "Profit", "datasetId": "facts", "encode": {"x": "month", "y": "profit"}}
  ]
}
```

Keep nulls as null. Preserve source ordering unless the source contract explicitly
authorizes a derived order. Preserve units in axes or static labels and preserve
attribution and uncertainty in complete final-frame content.

Use exact subtree `data_bindings`, for example `source_pointer: /labels` to
`option_pointer: /xAxis/data`. The complete source and option subtrees must be
deeply equal, including array/object structure, nulls, types, and order. Do not
split arrays into index mappings or copy source data into an ignored custom stash.
Full source-leaf coverage and full factual-leaf coverage on recognized rendered
surfaces are mandatory. Styling branches such as `itemStyle`, `lineStyle`, labels,
emphasis, and symbols remain Visual System choices and are not source facts.

The closed rendered destination set is consumed `dataset.source`/`dimensions`;
category and other axis `data`/`name`; type-appropriate series data surfaces and
series `name`; radar indicators; legend data; title text/subtext;
markPoint/markLine/markArea data; visualMap categories/pieces; and calendar ranges,
including subtrees beneath those surfaces. Arbitrary top-level keys are never
binding destinations. Overlapping bindings fail. Duplicate display requires the
same explicit authorization ID on every duplicate plus a matching request source
binding with `allow_duplicate_display: true`.

Direct series data surfaces are arrays. Graph and Sankey use exactly one of `data`
or `nodes`; never provide both, even when one is empty. Use at most one of `links`
or `edges`, with one required for Sankey. Nodes require stable unique IDs or
unambiguous names. Each link source and target resolves to exactly one declared
identity. Tree/treemap/sunburst children recursively use identified object nodes.
Do not attach these surfaces to unrelated series.

For direct series, require four-value candlestick OHLC items, five-value boxplot
items, heatmap x/y/value tuples, scatter/effectScatter coordinate tuples, and lines
objects with a path of at least two coordinate pairs. Data-item objects may carry
the same required tuple in `value` where ECharts supports that form.

A dataset is rendered only when a supported series omits the `data` key,
explicitly selects it by valid `datasetIndex` or unique `datasetId`, and has a
nonempty `encode` whose dimensions resolve against nonempty local data. The static
channel allowlist is series and coordinate aware: Cartesian `x`/`y`; polar
`radius`/`angle`; calendar `time`/`value`; geographic `lng`/`lat` plus an allowed
value channel; pie/funnel/radar/map `itemName`/`value`; theme river
`single`/`value`/`itemName`; and parallel `dimN`. Unknown channels and `tooltip`
fail. Ordinary channels take exactly one dimension; candlestick `y` takes four,
boxplot `y` takes five, and radar `value` may take multiple. Every factual
dimension must be covered by these static channels across the consuming series,
by a `show: true` pure `{@dimension}` label on a genuinely rendered consumed
series/mark, by an applied static `visualMap.dimension`, or by an exact binding to
another recognized static rendered surface. Binding the whole source table does
not make an unencoded column visible.
Every dataset must be consumed and every dataset fact must be source-bound; unused
or invented dataset components fail. At least one binding must reach direct
consumed series data or a consumed dataset source; supplemental
axis/title/legend/name bindings do not satisfy that core requirement.
Dataset consumption is limited to line, bar, pie, scatter, effectScatter, radar,
funnel, pictorialBar, themeRiver, boxplot, candlestick, heatmap, map, and parallel.
All other allowed 2D series continue to use their direct data surfaces.

## Allowed Declarative Features

Use standard series; `dataset`; Cartesian, polar, radar, parallel, single, calendar,
and geographic coordinates; `visualMap`; legends; static labels; and built-in
`markPoint`, `markLine`, and `markArea`. Graphs and Sankey require exact local
nodes and links. Hierarchies require exact nested local data. Maps may use only the
bundled `USA` map.

Use built-in formatter templates only. Precompute symbol sizes and derived values
upstream when they are source-authorized. Do not encode facts only in tooltip or
interaction. Do not include toolbox, brush, or data zoom controls.

Visible series/end labels, axis labels, mark labels, gauge detail/axis labels,
legend formatters, and visualMap formatters are content surfaces. Without an exact
binding to the complete source string, a formatter may contain only supported
built-in placeholders for that component and whitespace-only static segments.
Normalize only with `str.strip()` when deciding whether a segment is empty. Every
other static fragment, including punctuation, comparison signs, units, and
currency symbols, uses an existing `data_bindings` entry: point `option_pointer`
to the formatter and `source_pointer` to the exact source literal. The binding
authorizes only that matching occurrence, never another fragment or extra text.
Thus `{name}` needs no literal binding, while the colon in `{b}: {c}` does.
Non-formatter bindings continue to require exact value or subtree equality. A
pure `{@dimension}`, `{@[2]}`, or Unicode-name placeholder such as `{@来源}`
additionally requires a real dataset dimension, `show: true`, and a consumed
series or source-bound rendered mark.

Use `seriesLayoutBy: row` only when row-oriented dimension names and encode
references resolve exactly. Direct scatter and heatmap may use an in-bounds
numeric `visualMap.dimension`; category-axis scatter may use one-dimensional
direct values. Graph and Sankey link endpoints may use in-bounds numeric node
indices or unique string identities. Pie `animationType` and map `layoutCenter` /
`layoutSize` remain presentation options and never authorize source-data drift.

Use only the closed dataset keys `id`, `source`, `dimensions`, and `sourceHeader`,
and documented built-in series fields. Unknown fields such as `stash` fail even
when their values look like presentation data; no ignored option subtree may carry
facts. All admitted option components are closed as well: enforce each component's
object or object-array shape and recursively reject unknown fields under bounded
depth and node counts. `textStyle.rich` is the only wildcard object map: token
names are dynamic, while each token value uses the closed text-style profile.
Dataset source/dimensions, series data collections and encode, and mark data enter
their existing source-binding and type-specific validators only after their
dataset, series, or mark parent is closed. Dimension descriptors, encode channels,
direct data-item objects, graph nodes/links/categories, hierarchy nodes, and lines
items have closed type-specific profiles; exact source equality never authorizes
an unknown ECharts field. Anything absent from these profiles fails closed. The v1
JSON Schema defines the outer author object; the stdlib validator owns these
detailed ECharts option constraints.

For marks, use one locator form per item. Cartesian marks use a supported
statistical type, a two-value non-null `coord`, or compatible `xAxis`/`yAxis`
fields. Polar marks use `radiusAxis`/`angleAxis`; geo, radar, and calendar marks
use a two-value `coord`. Reject mixed or incompatible locator fields. A binding to
name, value, label, or style does not make a mark locator source-bound.

## Forbidden Surface

Reject functions, generators, `yield`, function-like or executable strings,
callbacks, events, actions,
all `graphic`, `custom`/`renderItem`, imports, initialization code, `setOption`,
resize code, relative assets, image/path resource strings, remote loading,
URL/data/blob/file/JavaScript resources, external maps, plugins, and ECharts GL.
Normalize JavaScript block and line comments before executable-string checks;
comments cannot split function/generator/async tokens, argument lists, or arrows.
Reject every key or series ending in `3D` or `GL`, including `grid3D`, `xAxis3D`,
`yAxis3D`, `globe`, `bar3D`, `scatter3D`, `surface`, `map3D`, `lines3D`, `line3D`,
`scatterGL`, `linesGL`, `flowGL`, and `graphGL`. `geo` may be an object or array,
but every map must be the bundled `USA` map.

Keep the canonical option at or below 64 KiB and use 1-8 series. Aggregate larger
data only when that transformation is explicitly authorized; otherwise return to
the source contract rather than dropping values.
