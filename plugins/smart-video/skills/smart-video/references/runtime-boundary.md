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

The current runtime requires semantic scene and template locators to create an
HTML checkpoint. For new MASTER-driven Slides, planning must set
`visual_recompose`, `fallback_automatic:false`, and
`free_generation_selected:true`, producing `full_html_recompose_v1`. The template
is not a visual source in this mode.

`apply-html` accepts a full custom Slide object for an ordinary HTML/SVG
checkpoint. A new ECharts Slide has no such checkpoint: the Skill must attach its
declarative spec as `shot.html_design.echarts_mg_spec` before `run`, and the
runtime injects the trusted local ECharts adapter during project creation.
`apply-echarts` is only for an existing registered checkpoint in a historical
run. Do not invent new author endpoints or require capabilities that are absent
from the installed npm.

## Avatar Targeting

New production uses `--avatar-mode planned`. The runtime derives the exact Avatar
shot set from `avatar_only`, `avatar_broll`, and `avatar_html`, regardless of
position or adjacency. It independently derives B-roll and Slide targets from
their corresponding `shot_type` values. Historical import may continue to use
legacy modes, but those modes must not constrain a new Storyboard.

The confirmed Storyboard is the planning authority. Runtime normalization must
preserve its shot IDs, order, count, types, and durations. `production_format`
only advertises whether the legacy renderer needs Slide capability: `broll_html`
when any Slide exists, otherwise `broll`.

The runtime must consume the confirmed `aspect_ratio` for canvas dimensions,
Slide capture, B-roll orientation/crop, Avatar generation, captions, preview, and
rendering. It must also consume optional `avatar_placement` on `avatar_html` and
`avatar_broll`; absence means default lower-right. Legal ratios and positions are
executed directly rather than blocked or substituted. Slide avoidance is design
guidance and must not become a hard runtime rejection gate.

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
