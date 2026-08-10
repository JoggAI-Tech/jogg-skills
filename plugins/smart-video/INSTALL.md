# Smart Video 0.8.9 Installation

Smart Video supports macOS and Windows from one plugin. The plugin contains its
Skill documents, authoring references, branding, and preserved encrypted Avatar
template resources. Runtime code is installed from pinned public npm packages.

## User Flow

1. Run the read-only `doctor` command.
2. Run the returned `bootstrap` command when dependencies are missing.
3. Open the verified Settings URL and authorize Jogg, or select Local Media for
   TTS/ASR-only workflows.

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
```

```powershell
& "<plugin-root>\scripts\smart-video.cmd" doctor
& "<plugin-root>\scripts\smart-video.cmd" bootstrap
```

`doctor` never changes the machine. `bootstrap` installs the pinned
`@joggai/smartvideo` package under
`~/.codex/smartvideo/node-runtime/releases/`, verifies the full package set,
and atomically updates `active-runtime.json`. An interrupted installation does
not replace the prior active runtime.

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

macOS bootstrap uses Homebrew when host tools are missing. Windows bootstrap
uses `winget` and Git Bash. Both require Node.js 22+, Python 3.10+, Google
Chrome, `jq`, and FFmpeg with `libx264`, AAC, VP9, and subtitles support.

The published `@joggai/smartvideo-avatar` package contains only the remote Jogg
driver and task contracts. It does not contain local Avatar inference code,
models, or Python dependencies.

Developers may override the registry package spec with
`SMARTVIDEO_PACKAGE_SPEC`. Normal users do not configure this variable or any
source checkout path.
