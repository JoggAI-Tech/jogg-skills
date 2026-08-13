---
name: smart-video
description: Use when the user asks to plan, create, continue, inspect, edit, preview, or render a Smart Video with Jogg voices, talking avatars, B-roll, semantic Slides, ECharts, subtitles, BGM, or a local MP4.
---

# Smart Video

Create an editable video through the npm-managed local Smart Video Studio. Use
`smart-video.sh` on macOS and `smart-video.cmd` on Windows. The Skill owns content
planning and Slide design. The existing npm runtime owns media generation,
timeline assembly, compositing, editor state, and rendering.

## User Checkpoints

For a new video, show only:

1. A compact Brief and its confirmation request.
2. The complete Storyboard, subtitle choice, and its confirmation request.
3. A blocking problem that requires the user to change input, authentication, or a confirmed choice.
4. The completed preview, editor, download, or render result.

Do not expose private prompts, B-roll queries, internal intent objects, MASTER
content, template IDs, render modes, validation details, provider task IDs, or
implementation steps. Do not ask the user to choose a template, style family,
palette, chart type, or Slide strategy.

## Lifecycle

1. Run `doctor`; run `bootstrap` only when dependencies are missing.
2. Run `preflight` and use only its returned `settings_url` and runtime facts.
3. Create a new `workspace`. Reuse `--work-dir` only when explicitly requested.
4. Build the Brief from the topic, source boundary, audience, language, tone,
   target duration, aspect ratio, and B-roll availability. Accept `16:9` or
   `9:16`. Use the requested duration; when no duration is given, default to
   `180` seconds. Wait for Brief confirmation.
5. Follow [content-orchestration.md](references/content-orchestration.md) to create
   the hidden outline, complete script, six supported shot types, B-roll retrieval
   intent, and source-bound Communication Intent and Visual Intent for every
   Slide-bearing shot. Show the complete Storyboard and wait for confirmation.
6. After Storyboard confirmation, use the plugin's `$direct-slide-art` Skill once
   with the complete confirmed Brief, script, and ordered Slide-bearing shots.
   Write its exact output to `<workspace_dir>/plans/slide-art-direction.json`.
   Do not expose this private artifact, invoke the Skill once per Slide, or replace
   it with a style-family choice.
7. Follow [visual-reference.md](references/visual-reference.md) to generate one
   locked `MASTER.md` from the complete Brief, script, all Slide intents, and the
   exact art-direction artifact. Derive the private `design_domain` from the
   confirmed content before generation; never expose it or ask the customer to
   choose it. The bundled private UI UX Pro Max snapshot must pass its inventory
   checks. Missing, invalid, or mismatched input stops Slide production; no
   template or default design replaces it.
8. Write the MASTER's exact `runtime_visual_style_profile` into the whole-video
   planning document. Every Slide uses the same MASTER and follows
   [slide-design.md](references/slide-design.md). After authoritative projection,
   author each eligible declarative ECharts spec and attach it as
   `shot.html_design.echarts_mg_spec` before `run`. PiP Avatars default to the
   runtime's lower-right position. For `avatar_html`, author the Slide around the
   final position. Store `avatar_placement` only when the user requests another
   position; deleting that field restores the default.
9. Before `run` or any paid request, preserve the confirmed shot IDs, order,
   types, and durations, then pass `--avatar-mode planned`. The runtime derives
   Avatar, B-roll, and Slide targets independently from every shot's `shot_type`.
   Then invoke `run` with the completed production plan.
   New ECharts Slides are validated and materialized by the trusted runtime during
   project creation. A plan with ordinary HTML/SVG Slides stops at `waiting_html`.
10. For each pending ordinary HTML/SVG Slide, use
   [html-authoring.md](references/html-authoring.md) and submit it through
   `apply-html`. Preserve approved clips and repair only the failed clip.
11. Call `resume`. For Jogg Avatar shots, complete the existing Avatar and Voice
    confirmation in the local editor when requested. An Avatar shot never enters
    the TTS batch; its downloaded MP4 audio is the shot's sole narration audio and
    measured duration.
12. Use `preview` or the returned editor URL for review, then invoke `render` for
    the local MP4.

## Shot Types

Use exactly these internal types:

| Internal type | User-facing type |
| --- | --- |
| `avatar_only` | `Avatar Only` |
| `broll_only` | `B-roll Only` |
| `avatar_broll` | `Avatar + B-roll` |
| `avatar_html` | `Avatar + Slide` |
| `broll_html` | `B-roll + Slide` |
| `html_only` | `Slide Only` |

Shot type controls runtime composition. Slide render mode is independently
`html_svg` or `echarts`. Do not invent combined types such as `avatar_echarts`.

The six supported shot types are freely composable. Any type may appear at any
position, in any order, any number of times, next to the same type, or not at all.
Do not impose opening/closing placement, adjacency, sequence, ratio, coverage,
diversity, minimum-count, or maximum-count rules. Choose each shot independently
from its communication need and preserve the confirmed Storyboard exactly.

`production_format` is only a coarse legacy runtime capability flag. Use
`broll_html` when any shot contains a Slide and `broll` otherwise. It must never
select, rewrite, reorder, or remove a shot type; `shot_type` remains authoritative.

## Slide Production

Use `smart_video_slide_design@1.0.0` with
`selection_source: production_default`. This stable identity names the Smart
Video Slide capability; it does not select a template.

All new Slides use the npm-supported adaptive authoring path:

```text
visual_reference.reference_mode: visual_recompose
visual_reference.fallback_automatic: false
visual_reference.free_generation_selected: true
authoring_context.authoring_mode: full_html_recompose_v1
authoring_context.fidelity: adaptive
```

The required semantic scene and template ID remain private compatibility locators
for the current npm planner. They provide no palette, typography, composition,
component, or motion authority. If the runtime returns a strict-reference
checkpoint for a new Slide, stop and correct the plan; do not submit a template
patch and do not silently change design strategy.

Ordinary Slides use HTML, CSS, and optional inline SVG. ECharts Slides use pure
declarative JSON; the trusted existing runtime owns all ECharts JavaScript.
Model-authored JavaScript, remote resources, font downloads, and external assets
are forbidden.

## Commands

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
bash "<plugin-root>/scripts/smart-video.sh" preflight
bash "<plugin-root>/scripts/smart-video.sh" workspace
bash "<plugin-root>/scripts/smart-video.sh" run \
  --topic "How artificial intelligence changes manufacturing" \
  --duration-seconds 180 \
  --avatar-mode planned \
  --planning-file "<workspace_dir>/plans/production-plan.json" \
  --work-dir "<workspace_dir>"
bash "<plugin-root>/scripts/smart-video.sh" status --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" html-status --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" apply-html --run-id "sv-..." --clip-id "mg:shot-01" --html-file "/absolute/path/to/slide.json"
# Existing registered checkpoint only; new ECharts Slides use echarts_mg_spec before run.
bash "<plugin-root>/scripts/smart-video.sh" apply-echarts --run-id "sv-..." --clip-id "mg:shot-02" --spec-file "/absolute/path/to/echarts.json"
bash "<plugin-root>/scripts/smart-video.sh" resume --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" preview --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" refresh-broll --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" render --run-id "sv-..."
```

Derive media targets from confirmed shot types, not from approximate user
wording. Explicit Avatar and Voice IDs win. Never invent an unavailable profile.

## Recovery

Preserve every existing Jogg Task ID, idempotency key, downloaded media file,
approved Slide, and local project ID. Poll or resume known work; never resubmit a
paid request automatically. A lost submission response remains
`blocked_jogg_recovery` until reconciled.

B-roll uses the existing retrieval and replacement behavior in
[broll-selection.md](references/broll-selection.md). Do not add a second B-roll
selection system.

## Reference Routing

| Phase | Read |
| --- | --- |
| Brief, script, Storyboard, shot strategy, intents | [content-orchestration.md](references/content-orchestration.md) |
| Whole-video and per-Slide art direction | Plugin Skill `$direct-slide-art` |
| B-roll retrieval | [broll-selection.md](references/broll-selection.md) |
| Whole-video MASTER | [visual-reference.md](references/visual-reference.md) |
| Per-Slide design | [slide-design.md](references/slide-design.md) |
| HTML/CSS/inline SVG authoring | [html-authoring.md](references/html-authoring.md) |
| ECharts authoring | [echarts-authoring.md](references/echarts-authoring.md), then [echarts-options.md](references/echarts-options.md) |
| Jogg tasks and recovery | [jogg-task-lifecycle.md](references/jogg-task-lifecycle.md), optionally [jogg-api.md](references/jogg-api.md) |
| Local runtime behavior | [runtime-boundary.md](references/runtime-boundary.md) |

Import historical projects with `import --file` and an explicit workspace. Do not
auto-migrate imported Slide designs.
