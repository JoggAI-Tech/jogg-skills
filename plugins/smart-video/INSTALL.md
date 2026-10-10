# Smart Video Installation

The plugin installs only its pinned product npm packages. System software,
Python packages, browsers, speech bridges, and models are prepared only for the
capability the user chooses. There is no automatic winget, Homebrew, apt, pip,
browser download, or model download in ordinary startup and rendering commands.

## Preparation Flow

After plugin installation, follow the bundled
[installation handoff and usage guidance](skills/smart-video/references/post-install.md).
The installing Agent opens the requested new chat through host tools. Onboarding
does not require product bootstrap or system dependency preparation.

1. Run `doctor --for service --strict --json`.
2. If Node is missing for the current request, the Agent first searches existing
   installations, then prepares Node from https://nodejs.org/en/download. Set
   `SMARTVIDEO_NODE_BINARY` to the validated absolute path for the initial
   launcher invocation. Windows also reads persistent User/Machine PATH and
   existing Node installation locations, so restarting Codex is unnecessary.
3. If the product runtime is missing, `bootstrap` installs and verifies the
   pinned npm BOM in a staging directory before activating it.
4. Explain missing dependencies in chat and default to Agent preparation without
   an installation-mode selection. Search for compatible existing software and
   prepare only items needed by the current request from official sources,
   preferably in user directories and virtualenvs. Honor explicit opt-outs;
   ask for actual administrator access, paid resources, or destructive replacement.
5. Register each validated executable with `env configure`, rerun the original
   capability check, and continue the existing task/checkpoint.
6. Run `preflight` only when the task needs service facts. Returned Settings URLs
   do not authorize opening a page; ask about authentication in chat first.

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor --for service --strict --json
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
bash "<plugin-root>/scripts/smart-video.sh" env configure --tool service_python --path "/absolute/venv/bin/python"
bash "<plugin-root>/scripts/smart-video.sh" doctor --for render --strict --json
```

```powershell
& "<plugin-root>\scripts\smart-video.cmd" doctor --for service --strict --json
& "<plugin-root>\scripts\smart-video.cmd" bootstrap
& "<plugin-root>\scripts\smart-video.cmd" env configure --tool service_python --path "C:\SmartVideoBeta\venv\Scripts\python.exe"
& "<plugin-root>\scripts\smart-video.cmd" doctor --for render --strict --json
```

The Node CLI handles doctor, env, workspace, settings, and preflight directly.
These commands do not require Bash, jq, curl, FFmpeg, or a browser unless the
requested capability needs them. Production orchestration still uses Bash/jq/curl;
on Windows only that legacy capability requires Git for Windows Bash.

`bootstrap` prepares product directories/packages and diagnoses the service.
`install-deps` is a diagnosis-only compatibility command.
`upgrade` installs the new pinned product BOM and diagnoses the service.
They never install or upgrade system software.

## Capability Checks

| Capability | Environment checked |
| --- | --- |
| product-install | Node and its npm-cli.js |
| service / auth / cloud-generation | Node, Python 3.10+, base service requirements |
| legacy-cli | Node, Bash, jq, curl |
| workspace | No external tools beyond the running Node |
| media-probe | ffprobe |
| html-capture | Node and a headless browser that can launch |
| render | Service environment, browser, FFmpeg encoders/filters, ffprobe |
| local-tts / local-asr / local-avatar | Selected local dependencies and supported platform |

`doctor` reports facts without installing anything. `--strict` returns
0 for ready, 2 for missing/incompatible dependencies, 3 for an unsupported
platform, and 4 for invalid configuration. Explicit invalid paths report a
path error instead of silently falling back. Successful browser detection
requires rendering a small headless page, not merely finding a file.

The Settings environment panel offers official links, an Agent preparation
request, path registration, and rechecking. Agent assistance copies a request
for the existing Codex conversation; the page does not run a system installer.

## Executable Paths

Use `env show` to inspect selected paths without exposing API keys.
`env configure --tool <id> --path <absolute-path>` validates the executable before
saving `config.json#tools`. Supported IDs are node, npm_cli, bash, jq, curl,
python, service_python, ffmpeg, ffprobe, and browser.

Windows npm uses the selected Node to execute npm-cli.js, avoiding npm.cmd
launch problems. Preserve virtualenv Python symlinks. Tools may live in paths
with spaces; processes use argument arrays. Paths must be valid in the actual
execution environment: native Windows, Git Bash, WSL, and Linux are distinct.

The service, media commands, sidecar, and renderer use the registered paths.
A child's PATH also includes tool directories when a downstream library needs
command lookup. An entire installation-time PATH snapshot is never saved.
Path changes affect new operations; finish active production before restarting
a service whose own interpreter changed. Moving/uninstalling a registered tool
produces a repair prompt on its next check.

## Data Directory

An explicit `--config <file>` selects that config's parent as the complete root.
Otherwise selection is: explicit SMARTVIDEO_HOME, nearest existing workspace
`.smartvideo`, accessible user `.codex/smartvideo`, then workspace `.smartvideo`.
An inaccessible explicit root is an error. Automatic storage never uses the
plugin installation. Use the same root and working directory throughout setup;
doctor does not create a workspace directory to persist its selection.

```text
<selected-root>/
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

The same root owns product packages, config, resources, and task state. Changing
roots does not migrate existing runs. Keep old roots for resume operations.
Authorize both the root and its adjacent migration lock in sandboxed sessions.
A storage permission error is a local filesystem failure, not a Jogg account
or API Credits problem. Add workspace `.smartvideo/` to local ignore rules.

Node and Python merge config changes under the same `config.json.write.lock`
and atomically replace the file, retaining tool registrations and other settings.

## Optional Preparation And Platform Limits

Official software sources: [Node.js](https://nodejs.org/en/download),
[Python](https://www.python.org/downloads/),
[Git for Windows](https://git-scm.com/downloads),
[jq](https://jqlang.org/download/), [curl](https://curl.se/download.html),
[Chrome](https://www.google.com/chrome/), and
[FFmpeg / ffprobe](https://ffmpeg.org/download.html).

Base Python requirements are shipped at `runtime/backend/requirements.txt`.
macOS and Windows Edge TTS and faster-whisper requirements are separate files
`requirements-local-tts.txt` and `requirements-local-asr.txt`.
Edge TTS requires network access and sends speech text to Microsoft's service.
Whisper ASR runs offline with CPU int8 and requires an explicitly prepared model
from `Systran/faster-whisper-small`, placed at
`<data-directory>/local_asr_models/faster-whisper-small`. The Agent prepares the
model only when transcription is requested; inference never downloads it.
Run `doctor --for local-tts` or `doctor --for local-asr` independently. Neither
capability requires the Apple speech bridge, Xcode, or Apple speech permissions.

Optional Avatar resources remain explicitly selected through `resources install`.
See https://docs.jogg.ai/avatar-resources for classroom-presenter and
office-presenter. Preparing these resources is a separate choice from login
and product bootstrap.

Linux dependency diagnosis and core environment flows are available; bundled
local media still reports unsupported on Linux. This change does not add Linux
OAuth credential storage or trusted screenshot support. Native Windows and
Linux production must pass their platform tests before claiming complete support.

## Coordinated Release

This branch adds `smartvideo_environment_v1`. The current published BOM predates
this contract. Publish compatible renderer/CLI and npm runtime releases, then
update the real BOM and release manifest before shipping the plugin. The launcher
returns `runtime_update_required` when pointed at an old package, preventing
fallback to its automatic installers. Do not replace pins with npm latest.
