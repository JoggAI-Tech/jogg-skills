---
name: smart-slides
description: Create a long-form smart-slides project through local Podcastor and Jogg services. Use when the user asks to generate, continue, check, preview, or render a smart-slides video with Jogg talking avatars, B-roll, HTML/MG, or a final MP4.
license: Proprietary
metadata: { "author": "JoggAI", "version": "0.1.0", "openclaw": { "requires": { "bins": ["curl", "jq", "ffmpeg"] }, "os": ["darwin", "linux"] } }
---

# smart-slides

Use this skill to turn a content request into a Jogg-assisted Video Studio MP4.

Run all operations through:

```bash
bash "scripts/video-studio.sh"
```

## User Intent

Extract these values from the request:

- `topic`: the requested subject. Required.
- `duration`: convert minutes to seconds. Default to `600` seconds for a long video.
- `avatar_mode`: `none`, `opening`, `opening_closing`, or `all`. Map “only at the opening and ending” to `opening_closing`.
- `avatar_profile`: infer `style`, `gender`, and `age` from the content when possible. Explicit user preferences always win.

For Chinese requests without an explicit voice, use the default Chinese female voice. For an avatar without an explicit persona, recommend a public landscape avatar based on the content:

- Finance, technology, education, health, policy, or news: `professional`, adult.
- Lifestyle, travel, fashion, beauty, food, or entertainment: `social`, young adult.
- Use gender only when the user or content clearly requires it; otherwise use `female` to match the default voice.

## Required Configuration

The runner uses these defaults:

```bash
export JOGG_REPO="/Users/cds-dn-137/Documents/golang/jogg-backend-srv"
export PODCASTOR_REPO="/Users/cds-dn-137/Documents/golang/operation-Podcastor"
export JOGG_BASE_URL="http://127.0.0.1:8000"
export PODCASTOR_BASE_URL="http://127.0.0.1:8001"
```

Authenticate with either:

- `JOGG_API_KEY`: an existing local Jogg OpenAPI access key.
- `JOGG_WEB_TOKEN`: the local Jogg browser JWT. The runner exchanges it in memory through `/openapi_key`; it does not write the token or key to disk.

Optional overrides: `JOGG_DEFAULT_AVATAR_ID`, `JOGG_DEFAULT_VOICE_ID`, `PODCASTOR_ENV_FILE`, `VIDEO_STUDIO_HERMES_REPO`, `JOGG_START_CMD`, and `PODCASTOR_START_CMD`.

## Commands

Preflight starts missing local services and verifies the available prerequisites:

```bash
bash "scripts/video-studio.sh" preflight
```

Create a video:

```bash
bash "scripts/video-studio.sh" run \
  --topic "人工智能如何改变制造业" \
  --duration-seconds 600 \
  --avatar-mode opening_closing \
  --avatar-style professional \
  --avatar-gender female \
  --avatar-age adult
```

Check or resume a returned run ID:

```bash
bash "scripts/video-studio.sh" status --run-id "vs-..."
bash "scripts/video-studio.sh" resume --run-id "vs-..."
```

## Execution Rules

- Run `preflight` before `run` when local services may not already be running.
- Never call Jogg or Podcastor with ad hoc commands when the runner supports the requested operation.
- Treat JSON on stdout as the operation result. Progress and errors are on stderr.
- Do not print, store, summarize, or expose `JOGG_WEB_TOKEN` or `JOGG_API_KEY`.
- Avatar videos are generated only for selected shots. They are stripped of audio before upload to Podcastor, and `avatar_enabled` is disabled so the Hermes global avatar does not appear elsewhere.
- If a poll limit is reached, return the `run_id`; use `resume` rather than submitting a second external task.
- A `waiting_render_worker` result is an environment problem, not a completed video.
