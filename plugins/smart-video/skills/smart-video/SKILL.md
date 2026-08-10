---
name: smart-video
description: Use when the user asks to create, continue, inspect, edit, preview, import, or render a long-form Smart Video or Video Studio video with Jogg voices, talking avatars, B-roll, HTML/MG, subtitles, BGM, or a local MP4.
---

# Smart Video

Operate the npm-managed local Smart Video Studio and SmartVideo runtime. Use `smart-video.sh`
on macOS and `smart-video.cmd` on Windows. Users choose only Jogg OAuth or Local Media.
Extract a required topic/source brief and `duration_seconds`; convert minutes to seconds and default to `90`.

## User-Visible Communication

Work silently between required user checkpoints. User-facing messages are limited to:

1. The compact Brief and its confirmation request.
2. The public Storyboard, subtitle choice, and its confirmation request.
3. A blocking problem that cannot be recovered automatically and requires a user decision or action.
4. The completed preview, editor, download, or render result.

Do not narrate file reads, commands, schemas, private planning data, template IDs,
contracts, gates, validation details, retries, provider task IDs, or implementation
steps. Do not send routine progress commentary unless the user explicitly asks for
status. Recover from retryable failures silently and keep the last confirmed Brief,
Storyboard, and shot edits unchanged. When a blocking message is necessary, state
only the affected stage, the user-visible impact, and the required action.

Codex may display its own collapsible tool activity. Minimize that activity by
batching independent reads and checks when safe, but never weaken checkpoints,
resume safety, or per-shot retry isolation merely to reduce visible operations.

## Core Lifecycle

Follow this order for a new video:

1. On first use, invoke `doctor`. If it reports `dependencies_missing`, run
   `bootstrap`. After a plugin update, invoke `upgrade` once to atomically apply
   the aggregate and independently versioned child packages pinned by the new
   `runtime-bom.json`, then run `doctor`. Normal lifecycle commands never install
   host software. Do not present the deprecated `install-deps` alias.
2. Always invoke `preflight` before planning or `run`. It starts the loopback
   service and verifies `/health` and `/settings`. Use only the returned `settings_url`.
   Never construct, guess, or report a loopback URL before readiness.
3. Invoke `workspace` and use its new `workspace_dir`. Reuse a directory with
   `--work-dir` only when the user explicitly requests that existing workspace.
4. Generate and show only the compact Brief with the public goal, audience,
   evidence boundary, visual tone, and B-roll availability. Save that revision in
   the workspace and wait for confirmation or a natural-language revision; do not
   generate the hidden outline before confirmation. Do not expose strategy,
   prototype, grammar, Visual System, or other private design fields.
5. After Brief confirmation, generate the hidden outline and semantic shot
   skeleton, then generate narration and shot strategy in section batches. In the
   same director call, generate B-roll retrieval only for B-roll shots and separate
   source-bound Communication Intent and Visual Intent for every Slide-bearing
   shot. Do not add a model call for the two intents. Show the complete Storyboard
   and wait for confirmation or shot-level edits. For every shot, show its number and title,
   user-facing type, planned duration, and complete narration script. After all
   shots, show `Subtitles: No / Yes`, defaulting to
   `No`. Titles, summaries, section names, or shot counts alone are not a complete
   Storyboard and must not be presented for formal confirmation.
6. After Storyboard confirmation, route every Slide through
   [visual-knowledge.md](references/visual-knowledge.md), then
   [visual-reference.md](references/visual-reference.md), then
   [slide-design.md](references/slide-design.md). The system validates the complete
   qualitative Brief and source-bound Slide set, generates every grammar decision,
   selects one immutable prototype internally, and runs `compile_visual_system`
   once before `design_slide` for each Slide. Produce authoring-ready contracts as private
   planning output. Paid media execution remains unauthorized until every Slide
   passes author validation and approval.
7. Run the `runtime-readiness` validation phase against the exact
   `preflight_local_base_url`, then invoke `run` with the confirmed planning file
   and workspace. The BOM-pinned npm-managed runtime must create the project and stop at
   `waiting_html` before paid media submission. Evaluate the sole Failure Decision Table in
   [slide-design.md](references/slide-design.md) at every applicable phase. Author
   each valid new Slide through [html-authoring.md](references/html-authoring.md)
   or [echarts-authoring.md](references/echarts-authoring.md) according to its
   preserved `render_mode`, write `generation-manifest.json`, and pass
   `validate_slide_generation.py --phase pre-adapter`. Do not switch strategy,
   render mode, or authoring path after failure.
8. Submit a validated new Slide only through the dedicated loopback
   `html-author` or `echarts-author` endpoint in [runtime-boundary.md](references/runtime-boundary.md).
   Pass the exact request, manifest, and author file text; use the returned updated
   manifest for pre-render and post-render validation. Invoke
   `unsupported_render_runtime` when the endpoint is absent, the approved runtime
   identity mismatches, persistence fails, or trusted render attestation fails.
   Do not invoke legacy `apply-html` or `apply-echarts` for a new Slide.
   The validator sends a fresh nonce directly to the loopback runtime and accepts
   only the exact measured identity, capabilities, routes, and nonce response.
   A missing endpoint, caller-supplied report, mismatch, redirect, or non-loopback
   origin stops with `unsupported_render_runtime`.
9. Only an imported legacy clip that lacks a new Slide design contract may use its
   current `authoring_context`,
   [legacy-html-authoring.md](references/legacy-html-authoring.md), `apply-html`,
   or `apply-echarts`. Keep that compatibility path separate and do not
   auto-migrate the clip.
10. After every required clip is approved, call `resume` once. When the selected
   backend is Jogg and the plan has Avatar shots, it stops at
   `waiting_avatar_confirmation` before any paid media submission. Open the
   returned `editor_url`; after Jogg login, use the npm-managed Studio editor's existing
   `Avatar` and `Voice` tabs to preview and choose one of each. The choices are
   saved to the current project without opening another page or overlay. Call
   `resume` again. Local Media uses its configured local profile
   and skips this checkpoint because it has no selectable Avatar catalog.
   A profile-only replacement must not change scripts, Slides, or shot timing.
   Runs without Avatar shots skip this checkpoint. After confirmation, the same
   command continues non-Avatar TTS, Avatar text-mode generation, B-roll,
   subtitles, and local project creation from saved checkpoints. An Avatar shot
   never enters the TTS batch; its downloaded MP4 audio is that shot's sole
   narration and measured duration.
11. Use `preview` or the returned `editor_url` for review and editing. The editor
    may open an incomplete project; missing media must not block inspection, while
    final output remains strict.
12. Invoke `render` for the local MP4.

Use the host-appropriate launcher. macOS examples:

```bash
bash "<plugin-root>/scripts/smart-video.sh" preflight
bash "<plugin-root>/scripts/smart-video.sh" workspace
bash "<plugin-root>/scripts/smart-video.sh" run \
  --topic "How artificial intelligence changes manufacturing" \
  --duration-seconds 90 \
  --avatar-mode opening_closing \
  --planning-file "<workspace_dir>/plans/production-plan.json" \
  --work-dir "<workspace_dir>"
```

Map user wording for `avatar_mode` to `none`, `opening`, `opening_closing`, or
`all`. Explicit voice and avatar IDs win. Otherwise pass the requested persona
filters and let the runtime resolve its visible catalog or configured service
default; do not invent IDs or claim that an unavailable profile exists.

At the Jogg-only `waiting_avatar_confirmation`, do not ask the user to choose from text IDs.
Open `editor_url` and wait for the user to choose from the original `Avatar` and
`Voice` tabs in the npm-managed editor. Do not open a separate selection page, add an
overlay, or add a selector to the outer launcher. The next
`resume` reads that saved selection and continues. Do not synthesize a sample or
submit Avatar/TTS merely to populate the panel. A confirmed fingerprint prevents
the checkpoint from repeating on resume, and selection occurs before any paid
Jogg submission.

## Storyboard Confirmation

Brief confirmation and Storyboard confirmation are separate checkpoints. Interpret
`confirm` from the last complete user-visible checkpoint only: when the Brief was
last shown, confirm only the Brief; when the complete Storyboard was last shown,
confirm only the Storyboard. Never infer confirmation for a stage that has not been
shown. Do not write confirmed Storyboard state or invoke `run` until the complete
Storyboard has been displayed and confirmed.

Use these user-facing type names and never expose the internal type, template ID,
contract, semantic scene ID, or runtime fields:

| Internal type | User-facing type |
| --- | --- |
| `avatar_only` | `Avatar Only` |
| `broll_only` | `B-roll Only` |
| `avatar_broll` | `Avatar + B-roll` |
| `avatar_html` | `Avatar + Slide` |
| `broll_html` | `B-roll + Slide` |
| `html_only` | `Slide Only` |

Render every shot in this compact form, using its existing purpose as the title
when no separate title exists. This example is illustrative only; bracketed values
are placeholders, not facts:

```text
### Shot 03 - How Metric A Changed
Type: B-roll + Slide
Duration: 18s
Script: Metric A rose from [source value 1] to [source value 2] during [source period].
B-roll: [source-authorized visible footage]; Purpose: [supporting context].
Slide Design: [primary focus]; Relationship: [information relationship]; Order: [presentation order].
```

Project each optional public line deterministically from the existing structured
director plan without another model call. Follow the strict scalar fields,
validation, fixed delimiters, and deterministic label-localization contract in
[content-orchestration.md](references/content-orchestration.md). Omit each line
when its medium is absent. The public lines are descriptions, not production
inputs.

After the last shot, show:

```text
Subtitles: No

You can confirm the Storyboard or change any shot's type, duration, script, B-roll, or Slide Design where present.
```

If any required field is missing, complete the display before requesting
confirmation. After a natural-language shot edit, redisplay the complete updated
Storyboard and wait for confirmation again. Users never need to inspect or edit JSON.
Do not expose raw visual intent, visual segments, search queries, evidence IDs,
strategy choice, prototype, grammar, Visual System, `render_mode`, chart type,
internal intent names, or implementation details. Users may request natural-language
changes, but never ask them to choose a design strategy, mode, template, palette,
or chart type.

## Planning Boundary

The planning sequence is fixed:

```text
confirmed Brief revision -> bound hidden outline -> per-shot script and strategy
-> one director call for B-roll retrieval plus separate Communication Intent and
Visual Intent -> Slide input gate -> 16:9 grammar and prototype selection
-> compile_visual_system -> design_slide -> authoring-ready Visual Critic
```

Keep the complete planning bundle, hidden outline, prompts, and revision fields
private. A Brief edit before confirmation changes only the Brief. Confirmation
creates the bound hidden outline; a later confirmed Brief revision replaces that
outline before another Storyboard can be generated. Reject stale revisions.
Preserve user-locked shot strategies and preserve narration for a visual-only
edit. Changing B-roll or Avatar to Slide requires a narration proposal and user
confirmation before it becomes production state.

Export only the confirmed public plan through the runtime's authoritative
`build_smart_video_planning_payload(...)` projector. Do not hand-build the JSON
or invent aliases. In particular, `script` is the aggregate narration string,
shots are objects under `scene_groups[].shots[]`, and each shot uses `shot_type`
rather than `type`. Read the exact public planning contract in
[content-orchestration.md](references/content-orchestration.md) before saving the
plan. When the lifecycle permits `run`, it preflights this public contract before
project creation. Fix a reported JSON path and retry with the same workspace;
never bypass the preflight. The public payload is not storage for the new Slide
design contract.

Every shot needs topic-specific narration and render intent. Any internal
`avatar_html`, `broll_html`, or `html_only` shot must contain its enabled Slide
planning fields, but those existing fields do not replace the new authoring-ready
design contract or authorize its runtime execution. The top-level format is only a
summary (`mixed` when needed) and never rewrites per-shot types. Never start media
generation from a missing or contradictory plan.

The plugin workspace owns the planning file and revision state. Codex writes the
confirmed public plan into that workspace and passes the saved path to `run` only
for a currently supported workflow; users must never be asked to create or edit
`production-plan.json` themselves. A missing planning file remains a resumable
`blocked_planning` safety state.

For every new Slide, [content-orchestration.md](references/content-orchestration.md)
owns the Brief binding, director intents, B-roll retrieval, and public projection;
bind evidence and structured data only when applicable.
[visual-reference.md](references/visual-reference.md) owns grammar and prototype
selection plus selection provenance.
[slide-design.md](references/slide-design.md) owns the exact strategy contracts,
Visual System compilation, authoring-ready Slide contract, and sole Failure
Decision Table.

## Slide Design Strategies

Use `smart_video_slide_design@1.0.0` as the only production strategy. Independent
comparison results are external, dependency-proven snapshots and are never accepted
by the production compiler, request, manifest, author, or render contracts. Never
switch, substitute, degrade, or fall back, and never ask the customer to choose a
strategy. Read [visual-reference.md](references/visual-reference.md) and
[slide-design.md](references/slide-design.md) for the exact machine contract and
provenance rules.

## Slide Authoring Boundary

Treat every new Slide design contract as authoritative. Author `html_svg` as one
safe local HTML/CSS/inline-SVG artifact and author `echarts` as one declarative
JSON object. Read [html-authoring.md](references/html-authoring.md) for shared
contracts and [echarts-authoring.md](references/echarts-authoring.md) for ECharts.
Run the deterministic validator before adaptation. Never let runtime context
override design choices, infer a strategy, switch render mode, or route to legacy
authoring.

Static authoring success is not runtime proof. The controlled v1 runtime proves
support only when its approved identity matches
`assets/runtime/trusted-runtime-identity.v1.json`, the dedicated author endpoint
persists the exact linked artifacts, and post-render validation accepts the real
PNG plus runtime attestation. Keep request, manifest, author artifact, and report
`final_frame_review_status: pending_render`; caller or model assertions never
promote it. Apply `unsupported_render_runtime` on any missing or mismatched fact,
without changing strategy, render mode, or author output.
The bundled runtime includes both dedicated author routes, but file presence is
not execution proof. Continue only after the running service passes the fresh
runtime-readiness challenge with the pinned identity.

Imported legacy clips without a new design contract may continue only through
[legacy-html-authoring.md](references/legacy-html-authoring.md) and, for chart
clips, [legacy-echarts-authoring.md](references/legacy-echarts-authoring.md).
They are not auto-migrated. Legacy capture, retry, approval, and resume behavior
remains unchanged.

## Media And Recovery

When no backend is selected, Settings must ask the user explicitly to choose
Jogg OAuth or Local Media. Jogg remains preferred when connected. Local Media is
valid only before a Jogg submission and uses managed local TTS and ASR; it does
not provide Avatar rendering. Never infer a developer checkout or silently switch an
existing remote run to local media.

Jogg TTS, ASR, and avatar generation use unified Task resources. Persist the
`task_id` and local downloaded file, never a short-lived Task URL. Existing Task,
Operation, Artifact, or legacy video checkpoints are authoritative. Always poll
or `resume`; never resubmit paid work automatically. A `submission_unknown`
checkpoint stops at `blocked_jogg_recovery` because the remote request may have
succeeded.

Measured local narration determines shot timing, subtitles, MG windows, B-roll,
and rendering. The requested duration is a planning target, not a reason to
stretch audio or pad silence. `refresh-broll` is only for an explicit material
redo and never submits Jogg work. Preserve the `run_id` for resumable
`waiting_html`, `waiting_jogg`, `blocked_broll`, and `waiting_render` results.

## Other Actions

The `apply-html` and `apply-echarts` commands below are legacy-only. A new Slide
uses the dedicated author endpoints documented in [runtime-boundary.md](references/runtime-boundary.md).

```bash
bash "<plugin-root>/scripts/smart-video.sh" status --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" html-status --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" apply-html --run-id "sv-..." --clip-id "mg:shot-01" --html-file "/absolute/path/to/clip.json"
bash "<plugin-root>/scripts/smart-video.sh" apply-echarts --run-id "sv-..." --clip-id "mg:shot-02" --spec-file "/absolute/path/to/echarts.json"
bash "<plugin-root>/scripts/smart-video.sh" resume --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" preview --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" refresh-broll --run-id "sv-..."
bash "<plugin-root>/scripts/smart-video.sh" render --run-id "sv-..."
```

Import with `import --file "/absolute/path/project.json" --work-dir "<workspace_dir>"`.
It does not migrate schemas and rejects an existing project ID. Use
`--replace-existing` only when the user explicitly requests replacement.
Imported legacy directors remain compatible and must not be migrated automatically.

## Reference Routing

Read only the reference for the current phase:

| Phase | Required reference | Optional only when needed |
| --- | --- | --- |
| Content and shot planning | [content-orchestration.md](references/content-orchestration.md) | [broll-selection.md](references/broll-selection.md) for provider material |
| Slide planning and design | [visual-knowledge.md](references/visual-knowledge.md), then [visual-reference.md](references/visual-reference.md), then [slide-design.md](references/slide-design.md) | None |
| New Slide authoring | [html-authoring.md](references/html-authoring.md) | [echarts-authoring.md](references/echarts-authoring.md) and [echarts-options.md](references/echarts-options.md) only when preserved `render_mode` is `echarts` |
| Imported legacy clip authoring | [legacy-html-authoring.md](references/legacy-html-authoring.md) | Legacy-only: [legacy-echarts-authoring.md](references/legacy-echarts-authoring.md) and [legacy-echarts-options.md](references/legacy-echarts-options.md) for a chart clip |
| Jogg request or recovery | [jogg-task-lifecycle.md](references/jogg-task-lifecycle.md) | [jogg-api.md](references/jogg-api.md) for exact request shapes |
| Runtime, setup, security | [runtime-boundary.md](references/runtime-boundary.md) | None |
| Imported legacy recovery | Runtime compatibility only | Never load a legacy reference for a new Slide |

## Boundaries

Use only the pinned npm-managed loopback runtime. Business network access is limited to
Jogg and explicitly configured Pexels requests. Never call Podcastor, Hermes,
COS, another LLM API, provider-direct media APIs, remote renderers, or runtime
CDNs. Keep tokens, API keys, signed URLs, and private planning state out of
frontend state, run JSON, stdout, and stderr.
