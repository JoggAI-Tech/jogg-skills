# Smart Video Beta

Plugin: smart-video-beta@0.8.23-beta.20261010.1. This channel is for internal
testing; prerelease labels do not make public packages private.

Install the moving beta branch:

```sh
codex plugin marketplace add JoggAI-Tech/jogg-skills --ref beta
codex plugin add smart-video-beta@jogg-skills-beta
```

For a reproducible installation, replace beta with smart-video-v0.8.23-beta.20261010.1.
Use this plugin's launcher; system and Python dependencies are prepared by the
Agent in chat only when a requested capability needs them.

Default data: ~/.codex/smartvideo-beta. Default service port: 51694.
OAuth uses a separate Keychain service or Windows DPAPI file and does not migrate
stable credentials. Do not explicitly point beta at stable projects or config.
Stable main and npm latest are unchanged.

Known test limits:

- Native Windows speech execution and Intel macOS remain unverified.
- Real Edge TTS and Whisper inference remain unverified.
- Studio uses the existing checked-in editor distribution because baseline Studio source is incomplete.
- Full Studio typecheck fails on baseline missing modules; extended HDR tests lack baseline image fixture. Renderer fallow audit reports unresolved findings; these commit hooks were excluded for this internal beta after lint/format passed.

Exact packages and source commits: .agents/plugins/beta-release.json.
