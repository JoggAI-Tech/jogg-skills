# Video Studio BGM Library

This folder is the curated BGM source for Video Studio.

Runtime behavior:

- `manifest.json` defines the selectable music tracks.
- `tracks/` holds bundled local audio files shipped with the repo.
- Runtime should prefer bundled files. `source_url` is kept for license attribution and emergency backfill only.
- The editor never asks an AI model to generate BGM.

License notes:

- The current bundled loops are adapted from Tanner Helland's "A Memory Away" under Creative Commons Attribution 4.0.
- Attribution is stored per track in the manifest and should be preserved in product/legal metadata.
