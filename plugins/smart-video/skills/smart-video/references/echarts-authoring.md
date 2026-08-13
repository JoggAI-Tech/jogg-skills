# ECharts Slide Authoring

Use this path only when the preserved Visual Intent selects `echarts` and the
source-bound structured data passes the semantic gate. ECharts is a Slide render
mode, not a separate shot type.

## Design Source

Read the same locked whole-video MASTER as every HTML/SVG Slide. Use its chart
guidance, semantic palette, hierarchy, density, and stable-final-frame rules.
Choose chart structure from the data relationship, never from decoration.

| Relationship | Prefer |
| --- | --- |
| continuous trend | line or area |
| category comparison or ranking | bar |
| a few parts of a whole | pie or ring |
| numeric relationship | scatter |
| multi-metric profile | radar |
| distribution and outliers | box plot |
| density | heatmap |
| hierarchy or network | tree, treemap, sunburst, or graph |
| entity flow | Sankey |
| conversion stages | funnel |
| single progress state | gauge |

Use a standard 2D chart. The current runtime does not support ECharts GL, remote
maps, custom `renderItem`, or external data.

## Optional Local Reference Search

Use the bundled index only for structural guidance:

```bash
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" search "smooth line time series" --limit 5 --json
python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py" show line-smooth --json
```

Select only `runtime_supported:true`. Never copy sample data, labels, colors,
URLs, controls, or JavaScript.

## Spec

Use a curated recipe when it exactly matches the relationship:

```json
{
  "asset_type": "echarts_mg",
  "recipe_id": "universal-line-bar",
  "title": "Accuracy improves with focused practice",
  "support": "42% baseline to 78% after practice",
  "transition_at_s": 2.0,
  "layout": "standard",
  "data": {
    "labels": ["Baseline", "After practice"],
    "values": [42, 78]
  }
}
```

For another supported pattern, use `official-example` with pure JSON option data:

```json
{
  "asset_type": "echarts_mg",
  "recipe_id": "official-example",
  "title": "Accuracy improves",
  "support": "Focused listening practice",
  "transition_at_s": 2.0,
  "layout": "standard",
  "data": {
    "example_id": "bar-simple",
    "option": {
      "grid": {"left": 96, "right": 96, "top": 64, "bottom": 64, "containLabel": true},
      "xAxis": {"type": "category", "data": ["Baseline", "After practice"]},
      "yAxis": {"type": "value", "min": 0, "max": 100},
      "series": [{
        "id": "accuracy",
        "type": "bar",
        "data": [42, 78],
        "itemStyle": {"color": "$mg-primary"}
      }]
    }
  }
}
```

## Contract

- Use source-authorized labels, values, units, order, and uncertainty only.
- Match `title` and `support` to the current shot's screen content.
- Derive `transition_at_s` from the matching `semantic_timeline` cue using
  `start_ratio * duration_seconds`; never trigger a result before its exact
  `narration_anchor`.
- Keep `transition_at_s` inside the active window and before
  `stable_hold_start_ratio * duration_seconds`.
- Use `$mg-*` color tokens; never use literal colors or themes.
- Keep labels inside the MASTER safe area: `96px` horizontal / `64px` vertical
  for `16:9`, or `54px` horizontal / `96px` vertical for `9:16`.
- Use a transparent chart surface; the shared `.mg-backdrop` handles composition.
- Use one to eight series and at most 1,000 array items; aggregate before authoring.
- Keep the option below 64 KB.
- Do not include initialization, `setOption`, resize code, functions, callbacks,
  events, imports, script tags, URLs, data URIs, toolbox, brush, runtime timeline,
  remote maps, or GL components.

Read [echarts-options.md](echarts-options.md) for accepted declarative option
patterns. The existing trusted runtime owns ECharts initialization, token
resolution, transition execution, and HTML adaptation.

## Attach And Inspect

After the authoritative projector creates the production plan, place the complete
spec object at `shot.html_design.echarts_mg_spec` for the matching projected shot
before `run`. Validate the author spec first:

```bash
python3 "<plugin-root>/skills/smart-video/scripts/validate_slide_generation.py" \
  --spec "/absolute/path/to/echarts-spec.json" \
  --duration-seconds 15
```

Keep its existing `mg_director`, `clip_id`, `shot_type`, and
`render_mode` unchanged. The runtime validates the declarative spec, injects its
trusted local ECharts adapter, and materializes the HTML during project creation.

Do not use `apply-echarts` for a new ECharts Slide: that command requires an
existing registered checkpoint and cannot create one. It remains valid only when
continuing a historical run that already contains that checkpoint.

Inspect the entry, data reveal, and stable final frame. Verify labels, values,
units, chart scale, clipping, overlap, backdrop opacity, and source fidelity.
Repair the spec in the production plan and restart only before paid media work has
begun. Once a run owns remote task IDs, follow normal recovery and do not resubmit
paid work.
