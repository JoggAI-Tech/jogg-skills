# ECharts Options

Adapt an official example into JSON only. Correct data mapping comes first;
preserve only options that help a video frame communicate.

## Minimal Cartesian Option

```json
{
  "grid": {"left": 24, "right": 24, "top": 32, "bottom": 24, "containLabel": true},
  "xAxis": {"type": "category", "data": ["A", "B", "C"]},
  "yAxis": {"type": "value"},
  "series": [{
    "id": "values",
    "type": "bar",
    "data": [12, 20, 15],
    "itemStyle": {"color": "$mg-primary"}
  }]
}
```

Do not include initialization, `setOption`, `resize`, event handlers, imports,
script tags, or functions. The bundled runtime owns them.

## Shared Data

Use direct `series.data` for one small series. Use `dataset` and `encode` when
several series share a table:

```json
{
  "dataset": {
    "source": [
      ["month", "sales", "profit"],
      ["Jan", 120, 32],
      ["Feb", 180, 48],
      ["Mar", 150, 41]
    ]
  },
  "xAxis": {"type": "category"},
  "yAxis": {"type": "value"},
  "series": [
    {"id": "sales", "type": "bar", "name": "Sales", "encode": {"x": "month", "y": "sales"}},
    {"id": "profit", "type": "line", "name": "Profit", "encode": {"x": "month", "y": "profit"}}
  ]
}
```

Use named dimensions and replace every upstream sample row with project data.

## Axes And Layout

- Category: `{"type":"category","data":[...]}`
- Value: `{"type":"value","min":0}`
- Time: `{"type":"time"}` with timestamps, date strings, or `[time,value]`
- Log: `{"type":"log"}` only when values are positive and magnitude matters

Set `grid.containLabel:true`. Reduce ticks or widen the grid before rotating
labels. Keep axis labels short enough for the active visual area.

## Reading Aids

- Use `tooltip.trigger:"axis"` for shared-axis line/bar and `"item"` for pie,
  scatter, map, or graph.
- Use a legend only for multiple named series. Use `legend.type:"scroll"` when
  names cannot fit.
- Label only a few high-value points. Built-in templates such as `"{b}: {c}"`
  are allowed; formatter functions are not.
- Use `visualMap` only when color or size encodes a numeric dimension.
- Use `dataZoom` only for a necessary data window; video usually benefits from
  aggregation.

## Common Series

Line:

```json
{"id":"trend","type":"line","data":[12,18,31],"smooth":true,"showSymbol":false,"sampling":"lttb","lineStyle":{"color":"$mg-primary","width":6}}
```

Bar:

```json
{"id":"ranking","type":"bar","data":[12,20,15],"barMaxWidth":52,"itemStyle":{"color":"$mg-primary","borderRadius":[6,6,0,0]}}
```

Pie:

```json
{"id":"share","type":"pie","radius":["45%","70%"],"data":[{"name":"A","value":40},{"name":"B","value":60}],"label":{"formatter":"{b}: {d}%"}}
```

Use a bar when pie categories exceed about six. Use `roseType` only when radius
is an intentional second encoding.

Scatter:

```json
{"id":"relationship","type":"scatter","data":[[12,20,6],[18,28,9],[26,35,12]],"symbolSize":14,"itemStyle":{"color":"$mg-highlight"}}
```

Dynamic symbol-size functions are not allowed. Precompute numeric item sizes.
Graph and Sankey require explicit local nodes/links. Hierarchies require nested
local data. Maps may use only the bundled USA map. Never retain `ROOT_PATH`,
`fetch`, `registerMap`, CDN paths, or demo datasets.

## Style Tokens

Use only `$mg-ink`, `$mg-muted`, `$mg-primary`, `$mg-highlight`, `$mg-danger`,
`$mg-outline`, `$mg-surface`, `$mg-surface-recessed`, or `transparent`.
Do not copy literal colors, shadows, gradients with literal stops, or example
themes. The runtime resolves tokens from the selected visual context.

## Remove From Examples

Remove `toolbox`, `brush`, `timeline`, `graphic`, custom `renderItem`, events,
callbacks, formatter functions, debug controls, remote media, external maps, and
all GL series. Keep `universalTransition` only when before/final data structures
correspond. The runtime accepts 1-8 series, options below 64 KB, and arrays up to
1,000 items; aggregate larger data first.
