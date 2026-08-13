# ECharts Options

Author declarative JSON only. Preserve source data exactly and keep the option as
small as the relationship allows.

## Common Forms

Line:

```json
{"id":"trend","type":"line","data":[12,18,31],"smooth":true,"showSymbol":false,"lineStyle":{"color":"$mg-primary","width":6}}
```

Bar:

```json
{"id":"ranking","type":"bar","data":[12,20,15],"barMaxWidth":52,"itemStyle":{"color":"$mg-primary","borderRadius":[6,6,0,0]}}
```

Pie:

```json
{"id":"share","type":"pie","radius":["45%","70%"],"data":[{"name":"A","value":40},{"name":"B","value":60}],"label":{"formatter":"{b}: {d}%"}}
```

Scatter:

```json
{"id":"relationship","type":"scatter","data":[[12,20],[18,28],[26,35]],"symbolSize":14,"itemStyle":{"color":"$mg-highlight"}}
```

Use direct `series.data` for a small series. Use `dataset` and `encode` when
several series share one table:

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

## Layout

- Use `grid.containLabel:true`.
- Keep the grid inside the MASTER safe area: `96px` horizontal / `64px` vertical
  for `16:9`, or `54px` horizontal / `96px` vertical for `9:16`.
- Reduce ticks or widen the grid before rotating labels.
- Use a legend only for multiple named series.
- Label only points that matter to the conclusion.
- Preserve units in axes or static labels.
- Keep nulls as null and preserve source order unless an authorized transformation
  explicitly changes it.

## Color Tokens

Use only `$mg-ink`, `$mg-muted`, `$mg-primary`, `$mg-highlight`, `$mg-danger`,
`$mg-outline`, `$mg-surface`, `$mg-surface-recessed`, or `transparent`.

## Remove

Remove functions, formatter callbacks, events, toolbox, brush, timeline,
`graphic`, custom `renderItem`, remote assets, external maps, image symbols,
initialization, `setOption`, resize code, and all GL or 3D components. The runtime
owns execution and timing.
