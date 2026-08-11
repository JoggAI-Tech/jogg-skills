# Smart Video 0.8.12 Installation

Smart Video supports macOS and Windows from one plugin. The plugin contains its
Skill documents, authoring references, and branding. Runtime code is installed
from pinned public npm packages; optional Avatar resources are downloaded to the
user-managed Smart Video directory only when requested.

## User Flow

1. Run the read-only `doctor` command.
2. Run the returned `bootstrap` command when dependencies are missing.
3. After updating the plugin, run `upgrade` once and then `doctor`.
4. Open the verified Settings URL and authorize Jogg, or select Local Media for
   TTS/ASR-only workflows.

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
| Avatar generation | Authorized Jogg Task API | Authorized Jogg Task API |
| Local MP4 rendering | Yes | Yes |

macOS and Linux bootstrap use the verified official Node.js distribution;
macOS uses the FFmpeg build recommended by FFmpeg's official download page.
Windows bootstrap uses `winget` and Git Bash. The exact Node.js minimum comes
from `runtime-bom.json`; this release requires Node.js 22+, Python 3.10+,
Google Chrome, `jq`, and FFmpeg with `libx264`, AAC, VP9, and subtitles support.

The published `@joggai/smartvideo-avatar` package contains only the remote Jogg
driver and task contracts. It does not contain local Avatar inference code,
models, or Python dependencies.

When the editor reports missing local Avatar resources, open
`https://docs.jogg.ai/avatar-resources` and choose a presenter, or run one of:

```bash
npx --yes @joggai/smartvideo@latest resources install classroom-presenter
npx --yes @joggai/smartvideo@latest resources install office-presenter
```

The installer verifies the resource archive and activates it below
`~/.codex/smartvideo/resources/avatar-packs/`. Plugin upgrades do not remove it.

Developers may override the registry package spec with
`SMARTVIDEO_PACKAGE_SPEC`. Normal users do not configure this variable or any
source checkout path.
