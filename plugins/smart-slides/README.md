# Smart Slides Codex Plugin

Smart Slides is an extracted, standalone Video Studio runtime. It preserves Podcastor's project schema, local editor state, B-roll/MG services, composition preview, render manifest, and work snapshot without requiring the Podcastor repository after installation.

The only video business requests are Jogg plus optional Pexels/Pixabay material downloads. Planning is authored by Codex from the extracted Podcastor contracts and passed to the local runner as JSON. The original Podcastor Video Studio preview/editor contract drives local Chrome HTML/MG rasterization, and FFmpeg performs final composition. Extracted deterministic planner helpers remain available only for source-parity and test fixtures through `SMART_SLIDES_ALLOW_DETERMINISTIC_FALLBACK=1`; they are not a user-generation path.

## Setup

Required commands: `curl`, `jq`, `ffmpeg`, `ffprobe`, Node.js 22 or newer, and local Google Chrome or Chromium. Set `SMART_SLIDES_NODE_BIN` or `SMART_SLIDES_CHROME_BIN` only when they are not available from the normal PATH or standard Chrome location. For a managed plugin dependency, place matching `ffmpeg` and `ffprobe` binaries in `SMART_SLIDES_TOOL_DIR` (default `~/.codex/smart-slides/bin`); preflight uses that private directory before the system PATH. The repository deliberately does not commit platform-specific FFmpeg binaries or install them silently, because they are architecture-specific and carry redistribution/license obligations. The renderer does not use a remote render service at runtime.

Configure `JOGG_API_KEY` from the Jogg OpenAPI dashboard in the environment or `~/.codex/smart-slides/.env`. Smart Slides calls `https://api.jogg.ai/v2/...` directly; a browser-session token is not a public OpenAPI credential. The key is neither saved in run state nor printed.

```bash
bash scripts/smart-slides.sh preflight
```

Preflight creates a local Python environment if needed, starts the bundled FastAPI on a free loopback port, and validates the configured Jogg OpenAPI key before any paid request.

Jogg result downloads are retried locally when the CDN is briefly unavailable. Set `SMART_SLIDES_JOGG_DOWNLOAD_MAX_SECONDS` only to tune the per-attempt download limit; retries always reuse the saved Jogg `video_id`.

## Example

```bash
bash scripts/smart-slides.sh run \
  --topic "人工智能如何改变制造业" \
  --duration-seconds 600 \
  --avatar-mode opening_closing \
  --planning-file "/absolute/path/to/codex-plan.json"
```

The Smart Slides skill reads the extracted planning and HTML/MG contracts, authors this file locally, and then starts the runner. Direct CLI use must provide the same planning JSON. If it is omitted, the runner returns `blocked_planning` before creating a project or making a paid Jogg request. Supply the plan later without losing the run:

```bash
bash scripts/smart-slides.sh resume \
  --run-id "ss-..." \
  --planning-file "/absolute/path/to/codex-plan.json"
```

The JSON result includes `run_id`, `project_id`, `editor_url`, `composition_preview_url`, `work_id`, and `final_video_url`. Use `resume --run-id ...` after a Jogg, material, or render timeout.

Every shot obtains sound from a Jogg avatar video using `voice.type=script`. FFmpeg extracts the audio locally. Only avatar-target shots retain a muted avatar picture; no standalone TTS endpoint is used.

The runner writes a `submitting` checkpoint before each paid Jogg POST. Because Jogg does not expose an idempotency key or lookup-by-name endpoint, a lost response becomes `blocked_jogg_recovery`; `resume` refuses to submit it again automatically. Once a `video_id` is saved, `resume` always reuses it.

## Source Updates

`extraction-manifest.json` records source commits, hashes, modes, and symbols. `scripts/sync-from-podcastor.sh` checks drift by default. `--refresh` updates only verbatim snapshots and deterministic planner extraction; it never overwrites local adapters.

Run the full suite with `bash tests/run-tests.sh`.
