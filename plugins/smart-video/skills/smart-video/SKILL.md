---
name: smart-video
description: Use when the user asks to create, continue, inspect, edit, preview, import, or render a long-form Smart Video or Video Studio video with Jogg voices, talking avatars, B-roll, HTML/MG, subtitles, BGM, or a local MP4.
---

# Smart Video

Operate the npm-managed local Smart Video Studio and SmartVideo runtime. Use `smart-video.sh`
on macOS and `smart-video.cmd` on Windows. Users choose only Jogg OAuth or Local Media.
Extract a required topic/source brief and `duration_seconds`; convert minutes to seconds and default to `180`.

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

1. On first use or after an update, invoke `doctor`. If it reports
   `dependencies_missing`, run `bootstrap`. Normal lifecycle commands never
   install host software. Do not present the deprecated `install-deps` alias.
2. Always invoke `preflight` before planning or `run`. It starts the loopback
   service and verifies `/health` and `/settings`. Use only the returned `settings_url`.
   Never construct, guess, or report a loopback URL before readiness.
3. Invoke `workspace` and use its new `workspace_dir`. Reuse a directory with
   `--work-dir` only when the user explicitly requests that existing workspace.
4. Generate and show only the compact Brief. Save it in the workspace and wait
   for confirmation or a natural-language revision; do not generate the hidden
   outline before confirmation.
5. After Brief confirmation, generate the hidden outline and semantic shot
   skeleton, then generate narration, shot strategy, B-roll intent, and Slide
   semantics in section batches. Show the complete Storyboard and wait for
   confirmation or shot-level edits. For every shot, show its number and title,
   user-facing type, planned duration, and complete narration script. After all
   shots, show `Subtitles: No / Yes`, defaulting to
   `No`. Titles, summaries, section names, or shot counts alone are not a complete
   Storyboard and must not be presented for formal confirmation.
6. Persist the confirmed private planning bundle, prompt log, public plan, and
   revision state under the workspace `plans` directory. Derive the top-level
   format from the actual shots; each internal `shot_type` remains authoritative.
7. Invoke `run` with `--planning-file` and `--work-dir`. An HTML/MG plan stops at
   `waiting_html` before project creation or paid media submission.
8. For each pending clip, read its complete `authoring_context`, create one asset,
   then call `apply-html` or `apply-echarts`. The command runs deterministic text
   fitting, captures one meaningful frame, and auto-approves when all hard gates pass.
   A failed clip remains retryable and must not prevent authoring later clips.
9. After every required clip is approved, call `resume` once. When the selected
   backend is Jogg and the plan has Avatar shots, it stops at
   `waiting_avatar_confirmation` before any paid media submission. Open the
   returned `editor_url`; after Jogg login, use the npm-managed Studio editor's existing
   `Avatar` and `Voice` tabs to preview and choose one of each. The choices are
   saved to the current project without opening another page or overlay. Call
   `resume` again. Local Media uses its configured local profile
   and skips this checkpoint because it has no selectable Avatar catalog.
   A profile-only replacement must not change scripts, Slides, or shot timing.
   Runs without Avatar shots skip this checkpoint. After confirmation, the same
   command continues TTS, Avatar, B-roll, subtitles, and local project creation
   from saved checkpoints.
10. Use `preview` or the returned `editor_url` for review and editing. The editor
    may open an incomplete project; missing media must not block inspection, while
    final output remains strict.
11. Invoke `render` for the local MP4.

Use the host-appropriate launcher. macOS examples:

```bash
bash "<plugin-root>/scripts/smart-video.sh" preflight
bash "<plugin-root>/scripts/smart-video.sh" workspace
bash "<plugin-root>/scripts/smart-video.sh" run \
  --topic "人工智能如何改变制造业" \
  --duration-seconds 180 \
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
when no separate title exists:

```text
### Shot 03 - Why the Old Method Fails
Type: B-roll + Slide
Duration: 18s
Script: The traditional process creates three separate handoffs...
```

After the last shot, show:

```text
Subtitles: No

You can confirm the Storyboard or change any shot's type, duration, or script.
```

If any required field is missing, complete the display before requesting
confirmation. After a natural-language shot edit, redisplay the complete updated
Storyboard and wait for confirmation again. Users never need to inspect or edit JSON.
Keep visual intent, visual segments, search intent, and Slide semantics private for
the Skill's planning and production workflow; do not include them in the public Storyboard.

## Planning Boundary

The planning sequence is fixed:

```text
Brief -> hidden outline -> per-shot script and strategy -> HTML-ready gate
-> semantic scene -> information-object plan -> one visual candidate
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
plan. `run` preflights this contract before project creation. Fix a reported JSON
path and retry with the same workspace; never bypass the preflight.

Every shot needs topic-specific narration and render intent. Any internal
`avatar_html`, `broll_html`, or `html_only` shot must contain its enabled Slide
contract. The top-level format is only a summary (`mixed` when needed) and never
rewrites per-shot types. Never start media generation from a missing or
contradictory plan.

The plugin workspace owns the planning file and revision state. Codex writes the
confirmed public plan into that workspace and passes the saved path to `run`; users
must never be asked to create or edit `production-plan.json` themselves. A missing
planning file remains a resumable `blocked_planning` safety state.

For a new information-layer clip, choose its semantic scene from the authorized
claim, evidence, entities, relations, structured data, and communication task.
Choose exactly one mapped visual candidate and persist the complete current
director contract with a stable clip ID. The reference supplies visual grammar,
not sample copy or facts. Use ECharts only when that selected candidate supports
it and a deterministic chart is the clearer expression.

## HTML Checkpoint

The per-clip `authoring_context` is authoritative. Read its exact story contract,
screen slots, ratio-specific reference hash/path, composition, prompt,
background rule, timing, and template audit fields before writing the asset. Do
not reselect its scene, reference, palette, or content. Full reference HTML stays
private and strict assets are materialized locally from the compact patch.

Visible copy comes only from `screen_slots`. Strict clips submit only the compact
replacement patch and never recreate HTML, CSS, SVG, geometry, or motion. An
adaptive `visual_recompose` clip may author one complete local HTML/CSS/inline-SVG
asset from the compiled information objects. Automatic capacity recompose remains
anchored to the selected reference and carries no free-generation style. A
separate free-generation style is allowed only after explicit user selection and
must never be inferred from template failure.
Never copy sample words, names, numbers, dates, sources, or facts from a reference.
ECharts clips use a pure JSON spec through `apply-echarts`; do not author chart
HTML or JavaScript.

Post-planning blocking checks are deliberately small: unsafe or malformed output,
missing generated-root identity, renderer failure, blank capture, or missing
approval. Composition, copy, fit, style, and motion reports guide inspection but
do not create a second semantic gate. Reapplying an asset clears that clip's old
captures. A normal resume never regenerates approved clips.

## Media And Recovery

When no backend is selected, Settings must ask the user explicitly to choose
Jogg OAuth or Local Media. Jogg remains preferred when connected. Local Media is
valid only before a Jogg submission and uses the managed local TTS, ASR, and
avatar components. Never infer a developer checkout or silently switch an
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
| New MG selection | [visual-reference.md](references/visual-reference.md) | None |
| Pending clip authoring | [html-authoring.md](references/html-authoring.md) | [echarts-authoring.md](references/echarts-authoring.md) and [echarts-options.md](references/echarts-options.md) for a chart clip |
| Jogg request or recovery | [jogg-task-lifecycle.md](references/jogg-task-lifecycle.md) | [jogg-api.md](references/jogg-api.md) for exact request shapes |
| Runtime, setup, security | [runtime-boundary.md](references/runtime-boundary.md) | None |
| Imported legacy recovery | Runtime compatibility only | Never load a separate legacy reference for a new clip |

## Boundaries

Use only the pinned npm-managed loopback runtime. Business network access is limited to
Jogg and explicitly configured Pexels requests. Never call Podcastor, Hermes,
COS, another LLM API, provider-direct media APIs, remote renderers, or runtime
CDNs. Keep tokens, API keys, signed URLs, and private planning state out of
frontend state, run JSON, stdout, and stderr.
