# Smart Video

Release `0.8.19` provides the Smart Video Skill, editor workflow, media
orchestration, MG references, and a pinned npm-managed runtime for macOS and
Windows.

The managed runtime is installed from these pinned public npm packages:

- `@joggai/smartvideo-cli@0.0.7`
- `@joggai/smartvideo@0.1.12`
- `@joggai/smartvideo-runtime@0.1.10`
- `@joggai/smartvideo-editor@0.1.1`
- `@joggai/smartvideo-registry@0.1.0`
- `@joggai/smartvideo-renderer@0.1.2`
- `@joggai/smartvideo-speech@0.1.0`
- `@joggai/smartvideo-avatar@0.1.3`
- `@joggai/smartvideo-avatar-engine@0.1.1` (installed on demand)

`bootstrap` installs `@joggai/smartvideo@0.1.12` into the user's managed Smart
Video runtime. npm resolves the remaining pinned packages from that aggregate
package. The plugin contains no npm tarballs and requires no source checkout.

The Avatar package contains the remote Jogg Task/Artifact driver and the local
`avatar-engine` orchestration driver. The on-demand Avatar Engine npm package
contains its portable inference source and encrypted model assets, and creates
its managed Python environment outside `node_modules` during explicit resource
installation. Encrypted Avatar templates are no longer bundled into the plugin.
The optional presenter packs can be installed, updated, and removed independently under
`~/.codex/smartvideo/resources/avatar-packs/`:

```bash
npx --yes @joggai/smartvideo@0.1.12 resources install classroom-presenter
npx --yes @joggai/smartvideo@0.1.12 resources install office-presenter
```

Each resource command atomically installs or upgrades the managed Avatar driver
and `@joggai/smartvideo-avatar-engine@0.1.1`, then bootstraps the engine and
downloads and verifies the Presenter pack. No engine path is required from the
user. Local generation becomes ready only after all three parts pass validation;
otherwise the runtime returns `driver_unavailable` and does not start generation.

Run `doctor`, then the returned `bootstrap` command. `preflight` starts the
loopback service and returns a Settings URL only after `/health` and `/settings`
are ready.

After a plugin update, `upgrade` installs and verifies the new BOM-pinned package
set before activation. Child packages do not need to share the aggregate package
version, and the plugin never requires a private or bundled `npm/` directory.
If the BOM raises the Node.js minimum, macOS and Linux download and checksum the
matching official release from `nodejs.org` into the user-managed Smart Video
home. Smart Video never invokes Homebrew. It reuses a compatible system Python
and Chrome installation; when either is missing, bootstrap points to the
official python.org or Google Chrome download instead of installing through a
package manager.

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
