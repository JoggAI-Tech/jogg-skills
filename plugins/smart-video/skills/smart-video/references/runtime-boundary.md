# Runtime Boundary

The installed npm packages are the execution layer. This Skill does not replace,
patch, or bypass them.

## Ownership

The Skill owns:

- Brief, script, shot strategy, and public Storyboard;
- B-roll retrieval intent;
- Communication Intent and Visual Intent;
- the whole-video UI UX Pro Max MASTER;
- direct HTML/CSS/inline SVG or declarative ECharts authoring.

The npm runtime owns:

- local service startup and settings;
- planning projection and checkpoint state;
- Jogg, local speech, Avatar, and B-roll execution;
- `apply-html` validation plus pre-run ECharts validation and materialization;
- Avatar/B-roll/Slide layer order and opacity application;
- timeline assembly, editor state, preview, and final render.

## Local Components

- The service and editor bind loopback ports.
- Configuration, managed dependencies, and run state live outside the immutable
  plugin cache.
- Every new video uses a unique workspace unless the user explicitly requests an
  existing one.
- `bootstrap` installs the bundled first-party packages and their ordinary
  dependencies into the managed user runtime.
- The Skill's private UI UX Pro Max MASTER builder is local and uses no network.

## Slide Compatibility

The runtime requires a semantic scene to describe information structure. An
ordinary MASTER-driven Slide sets `visual_recompose`,
`fallback_automatic:false`, and `free_generation_selected:true`, producing
`direct_slide_html_v1`. It has no visual-template locator or template-derived
authoring context. ECharts may retain one compact scene-owned layout hint.

`apply-html` accepts a full custom Slide object for an ordinary HTML/SVG
checkpoint. A new ECharts Slide has no such checkpoint: the Skill must attach its
declarative spec as `shot.html_design.echarts_mg_spec` before `run`, and the
runtime injects the trusted local ECharts adapter during project creation.
`apply-echarts` is only for an existing registered checkpoint in a historical
run. Do not invent new author endpoints or require capabilities that are absent
from the installed npm.

## Avatar Targeting

The current npm command surface exposes only `none`, `opening`,
`opening_closing`, and `all`. These select no shots, the first shot, the first and
last shots, or every shot; they do not derive targets from `shot_type`.

Before `run`, compare the mode's exact target set with the shots typed
`avatar_only`, `avatar_broll`, or `avatar_html`. Use the first exact match in the
canonical order `none`, `opening`, `opening_closing`, `all`, and pass that mode
explicitly through `--avatar-mode`. A mismatch is
`unsupported_avatar_targeting` and must stop before any paid request. Do not use a
broader mode, mutate run state, remove generated Avatar assets later, or claim the
result validates the planned shot types.

## Network

Allowed network activity is limited to the runtime's configured Jogg OAuth and
`/plugin/v1` APIs plus configured B-roll providers. FrameVideo Studio and render
operations stay on loopback or local files.

Do not call provider-direct APIs, Jogg Web controllers, `/v2`, external LLMs,
remote renderers, font CDNs, or runtime JavaScript sources.

## Recovery

Run state may store project, shot, Task, Artifact, compatibility operation, local
media, and work IDs. It must not expose tokens, provider URLs, signed URLs, or
process command lines.

Existing Task IDs, idempotency keys, downloaded media, approved Slides, and local
work IDs are authoritative. Resume known work and never resubmit paid media
automatically. The editor may open an incomplete project; final rendering remains
strict.
