---
name: smart-slides
description: Use when the user asks to create, continue, inspect, edit, preview, import, or render a long-form smart-slides or Video Studio video with Jogg voices, talking avatars, B-roll, HTML/MG, subtitles, BGM, or a local MP4.
---

# Smart Slides

Create and edit the existing Video Studio project format without a Podcastor source checkout or cloud renderer. Use `<plugin-root>/scripts/smart-slides.sh` for lifecycle operations.

## Interpret The Request

Extract:

- `topic`: required subject or source brief.
- `duration_seconds`: convert minutes to seconds; default long-form requests to `600`.
- `avatar_mode`: map user wording to `none`, `opening`, `opening_closing`, or `all`.
- avatar persona: explicit avatar/voice IDs win. Otherwise infer professional/social, gender, and age from the subject.

For an unspecified Chinese voice, choose the first available Chinese female voice. For an unspecified avatar, choose a public landscape avatar and progressively relax style, age, then gender filters if no candidate is available.

## Generate Planning

Read [planning-contracts.md](references/planning-contracts.md) before authoring a plan and [html-mg-contract.md](references/html-mg-contract.md) before authoring HTML/MG. These contracts are extracted from Podcastor's Video Studio planner at the source commit recorded in `extraction-manifest.json`.

Before starting a new run, Codex must author a planning JSON and pass it with `--planning-file`. Persist it under `~/.codex/smart-slides/plans/` so a blocked or interrupted run can reuse it. Include the existing project fields `producer_analysis`, `production_requirement_document`, `creative_plan`, `script`, `script_director`, `director_document`, and non-empty `scene_groups`. Every shot needs topic-specific narration and render intent. The local normalizer validates scene durations, render contracts, and HTML/MG fields. Do not call an external LLM API.

Never start paid generation with deterministic fallback prose. Without a planning file, the runner returns `blocked_planning` before project creation or Jogg submission. Author the missing plan, then continue the same run with `resume --run-id ... --planning-file ...`.

## Run

Preflight checks local tools, starts the bundled loopback-only API, and starts Jogg only when it is not already reachable:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" preflight
```

Create a 10-minute project:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" run \
  --topic "人工智能如何改变制造业" \
  --duration-seconds 600 \
  --avatar-mode opening_closing \
  --avatar-style professional \
  --avatar-gender female \
  --avatar-age adult \
  --planning-file "/absolute/path/to/plan.json"
```

Use the returned ID for lifecycle actions:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" status --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" preview --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" render --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" resume --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" resume --run-id "ss-..." --planning-file "/absolute/path/to/plan.json"
```

Import an existing Video Studio project JSON without schema migration:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" import --file "/absolute/path/project.json"
```

Open `editor_url` to edit the timeline, B-roll, HTML/MG, avatar scope, narration overrides, and BGM. Open `composition_preview_url` for the extracted composition preview. `final_video_url` is a local MP4.

## Jogg And Sound

Read [jogg-endpoints.md](references/jogg-endpoints.md) for request shapes and [jogg-workflows.md](references/jogg-workflows.md) for polling.

- Every shot uses `/open/v2/create_video_from_avatar` with `voice.type="script"`.
- There is no standalone TTS request.
- FFmpeg extracts audio from every completed Jogg video.
- Only `avatar_mode` target shots retain a muted avatar video. Non-target Jogg video images are deleted after audio extraction.
- A saved `video_id` is a paid-task checkpoint. Always use `resume`; never resubmit it.
- A `submission_unknown` task means Jogg may have accepted the paid POST but its response was lost. Stop and report `blocked_jogg_recovery`; never clear or resubmit that task automatically.

## Authentication

Use either `JOGG_API_KEY` or `JOGG_WEB_TOKEN`. The web token reads `/openapi_key` and only calls `/openapi_key/generate` when no key exists. Credentials stay in process memory and never enter run state or stdout.

## Boundaries

Read [runtime-boundary.md](references/runtime-boundary.md). The only business network requests allowed are Jogg and explicitly configured Pexels/Pixabay requests. Never call Podcastor remote APIs, Hermes, COS, DeepSeek, SiliconFlow, another LLM API, standalone TTS, a remote renderer, or a runtime CDN.

Stdout is redacted JSON. Progress goes to stderr. A `blocked_planning`, `waiting_jogg`, `blocked_broll`, or `waiting_render` result is resumable and must be returned with its `run_id`. For `blocked_planning`, create the contract-compliant JSON before resuming; do not enable deterministic fallbacks for a user run.

Rendering requires a locally available HyperFrames `0.7.59`. The runner uses `npx --no-install hyperframes@0.7.59` or `SMART_SLIDES_HYPERFRAMES_BIN`; do not allow npm installation or runtime package downloads.
