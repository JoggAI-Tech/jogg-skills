# Smart Video 0.8.18 Installation

Smart Video supports macOS and Windows from one plugin. The plugin contains its
Skill documents, authoring references, and branding. Runtime code is installed
from pinned public npm packages; optional Avatar resources are downloaded to the
user-managed Smart Video directory only when requested.

## User Flow

1. Run the read-only `doctor` command.
2. Run the returned `bootstrap` command when dependencies are missing.
3. After updating the plugin, run `upgrade` once and then `doctor`.
4. Open the verified Settings URL and authorize Jogg, or select Local Media for
   local TTS, ASR, and an explicitly installed Avatar engine.

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
bash "<plugin-root>/scripts/smart-video.sh" upgrade
```

```powershell
& "<plugin-root>\scripts\smart-video.cmd" doctor
& "<plugin-root>\scripts\smart-video.cmd" bootstrap
& "<plugin-root>\scripts\smart-video.cmd" upgrade
```

`doctor` never changes the machine. `bootstrap` installs the pinned
`@joggai/smartvideo` package under
`~/.codex/smartvideo/node-runtime/releases/`, verifies the full package set,
and atomically updates `active-runtime.json`. An interrupted installation does
not replace the prior active runtime.

When Node.js is missing or older than `runtime-bom.json#minimum_node`, macOS and
Linux bootstrap download the matching official binary release directly from
`https://nodejs.org/dist/`. The installer verifies the archive against Node.js'
official `SHASUMS256.txt`, then activates it under
`~/.codex/smartvideo/node/current`. It does not require Homebrew, sudo, or a
system-wide Node installation. Existing managed Node versions remain available
until a later cleanup, so an interrupted upgrade cannot remove the active one.

On macOS, FFmpeg is also managed without Homebrew. Bootstrap installs a pinned,
SHA-256-verified static build from the macOS provider linked on
`https://ffmpeg.org/download.html`, then activates `ffmpeg` and `ffprobe` under
`~/.codex/smartvideo/bin`. Existing compatible FFmpeg binaries are reused.
Because the upstream-recommended macOS build is x86_64, Apple Silicon requires
Apple's Rosetta when no compatible native FFmpeg is already installed.

Smart Video never runs Homebrew. On macOS it reuses compatible Python 3.10-3.13,
`jq`, and Google Chrome installations. If Python or Chrome is missing,
bootstrap returns the official python.org or Google download URL; no package
manager or administrator-level package-manager setup is required by the plugin.

`upgrade` does not blindly install npm `latest`. It reads the updated plugin's
`runtime-bom.json`, installs that compatible aggregate release, verifies every
child package against its own pinned version, then atomically activates it.
Aggregate and child package versions are independent.

The packages do not use npm `postinstall`. Python environments, the Windows
Vosk model, and the compiled Apple speech bridge are created under the user's
Smart Video home only during explicit bootstrap. Project data is never stored
inside the plugin installation.

## Platform Support

| Capability | macOS | Windows |
| --- | --- | --- |
| Studio and Jogg OAuth | Yes | Yes |
| Local TTS | Apple speech | Edge TTS |
| Local Chinese ASR | Apple speech recognition | Vosk Chinese model |
| Avatar generation | Jogg API or managed local driver | Jogg API or managed local driver |
| Local MP4 rendering | Yes | Yes |

macOS and Linux bootstrap use the verified official Node.js distribution;
macOS uses the FFmpeg build recommended by FFmpeg's official download page.
Windows bootstrap uses `winget` and Git Bash. The exact Node.js minimum comes
from `runtime-bom.json`; this release requires Node.js 22+, Python 3.10+,
Google Chrome, `jq`, and FFmpeg with `libx264`, AAC, VP9, and subtitles support.

The published `@joggai/smartvideo-avatar@0.1.3` package contains the remote Jogg
task contracts and the local `avatar-engine` orchestration driver. The separate
`@joggai/smartvideo-avatar-engine@0.1.1` package contains the portable inference
source and encrypted model assets; its managed Python environment is created
outside `node_modules` only during explicit resource installation. Local Avatar
bootstrap accepts Python 3.10 through 3.13; set
`SMARTVIDEO_AVATAR_ENGINE_PYTHON` only when a compatible executable is not the
default `python3`.

When the editor reports missing local Avatar resources, open
`https://docs.jogg.ai/avatar-resources` and choose a presenter, or run one of:

```bash
npx --yes @joggai/smartvideo@0.1.11 resources install classroom-presenter
npx --yes @joggai/smartvideo@0.1.11 resources install office-presenter
```

The installer uses the same Avatar Engine npm package on macOS and Windows. It
installs the engine and shared driver in one staged release, bootstraps the
managed Python environment, verifies engine readiness, then verifies and
activates the Presenter archive below
`~/.codex/smartvideo/resources/avatar-packs/`. Plugin upgrades do not remove it.
`SMARTVIDEO_AVATAR_ENGINE_ROOT` and
`SMARTVIDEO_AVATAR_ENGINE_MANAGED_ROOT` are developer overrides; normal users do
not configure them. A missing or invalid engine reports `driver_unavailable`
instead of treating the Presenter catalog as executable.

Developers may override the registry package spec with
`SMARTVIDEO_PACKAGE_SPEC`. Normal users do not configure this variable or any
source checkout path.
