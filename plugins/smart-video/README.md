# Smart Video

Release `0.8.9` provides the Smart Video Skill, editor workflow, media
orchestration, MG references, and a pinned npm-managed runtime for macOS and
Windows.

The plugin bundles these first-party package tarballs under `npm/`:

- `@smartvideo/cli@0.0.7`
- `@jogg-ai/smartvideo@0.1.0`
- `@jogg-ai/smartvideo-runtime@0.1.0`
- `@jogg-ai/smartvideo-editor@0.1.0`
- `@jogg-ai/smartvideo-registry@0.1.0`
- `@jogg-ai/smartvideo-renderer@0.1.0`
- `@jogg-ai/smartvideo-speech@0.1.0`
- `@jogg-ai/smartvideo-avatar@0.1.0`

`bootstrap` installs these exact local tarballs into the user's managed Smart
Video runtime. npm may still download their normal third-party dependencies
when they are not already cached. No source checkout or first-party npm registry
access is required.

The Avatar package is a remote Jogg Task/Artifact driver only. It contains no
local inference implementation, Python runtime, ONNX model, or model package.
Local fallback remains available for TTS and ASR; Avatar generation requires
Jogg authorization. Existing encrypted Avatar template resources remain in the
plugin as replaceable resources but are not executed or materialized locally.

Run `doctor`, then the returned `bootstrap` command. `preflight` starts the
loopback service and returns a Settings URL only after `/health` and `/settings`
are ready.

```bash
bash scripts/smart-video.sh doctor
bash scripts/smart-video.sh bootstrap
bash scripts/smart-video.sh preflight
```

Generated projects, OAuth credentials, task checkpoints, and managed runtime
state live under `~/.codex/smartvideo/`, outside the immutable plugin cache.
Incomplete projects may open in the English-by-default editor, while MP4 export
continues to require complete render assets.

See [INSTALL.md](INSTALL.md) for platform prerequisites and
[skills/smart-video/SKILL.md](skills/smart-video/SKILL.md) for the production
workflow.
