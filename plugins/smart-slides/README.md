# Smart Slides Codex Plugin

Smart Slides is an extracted, standalone Video Studio runtime. It preserves Podcastor's project schema, local editor state, B-roll/MG services, composition preview, render manifest, and work snapshot without requiring the Podcastor repository after installation.

The only video business requests are Jogg plus optional Pexels/Pixabay material downloads. Planning is authored by Codex from the extracted Podcastor contracts and passed to the local runner as JSON. The original Podcastor Video Studio preview/editor contract drives local Chrome HTML/MG rasterization, and FFmpeg performs final composition. Extracted deterministic planner helpers remain available only for source-parity and test fixtures through `SMART_SLIDES_ALLOW_DETERMINISTIC_FALLBACK=1`; they are not a user-generation path.

## Setup

Required commands: `curl`, `jq`, `ffmpeg`, `ffprobe`, and local Google Chrome or Chromium. Set `SMART_SLIDES_CHROME_BIN` only when Chrome is not installed in its standard location. The renderer does not install packages or use a remote render service at runtime.

Configure either `JOGG_API_KEY` or `JOGG_WEB_TOKEN` in the environment or `~/.codex/smart-slides/.env`. A web token is exchanged for an OpenAPI key in memory. Neither credential is saved or printed.

```bash
bash scripts/smart-slides.sh preflight
```

Preflight creates a local Python environment if needed, starts the bundled FastAPI on a free loopback port, and starts Jogg only if it is not already reachable.

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
