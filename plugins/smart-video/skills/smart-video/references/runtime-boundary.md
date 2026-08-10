# Runtime Boundary

## Verified Current Status

The bundled npm runtime implements the `html-author`, `echarts-author`, and
runtime-readiness routes. Installed files alone are not execution proof: the
running loopback service must still pass the direct challenge below before a new
Slide is submitted.

Before any endpoint submission, run the `runtime-readiness` phase with the exact
loopback origin returned by `preflight`. The Skill validator creates a fresh
256-bit nonce and posts it directly to `/api/v1/runtime-readiness/attest`. The
running service must reject replay and return the same nonce, exact approved
routes and capabilities, its verified identity inventory, and the SHA-256 of the
identity file bytes. The Skill compares all fields with its pinned identity.

This is a local execution-readiness challenge, not cryptographic process identity.
It proves that the responding loopback service can read and verify the required
runtime files at challenge time. It does not defend against a hostile local
process with the same user privileges. Caller-authored reports, redirects,
non-loopback origins, copied hashes, missing routes, and mismatches are rejected
with `unsupported_render_runtime`.

The plugin exports Smart Video projects into a local FrameVideo project. It
does not import Podcastor at runtime.

## Local Components

- FastAPI listens only on a free `127.0.0.1` port.
- The launcher and `/api/v1/video-studio` share that origin.
- The plugin cache is immutable. Configuration, managed dependencies, and run
  state live under the current user's Smart Video home.
- Every new video receives a unique workspace below the configured data root.
  Reuse requires an explicit `--work-dir`.
- The npm-managed Studio editor binds an ephemeral loopback port. It defaults to
  English, can switch to Chinese, and may open an incomplete project for repair.
- Explicit `framevideo.mode:"checkout"` plus `framevideo.root` enables a source
  editor for development only.
- `bootstrap` installs the exact bundled first-party npm tarballs into a staged
  user runtime, verifies them, and activates them atomically. npm may resolve
  ordinary third-party dependencies. No developer checkout or first-party npm
  registry access is required.
- Local Media uses the managed macOS speech bridge or Windows Edge TTS plus
  offline ASR. Avatar generation always uses the authorized Jogg Task and
  Artifact APIs. The npm Avatar package is a remote driver only and includes no
  inference code or model. Preserved template resources remain independently
  replaceable and are not materialized by the runtime.

## Startup

Run `doctor`, then `bootstrap` only when dependencies are missing. `preflight`
starts the server and verifies `/health` and `/settings`; only after readiness may
the returned `settings_url` be shown. Never guess a loopback port before the
server is healthy.

## Required New Slide Author Endpoints

After `pre-adapter` validation and successful runtime readiness, a conforming
candidate runtime must submit a new Slide to exactly one dedicated loopback endpoint:

```text
PATCH /api/v1/video-studio/projects/{project_id}/shots/{shot_id}/html-author
PATCH /api/v1/video-studio/projects/{project_id}/shots/{shot_id}/echarts-author
```

The HTML body contains `request`, `manifest`, exact `author_html`, and optional
single-file `adapter_path`. The ECharts body contains `request`, `manifest`, exact
`author_json`, and optional `adapter_path`. The request identity must match the
target shot and clip. Use the returned `generation_manifest`; do not reconstruct
its adapter record. The endpoints reject hash, identity, render-mode, and root
linkage errors and never call the legacy recipe routes.

The trusted renderer identity is pinned by
`assets/runtime/trusted-runtime-identity.v1.json`. Post-render evidence is accepted
only when the readiness challenge matches that identity and the trusted render
report binds the author, adapter, screenshot, final timeline time, and observed root. The
observed root must come from the adapter page and include zero browser runtime,
console, network-load, and HTTP-response failures. ECharts capture also retains
complete text geometry with zero clipped labels and zero overlapping label pairs.
A mismatch is `unsupported_render_runtime`, not a reason to switch authoring paths.

## Allowed Requests

- Jogg OAuth2/OIDC and `/plugin/v1` through `JoggPluginClient`.
- Pexels search/download only with configured BYOK and requested material.
- FrameVideo Studio and renderer on loopback/local filesystem.
- Package/browser installation during explicit `bootstrap`.

## Forbidden Requests

- Jogg Web Controllers, `/v2`, `X-Api-Key`, or provider-direct requests.
- Podcastor remote API or source-repository imports.
- Another render worker, cloud object store, external LLM, or remote renderer.
- Runtime JavaScript or font CDNs.

## Checkpoints

Run state may store project/shot/Task IDs, compatibility Operation or Artifact
IDs, local paths, FrameVideo fingerprint, stage, work ID, and local result URLs.
It must not store bearer/refresh tokens, API keys, provider URLs, Task URLs,
signed upload targets, or process command lines.

Existing Task IDs, downloaded audio, retained avatar video, approved HTML, and
local work ID are authoritative. Missing downstream local artifacts may be
rebuilt, but paid Jogg work is never resubmitted automatically. Editor access is
independent of media completeness; final MP4 export remains strict.
