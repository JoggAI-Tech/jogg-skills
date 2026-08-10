# Legacy ECharts Authoring

Use this imported-legacy path when a shot is better read as a chart. It stays inside the public
Smart Video skill and the selected semantic scene; it is not a parallel planner
or runtime dependency.

## Discover Before Rendering

Describe the chart type, behavior, and data relationship in one local query:

```bash
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" search "smooth line time series" --limit 5 --json
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" search "stacked bar leverage" --type bar --limit 5 --json
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" show line-smooth --json
```

The bundled index contains 329 official examples across 39 categories. Select a
result with `runtime_supported:true`, record its ID, and use title/categories
only for structural guidance. Read [legacy-echarts-options.md](legacy-echarts-options.md) before
adapting an option. Bundled templates are references, never project assets.

## Type Selection

Choose from the data relationship before searching for visual style:

| Relationship | Prefer | Category |
| --- | --- | --- |
| continuous trend or time series | line or area | `line` |
| category comparison or ranking | bar | `bar` |
| a few parts of a whole | pie or ring | `pie` |
| numeric relationships | scatter or bubble | `scatter` |
| geographic distribution or route | map or lines | `map`, `lines` |
| multi-metric profile | radar | `radar` |
| distribution and outliers | box plot | `boxplot` |
| two-dimensional density | heatmap | `heatmap` |
| network or hierarchy | graph, tree, treemap, sunburst | corresponding type |
| flow between entities | Sankey | `sankey` |
| conversion stages | funnel | `funnel` |
| single progress or state | gauge | `gauge` |

Use candlestick only for OHLC data, calendar for date density, and parallel axes
for multi-variable comparison. Prefer standard series over `custom`, `graphic`,
or interactive examples.

The runtime does not bundle ECharts GL. Reject `globe`, `bar3D`, `scatter3D`,
`surface`, `map3D`, `lines3D`, `line3D`, `scatterGL`, `linesGL`, `flowGL`, and
`graphGL`; choose a semantically equivalent supported 2D chart.

```bash
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" types
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" template <category>
```

## Recipes

Use a curated recipe only when its complete motion relationship matches the
selected scene and visual-reference composition:

| Recipe | Use for | Required data |
| --- | --- | --- |
| `universal-line-bar` | trend becoming a comparison | `labels`, `values` |
| `map-bar-morph` | US distribution becoming a ranking | `items: [{name,value}]` |
| `graph-propagation` | network expansion or contagion | `nodes`, `links` |
| `radar-reveal` | capability change | `indicators`, `values`, optional `baseline` |
| `causal-flow` | ordered causal transmission | `nodes`, `links` |
| `waterfall-decline` | increment/decrement contribution | `labels`, `deltas` |
| `stacked-leverage` | components accumulating by stage | `labels`, named series |

Use `official-example` for another supported 2D pattern. Choose a simpler chart
when an example needs GL, custom `renderItem`, executable graphics, an external
map, or remote data.

## Curated Spec

```json
{
  "asset_type": "echarts_mg",
  "recipe_id": "universal-line-bar",
  "title": "Leverage rises with prices",
  "support": "Prices -> collateral -> lending",
  "transition_at_s": 2.05,
  "layout": "standard",
  "data": {
    "labels": ["Prices", "Collateral", "Lending"],
    "values": [100, 146, 213]
  }
}
```

## Official Example Spec

Adapt the selected example into pure JSON. Replace every sample label and value
with project data. Preserve useful data shape, not colors, URLs, title, toolbox,
or demo controls.

```json
{
  "asset_type": "echarts_mg",
  "recipe_id": "official-example",
  "title": "Risk accelerates",
  "support": "Risk rises over four quarters",
  "transition_at_s": 1.8,
  "layout": "standard",
  "data": {
    "example_id": "line-smooth",
    "option": {
      "grid": {"left": 24, "right": 24, "top": 28, "bottom": 24, "containLabel": true},
      "xAxis": {"type": "category", "data": ["Q1", "Q2", "Q3", "Q4"]},
      "yAxis": {"type": "value"},
      "series": [{
        "id": "risk",
        "type": "line",
        "smooth": true,
        "showSymbol": false,
        "data": [18, 27, 45, 73],
        "lineStyle": {"color": "$mg-primary", "width": 7}
      }]
    }
  }
}
```

`data.initial_option` is optional. Without it, the runtime derives an entry
state and assigns stable series IDs. Provide it only for a meaningful before
state; preserve final series count, order, and IDs.

## Boundary

- Match `title` and `support` to the shot's `screen_slots`.
- Keep `transition_at_s` inside the active window and before shot end.
- Use JSON and local project data only. Functions, events, URLs, data URIs,
  external maps, GL, and arbitrary scripts are rejected.
- Use `$mg-*` semantic color tokens; literal colors are rejected.
- Keep options below 64 KB, 1-8 series, and arrays at or below 1,000 items.
- Use a transparent canvas and the shared background rule. Do not obscure B-roll.
- Never copy upstream source into `custom_html` or `custom_css`.

Apply through `apply-echarts`. Inspect entry, transition, and hold frames when
motion needs that evidence. Approval still requires one renderable,
non-transparent capture rather than three distinct frame hashes.

## Upstream And License

The index and representative templates come from the
[Apache ECharts examples](https://echarts.apache.org/examples/en/index.html) and
[apache/echarts](https://github.com/apache/echarts), licensed under Apache 2.0.
The snapshot date is 2026-07-30. Preserve copyright, license, NOTICE, example ID,
source URL, and ECharts version when redistributing substantially unchanged
upstream code. Production specs remove demo URLs, `ROOT_PATH`, `CDN_PATH`, and
sample data.
