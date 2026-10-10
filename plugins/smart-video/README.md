# Smart Video

Release `0.8.22` provides the Smart Video Skill, editor workflow, media
orchestration, MG references, and a pinned npm-managed runtime for macOS and
Windows.

The managed runtime is installed from these pinned public npm packages:

- `@joggai/smartvideo-cli@0.0.7`
- `@joggai/smartvideo@0.1.14`
- `@joggai/smartvideo-runtime@0.1.11`
- `@joggai/smartvideo-editor@0.1.1`
- `@joggai/smartvideo-registry@0.1.0`
- `@joggai/smartvideo-renderer@0.1.2`
- `@joggai/smartvideo-speech@0.1.0`
- `@joggai/smartvideo-avatar@0.1.3`
- `@joggai/smartvideo-avatar-engine@0.1.1` (installed on demand)

`bootstrap` installs `@joggai/smartvideo@0.1.14` into the user's managed Smart
Video runtime. npm resolves the remaining pinned packages from that aggregate
package. The plugin contains no npm tarballs and requires no source checkout.

The Avatar package contains the remote Jogg Task/Artifact driver and the local
`avatar-engine` orchestration driver. The on-demand Avatar Engine npm package
contains its portable inference source and encrypted model assets, and creates
its managed Python environment outside `node_modules` during explicit resource
installation. Encrypted Avatar templates are no longer bundled into the plugin.
The optional presenter packs can be installed, updated, and removed independently under
`<selected-root>/resources/avatar-packs/`:

```bash
bash "<plugin-root>/scripts/smart-video.sh" resources install classroom-presenter
bash "<plugin-root>/scripts/smart-video.sh" resources install office-presenter
```

Each resource command atomically installs or upgrades the managed Avatar driver
and `@joggai/smartvideo-avatar-engine@0.1.1`, then bootstraps the engine and
downloads and verifies the Presenter pack. No engine path is required from the
user. Local generation becomes ready only after all three parts pass validation;
otherwise the runtime returns `driver_unavailable` and does not start generation.

After installation, the installing Agent follows the bundled
[new-chat handoff and usage guidance](skills/smart-video/references/post-install.md).
For a real task, check only its required capability with `doctor --for <capability>`.
Explain missing tools in chat and proceed with Agent preparation, reusing existing
installations first. Do not present installation-mode choices or open Settings
automatically.
`bootstrap` installs only the pinned product packages. `preflight` starts the
loopback service and returns a Settings URL only after `/health` and `/settings`
are ready.

After a plugin update, `upgrade` installs and verifies the new BOM-pinned package
set before activation. Child packages do not need to share the aggregate package
version, and the plugin never requires a private or bundled `npm/` directory.
Missing Node, Python, FFmpeg, Chrome, and local models return official preparation
guidance. Register validated paths with `env configure` and recheck the original
capability. Windows can use installed executables immediately with stale PATH.
See [INSTALL.md](INSTALL.md) for preparation, platform limits, and coordinated release
requirements. The published BOM must be updated after the compatible packages
are released; older runtimes return `runtime_update_required`.

```bash
bash "<plugin-root>/scripts/smart-video.sh" doctor
bash "<plugin-root>/scripts/smart-video.sh" bootstrap
bash "<plugin-root>/scripts/smart-video.sh" upgrade
bash "<plugin-root>/scripts/smart-video.sh" preflight
```

Generated projects, OAuth credentials, task checkpoints, and managed runtime
state live outside the immutable plugin cache. The launcher automatically uses
the system user directory or a writable workspace's `.smartvideo` directory;
`SMARTVIDEO_HOME` can override that selection. For directory selection and sandbox access, see
[Data Directory And Sandbox Access](INSTALL.md#data-directory-and-sandbox-access).
Incomplete projects may open in the English-by-default editor, while MP4 export
continues to require complete render assets.

See [INSTALL.md](INSTALL.md) for platform prerequisites and
[skills/smart-video/SKILL.md](skills/smart-video/SKILL.md) for the production
workflow.
