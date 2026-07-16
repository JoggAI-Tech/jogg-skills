# Local Runtime Boundary

The plugin ships a source snapshot of Video Studio and does not import Podcastor at runtime.

## Local Components

- FastAPI listens only on a free `127.0.0.1` port.
- The static editor and `/api/v1/video-studio` share that origin.
- Projects, run state, assets, render snapshots, subtitles, previews, works, and MP4 files live under `~/.codex/smart-slides/`.
- HyperFrames 0.7.59 renders in local Chrome; FFmpeg performs audio extraction and final media assembly.
- GSAP 3.14.2 is bundled locally. Runtime compositions do not fetch a CDN script.

## Allowed Requests

- Local Jogg identity/OpenAPI key, voices, avatars, avatar video submission/status, and Jogg result download.
- Pexels and Pixabay search/download only when their keys are configured and material is requested.
- Package/browser installation during explicit preflight setup is tooling setup, not a video business API.

## Forbidden Requests

- Podcastor remote API or source-repo runtime imports.
- Hermes or another render worker.
- COS or another cloud object store.
- DeepSeek, SiliconFlow, or another external LLM.
- Standalone TTS.
- Remote video rendering.
- Runtime JavaScript/font CDNs.

## Checkpoints

Run state may store project ID, shot IDs, Jogg video IDs, local file paths, stage, work ID, and local result URLs. It must not store bearer tokens or OpenAPI keys.

`resume` treats an existing Jogg `video_id`, extracted audio, retained avatar video, and local work ID as authoritative. Missing downstream files may be rebuilt, but paid Jogg tasks are never resubmitted automatically.
