# Smart Video

Release `0.8.12` provides the Smart Video Skill, editor workflow, media
orchestration, MG references, and a pinned npm-managed runtime for macOS and
Windows.

The managed runtime is installed from these pinned public npm packages:

- `@joggai/smartvideo-cli@0.0.7`
- `@joggai/smartvideo@0.1.5`
- `@joggai/smartvideo-runtime@0.1.2`
- `@joggai/smartvideo-editor@0.1.1`
- `@joggai/smartvideo-registry@0.1.0`
- `@joggai/smartvideo-renderer@0.1.2`
- `@joggai/smartvideo-speech@0.1.0`
- `@joggai/smartvideo-avatar@0.1.0`

`bootstrap` installs `@joggai/smartvideo@0.1.5` into the user's managed Smart
Video runtime. npm resolves the remaining pinned packages from that aggregate
package. The plugin contains no npm tarballs and requires no source checkout.

The Avatar package is a remote Jogg Task/Artifact driver only. It contains no
local inference implementation, Python runtime, ONNX model, or model package.
Local fallback remains available for TTS and ASR; Avatar generation requires
Jogg authorization. Encrypted Avatar templates are no longer bundled into the
plugin. The optional presenter packs can be installed, updated, and removed
independently under `~/.codex/smartvideo/resources/avatar-packs/`:

```bash
npx --yes @joggai/smartvideo@latest resources install classroom-presenter
npx --yes @joggai/smartvideo@latest resources install office-presenter
```

Run `doctor`, then the returned `bootstrap` command. `preflight` starts the
loopback service and returns a Settings URL only after `/health` and `/settings`
are ready.

After a plugin update, `upgrade` installs and verifies the new BOM-pinned package
set before activation. Child packages do not need to share the aggregate package
version, and the plugin never requires a private or bundled `npm/` directory.
If the BOM raises the Node.js minimum, macOS and Linux download and checksum the
matching official release from `nodejs.org` into the user-managed Smart Video
home; Homebrew and administrator access are not required.

macOS FFmpeg setup follows the same managed-runtime principle. Smart Video
downloads a pinned, checksum-verified static build from the macOS provider
linked by `ffmpeg.org`, keeps it under `~/.codex/smartvideo`, and never invokes
Homebrew for FFmpeg.

```bash
bash scripts/smart-video.sh doctor
bash scripts/smart-video.sh bootstrap
bash scripts/smart-video.sh upgrade
bash scripts/smart-video.sh preflight
```

Generated projects, OAuth credentials, task checkpoints, and managed runtime
state live under `~/.codex/smartvideo/`, outside the immutable plugin cache.
Incomplete projects may open in the English-by-default editor, while MP4 export
continues to require complete render assets.

See [INSTALL.md](INSTALL.md) for platform prerequisites and
[skills/smart-video/SKILL.md](skills/smart-video/SKILL.md) for the production
workflow.
