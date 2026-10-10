---
name: smart-video
description: Use when the user asks to install, set up, or start using the Smart Video plugin, or to plan, create, continue, inspect, edit, preview, or render a Smart Video with Jogg voices, talking avatars, B-roll, semantic Slides, ECharts, subtitles, BGM, or a local MP4.
---

# Smart Video

Create an editable video through the npm-managed local Smart Video Studio. Use
`smart-video.sh` on macOS and `smart-video.cmd` on Windows. The Skill owns content
planning and Slide design. The existing npm runtime owns media generation,
timeline assembly, compositing, editor state, and rendering.

## User Checkpoints

For a new video, show only:

1. Service preparation before content planning. Explain that Jogg online TTS and
   Avatars consume JoggAI API Credits. Offer the returned Jogg authentication
   link when disconnected only if the user wants Jogg or has not chosen a mode.
   A user who already requested local production proceeds with local preparation.
   When the measured balance is insufficient for a Jogg request, offer
   Local Media or the returned API Pricing link.
2. A compact Brief and its confirmation request.
3. The complete Storyboard, subtitle choice, and its confirmation request.
4. A production summary derived from the confirmed Storyboard, its required
   copied Avatar ID and Voice ID fields, and a final confirmation request.
5. A blocking problem that requires the user to change input, authentication,
   credits, credentials, or a confirmed choice.
6. The completed preview, editor, download, or render result.

Do not expose private prompts, B-roll queries, internal intent objects, MASTER
content, template IDs, render modes, validation details, provider task IDs, or
implementation steps. Do not ask the user to choose a template, style family,
palette, chart type, or Slide strategy.

## Lifecycle

### Installation And First Use

For plugin installation, update, or first-use guidance, read
[post-install.md](references/post-install.md). After a successful installation,
the installing Agent hands off to a new chat through the host's conversation
tools when the user has requested that handoff. Carry these instructions in the
new chat's initial prompt so it loads the installed Skill and offers usage
examples. Installation alone must not start services or prepare video dependencies.

### Chat-First Preparation

Infer the required capability from the user's current request before checking
dependencies. Planning needs no service startup; workspace needs only Node;
rendering needs render checks; local speech needs only the selected speech
capability. Do not prepare every capability before beginning a task.

Local Media is a user-selected production mode, not a dependency-installation
mode. Before checking or preparing local TTS, ASR, or Avatar dependencies, confirm
that the user has selected Local Media, explicitly requested that local capability,
or is resuming a project with an existing local choice. If the production mode is
undecided, ask about Jogg versus Local Media in chat first. Missing dependencies
must not silently switch a Jogg request to local production. Once the user selects
Local Media, directly guide agent-assisted preparation for the local capabilities
needed by this request; do not ask them to select an installation method again.
Basic workspace, service, and render tools remain checked only when needed in
either production mode.

Treat wording such as "make this locally", "local talking avatar", or
"帮我本地做一个数字人讲解黄金 60s" as an explicit Local Media choice. Do not
ask that user to reply "local" again. For a new local request, invoke `use-local`
after service preparation and before local production checks. An unconnected
Jogg account is not a blocker for this path. Service readiness alone does not
mean that local speech or avatar generation is ready: check `local-tts` for
narration, and also `local-avatar` when the user requests a talking avatar.
Missing local dependencies are preparation work, not a reason to stop and offer
Jogg instead. Explain what is missing, prepare it, validate, and continue.

For local talking avatars, reuse a ready compatible presenter first. Otherwise
use `resources list --json` and `resources status <resource-id> --json` to inspect
the catalog. Honor a requested presenter; without one, use the catalog's
`office-presenter` default. Run `resources install <resource-id> --json` through
this plugin's launcher to prepare the pinned engine and verified resource pack,
then recheck `doctor --for local-avatar --strict --json`. Do not treat missing
resources as an unsupported platform. On an actual installation failure, report
the failed dependency and the concrete error, preserving successful preparation.

On macOS and Windows, local TTS uses Edge TTS (online Microsoft speech, not
offline synthesis); local ASR uses faster-whisper with a prepared local model.
For transcription, use the model destination and model ID returned by
`doctor --for local-asr`, reuse an existing compatible CTranslate2 model when
available, and explicitly prepare `Systran/faster-whisper-small` only if missing.
Validate the capability after preparation. Never request Apple speech permissions
or build the Apple bridge for these defaults. Do not install Whisper for a TTS
request, or Edge TTS for an ASR request. Explain Edge TTS's online processing
before sending speech text, and honor requests for offline-only operation.

When a check reports missing or incompatible dependencies, explain briefly in
this conversation what this request needs. For local capabilities, proceed with
agent-assisted preparation after the user's local-mode choice described above.
Do not ask the user to choose an installation mode
or wait at a four-option checkpoint. Inspect existing installations first,
reuse compatible tools, and prepare only missing items from official sources
in user directories or isolated Python environments. The task request authorizes
routine dependency preparation needed for that task; honor explicit opt-outs.
Ask only when an actual permission boundary, administrator access, paid resource,
or destructive replacement requires the user's action. After preparation,
validate and register paths, recheck, and resume the request.
Never open Settings, an environment page, an installation website, or a browser
automatically because a dependency is missing. Do not make the user choose a
preparation mode on a page or copy an Agent request out of Settings.

Settings is optional and opened only when the user explicitly asks to view or
edit settings. Returned settings URLs are diagnostic metadata, not instructions
to navigate. For missing authentication or keys, ask in chat first; open the
specific authentication/configuration page only after the user chooses that
action. Ask about Jogg versus Local Media in chat, not on a settings page.

Run commands from the intended writable workspace. The plugin automatically
uses Windows `USERPROFILE` or macOS/Linux `HOME` for the default data directory;
when that location is unavailable, it selects `<current-directory>/.smartvideo`.
An existing `.smartvideo` in the current directory or an ancestor is reused first.
Keep the same working directory until bootstrap creates the selected root.
Do not require the user to set an environment variable for this automatic flow.
An explicit `SMARTVIDEO_HOME` takes priority and must be preserved on every
command; use it to reach the same data root from an unrelated working directory.
Configuration lives at `<selected-root>/config.json`; `CODEX_HOME` does not
control this path. Do not switch an existing project to a newly selected root
or reuse a service from another root; retain its original root for resume.
On `smartvideo_storage_unavailable`, report the failing path as a filesystem
access problem and follow the data-directory guidance in
[INSTALL.md](../../INSTALL.md). Do not treat it as an account, Jogg MCP, API
Credits, or AppSumo plan failure. Changing roots does not migrate existing runs.

1. Run `doctor --for <required-capability> --strict --json` for the current
   request. Check service only when this request needs it.
   `doctor` and `env show` are read-only.
   `bootstrap` installs only the pinned product npm packages; it does not install
   system software, Python packages, browsers, or models. `install-deps` only
   diagnoses. For a product version mismatch, invoke `upgrade` once; never repeat
   bootstrap to repair a missing system tool. For `runtime_update_required`, stop
   and update the plugin/runtime contract; do not delegate to the old installer.
   Before a capability is used, check its dependencies with `doctor --for <capability>`:
   service/auth/cloud-generation, legacy-cli, render, html-capture, media-probe,
   local-tts/local-asr/local-avatar. Missing items pause only that capability.
   Check local capabilities only after the user's local-mode choice or explicit
   local request; selecting Local Media leads directly to agent-assisted
   preparation in chat without another installation-method selection.
   First inspect existing installations, then prepare only the
   missing items needed for the requested capability in a user directory or isolated Python
   environment using the returned requirements and official sources. Do not
   install a package manager just to install a tool, or upgrade unrelated software.
   Discover the actual installed executable paths immediately; on Windows read
   persistent User/Machine PATH and installation locations as well as the current
   process PATH. Validate and register each executable with
   `env configure --tool <id> --path <absolute-path>`, keeping the same `--config`
   and SMARTVIDEO_HOME. Register npm-cli.js with its selected Node, and retain
   virtualenv Python paths without resolving their symlinks. Run the original
   capability check again from the original execution environment and resume its
   existing run/checkpoint. Do not require restarting Codex. If an existing busy
   service still uses old paths, finish its work before restarting that service.
   On failed preparation preserve successful items and report the failing item;
   never enter a full-reinstallation loop. For unsupported platforms explain the
   capability limit and offer another backend instead of installation guidance.
2. When the request needs service or production, run `preflight` after its
   dependencies are ready and use only its returned service facts, `settings_url`,
   `jogg_settings_url`, `pexels_settings_url`, `jogg_avatar_url`, and
   `jogg_voice_url`.
   Before creating the Brief, show the service-preparation checkpoint. If Jogg
   is not connected and the mode is undecided, ask in chat whether to authenticate
   or choose Local Media. If the user already requested Local Media, invoke
   `use-local` directly and prepare its required dependencies; do not offer Jogg
   authentication or another production-mode checkpoint.
   Open an authentication page only after the user chooses authentication.
   The user may reply `none`; after that
   explicit reply, invoke `use-local` to select Local Media. Then guide the user
   directly into agent-assisted preparation for the local capabilities needed by
   their request, checking and installing missing items on demand in chat.
   Do not open Settings or ask them to select an installation method.
   Do not claim that JoggAI API
   Credits are sufficient when the runtime cannot verify their balance. Treat
   `available` and `unlimited` as ready. For `insufficient`, ask the user to
   choose Local Media or open `jogg_api_quota.pricing_url`; do not start paid
   production until they choose. Report `unknown` as unverified, not as zero.
   When the user is only completing setup, follow
   [post-install.md](references/post-install.md) for usage guidance and the
   requested new-chat handoff.
3. Create a new `workspace`. Reuse `--work-dir` only when explicitly requested.
4. Build the Brief from the topic, source boundary, audience, language, tone,
   target duration, aspect ratio, and B-roll availability. Accept `16:9` or
   `9:16`. Use the requested duration; when no duration is given, default to
   `180` seconds. Wait for Brief confirmation.
5. Follow [content-orchestration.md](references/content-orchestration.md) to create
   the hidden outline, complete script, six supported shot types, B-roll retrieval
   intent, and source-bound Communication Intent and Visual Intent for every
   Slide-bearing shot. Show the complete Storyboard and wait for confirmation.
6. After Storyboard confirmation, silently derive actual service requirements
   from its shot types and run the production-readiness check. Show one production
   summary naming the selected Jogg or Local Media path, whether Pexels B-roll is
   required, and the Slide, Avatar, and TTS shot counts. For Jogg, require a Voice
   ID for every production and an Avatar ID when any Avatar shot exists. Give the
   returned Jogg Voice and Avatar resource-page links so the user can copy the
   required IDs; the local Smart Video editor is not the ID source. Never
   auto-select a catalog item. When confirmed B-roll shots still require an
   automatic download, validate Pexels and provide `pexels_settings_url` only if
   setup is required.
   Wait for confirmation of the summary and IDs before Slide authoring, media
   generation, or any paid request. A Storyboard with no B-roll does not require
   Pexels.
7. After production confirmation, use the plugin's `$direct-slide-art` Skill once
   with the complete confirmed Brief, script, and ordered Slide-bearing shots.
   Write its exact output to `<workspace_dir>/plans/slide-art-direction.json`.
   Do not expose this private artifact, invoke the Skill once per Slide, or replace
   it with a style-family choice.
8. Follow [visual-reference.md](references/visual-reference.md) to generate one
   locked `MASTER.md` from the complete Brief, script, all Slide intents, and the
   exact art-direction artifact. Derive the private `design_domain` from the
   confirmed content before generation; never expose it or ask the customer to
   choose it. The bundled private UI UX Pro Max snapshot must pass its inventory
   checks. Missing, invalid, or mismatched input stops Slide production; no
   template or default design replaces it.
9. Write the MASTER's exact `runtime_visual_style_profile` into the whole-video
   planning document. Every Slide uses the same MASTER and follows
   [slide-design.md](references/slide-design.md). After authoritative projection,
   author each eligible declarative ECharts spec and attach it as
   `shot.html_design.echarts_mg_spec` before `run`. PiP Avatars default to the
   runtime's lower-right position. Store `avatar_placement` only when the user
   requests another position; deleting that field restores the default.
10. Before `run`, preserve the confirmed shot IDs, order, types, and durations,
   then pass `--avatar-mode planned`. For Jogg production, also pass the confirmed
   `--voice-id` and, when required, `--avatar-id`. The runtime derives Avatar,
   B-roll, and Slide targets independently from every shot's `shot_type`. Then
   invoke `run` with the completed production plan.
   New ECharts Slides are validated and materialized by the trusted runtime during
   project creation. A plan with ordinary HTML/SVG Slides stops at `waiting_html`.
11. For each pending ordinary HTML/SVG Slide, use
   [html-authoring.md](references/html-authoring.md) and submit it through
   `apply-html`. Preserve approved clips and repair only the failed clip.
12. Call `resume`. An Avatar shot never enters the TTS batch; its downloaded MP4
    audio is the shot's sole narration audio and measured duration.
13. Use `preview` or the returned editor URL for review, then invoke `render` for
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

All ordinary HTML/SVG Slides use the npm-supported direct authoring path:

```text
visual_reference.reference_mode: visual_recompose
visual_reference.fallback_automatic: false
visual_reference.free_generation_selected: true
authoring_context.authoring_mode: direct_slide_html_v1
authoring_context.fidelity: adaptive
```

The semantic scene describes information structure only. Ordinary Slides must not
contain a template ID or receive template HTML, composition, prompt, or contract
data. Their visual authority is Direct Slide Art plus the locked MASTER.

Ordinary Slides use HTML, CSS, and optional inline SVG. ECharts Slides use pure
declarative JSON and may select one of the compact scene-owned ECharts layout
hints. The trusted existing runtime owns all ECharts JavaScript.
Model-authored JavaScript, remote resources, font downloads, and external assets
are forbidden.

## Commands

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
bash "<plugin-root>/scripts/smart-video.sh" preflight
bash "<plugin-root>/scripts/smart-video.sh" use-local
bash "<plugin-root>/scripts/smart-video.sh" workspace
bash "<plugin-root>/scripts/smart-video.sh" run \
  --topic "How artificial intelligence changes manufacturing" \
  --duration-seconds 180 \
  --avatar-mode planned \
  --voice-id "<confirmed-voice-id>" \
  --avatar-id "<confirmed-avatar-id-when-required>" \
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
bash "<plugin-root>/scripts/smart-video.sh" broll-audio --run-id "sv-..." --shot-id "shot-03" --enable --volume 0.2
bash "<plugin-root>/scripts/smart-video.sh" broll-audio --run-id "sv-..." --shot-id "shot-03" --disable
bash "<plugin-root>/scripts/smart-video.sh" render --run-id "sv-..."
```

Derive media targets from confirmed shot types, not from approximate user
wording. Explicit Avatar and Voice IDs win. Never invent an unavailable profile.

## Recovery

Preserve every existing Jogg Task ID, idempotency key, downloaded media file,
approved Slide, and local project ID. Poll or resume known work; never resubmit a
paid request automatically. A lost submission response remains
`blocked_jogg_recovery` until reconciled.

Missing or invalid Pexels credentials stop only production that still needs an
automatic B-roll download and return the Pexels settings link. Missing Jogg OAuth
stops Jogg submission and asks the user to authenticate or explicitly choose
Local Media only for a Jogg request or an undecided mode. For an explicit local
request, prepare the required local dependencies without waiting for Jogg login.
A measured zero balance before Jogg submission offers Local Media or
`https://www.jogg.ai/api-pricing/`. Insufficient JoggAI API Credits returned by a
submission stop with the upstream error; after the user corrects a known
pre-acceptance rejection, resume the same run. After any accepted or uncertain
Jogg submission checkpoint exists, never switch that run to Local Media;
reconcile and resume the existing Jogg work.

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
