# Runtime Boundary

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
