# Smart Video 0.8.21 Installation

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
`<selected-root>/node-runtime/releases/`, verifies the full package set,
and atomically updates `active-runtime.json`. An interrupted installation does
not replace the prior active runtime.

When Node.js is missing or older than `runtime-bom.json#minimum_node`, macOS and
Linux bootstrap download the matching official binary release directly from
`https://nodejs.org/dist/`. The installer verifies the archive against Node.js'
official `SHASUMS256.txt`, then activates it under
`<selected-root>/node/current`. It does not require Homebrew, sudo, or a
system-wide Node installation. Existing managed Node versions remain available
until a later cleanup, so an interrupted upgrade cannot remove the active one.

On macOS, FFmpeg is also managed without Homebrew. Bootstrap installs a pinned,
SHA-256-verified static build from the macOS provider linked on
`https://ffmpeg.org/download.html`, then activates `ffmpeg` and `ffprobe` under
`<selected-root>/bin`. Existing compatible FFmpeg binaries are reused.
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

## Data Directory And Sandbox Access

The plugin automatically detects the operating system and selects storage in
this order:

1. A nonempty `SMARTVIDEO_HOME` override. An inaccessible explicit path reports
   an error rather than selecting another directory.
2. The nearest existing `.smartvideo` directory in the current working directory
   or its ancestors. This keeps an initialized workspace on the same data root
   when commands run from project subdirectories or Home permissions change.
3. The system user directory, when accessible: `%USERPROFILE%\.codex\smartvideo`
   on Windows, or `$HOME/.codex/smartvideo` on macOS/Linux. Windows uses `HOME`
   only when `USERPROFILE` is unavailable; native and Git Bash paths are converted
   automatically.
4. `<current-working-directory>/.smartvideo` when the system user directory is
   unavailable. The launcher checks access and reports the selected path. It
   never chooses a directory inside the plugin installation for automatic storage.

Run commands from the intended writable Codex workspace. The launcher does not
assume that a particular Documents folder is authorized, inspect Codex's private
settings, or change sandbox permissions. `CODEX_HOME` does not select Smart Video
storage. No environment variable is needed for the normal automatic flow:

```powershell
& "<plugin-root>\scripts\smart-video.cmd" doctor
& "<plugin-root>\scripts\smart-video.cmd" bootstrap
& "<plugin-root>\scripts\smart-video.cmd" preflight
```

Or in Git Bash:

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
bash "<plugin-root>/scripts/smart-video.sh" preflight
```

Before the first write command, use the same working directory for `doctor` and
`bootstrap`: a read-only `doctor` does not create a workspace directory to persist
its selection. After initialization, the existing `.smartvideo` directory makes
selection stable from that workspace and its subdirectories. Commands from an
unrelated directory need an explicit `SMARTVIDEO_HOME` pointing to the same root.
Add the workspace's `.smartvideo/` directory to its local ignore rules when using
version control; it contains local runtime and project data.

For a specific location, optionally set an absolute path, for example:

```powershell
$env:SMARTVIDEO_HOME = Join-Path $env:USERPROFILE "Documents\Codex\.smartvideo"
```

When using an override, keep the same value for every subsequent command, including
`settings`, `workspace`, `run`, `resume`, `render`, and `upgrade`. A shell-local
assignment does not configure other terminals or later Codex command processes;
set it in each invocation or in the environment inherited by the Codex session.
Selecting a different root creates a separate installation and data tree. It does not move old
projects or reconnect an already running service to the new directory. Stop the
old service before switching roots; retain the original directory for existing
runs. Existing absolute `paths.data_dir` and `paths.tool_dir` values in a copied
config must be reviewed because they continue to select their original paths.

The plugin routes the shell runtime through `--config <SMARTVIDEO_HOME>/config.json`
and uses the same root for npm packages and managed resources. An explicit
leading `--config <file>` overrides the config and its derived run/data paths;
it does not relocate npm packages or resources. Use `SMARTVIDEO_HOME` to select
the complete root. These examples use the plugin launcher, not a direct npm CLI
invocation, which may have a different default config in older runtime versions.

```text
<SMARTVIDEO_HOME>/
  config.json
  active-runtime.json
  service.json
  node-runtime/releases/
  data/
  runs/
  logs/
  cache/
  resources/
```

Directories and files appear as their corresponding commands run. Merely
creating them manually does not grant subsequent read/write permission.
`smartvideo_storage_unavailable` identifies the directory whose access check
failed. Check OS permissions and the current Codex session's allowed filesystem
paths. The pinned npm runtime also creates the adjacent temporary
`<SMARTVIDEO_HOME>.migration.lock`, so authorizing only the root's contents may
be insufficient. Selecting a root inside an already authorized workspace covers
both locations. Custom config, data, or tool directories need their own access.
The launcher uses only permission checks for `doctor`; commands that write also
perform a temporary file probe. A write probe may discover a sandbox restriction
that was invisible to `doctor` and trigger automatic fallback. Explicit overrides
and existing workspace roots report an error if inaccessible. If neither the
default location nor the current workspace is writable, the launcher reports
`smartvideo_storage_unavailable`. The actual runtime operation may still detect
additional ACL or sandbox restrictions.

A filesystem permission failure does not establish an OAuth, Jogg MCP, API
Credits, or AppSumo plan entitlement problem. Running in another terminal only
helps when that terminal has access to the same selected directory; it does not
grant access to later sandboxed commands.

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
bash "<plugin-root>/scripts/smart-video.sh" resources install classroom-presenter
bash "<plugin-root>/scripts/smart-video.sh" resources install office-presenter
```

```powershell
& "<plugin-root>\scripts\smart-video.cmd" resources install classroom-presenter
& "<plugin-root>\scripts\smart-video.cmd" resources install office-presenter
```

The installer uses the same Avatar Engine npm package on macOS and Windows. It
installs the engine and shared driver in one staged release, bootstraps the
managed Python environment, verifies engine readiness, then verifies and
activates the Presenter archive below
`<selected-root>/resources/avatar-packs/`. Plugin upgrades do not remove it.
`SMARTVIDEO_AVATAR_ENGINE_ROOT` and
`SMARTVIDEO_AVATAR_ENGINE_MANAGED_ROOT` are developer overrides; normal users do
not configure them. A missing or invalid engine reports `driver_unavailable`
instead of treating the Presenter catalog as executable.

Developers may override the registry package spec with
`SMARTVIDEO_PACKAGE_SPEC`. Normal users do not configure this variable or any
source checkout path.
