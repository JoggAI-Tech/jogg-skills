# Local Runtime Boundary

The plugin ships a source snapshot of Video Studio and does not import Podcastor at runtime.

## Local Components

- FastAPI listens only on a free `127.0.0.1` port.
- The static editor and `/api/v1/video-studio` share that origin.
- Projects, run state, assets, render snapshots, subtitles, previews, works, and MP4 files live under `~/.codex/smart-slides/`.
- The extracted Podcastor editor and `build_composition_preview_html()` produce the source-of-truth preview and HTML/MG contract.
- Local Chrome rasterizes the selected HTML/MG layer; FFmpeg composes local B-roll, retained Jogg avatar video, Jogg narration audio, captions, and BGM into the MP4.

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
