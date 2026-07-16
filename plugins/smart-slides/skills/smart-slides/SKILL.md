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

Read [planning-contracts.md](references/planning-contracts.md), [MG-VISUAL-STANDARD-v1.md](references/MG-VISUAL-STANDARD-v1.md), and [mg-director-visual-contract.md](references/mg-director-visual-contract.md) before authoring a plan. Read [html-mg-contract.md](references/html-mg-contract.md) when implementing the director-selected HTML/MG. These are direct Podcastor source references at the commit recorded in `extraction-manifest.json`; do not replace them with a generic card or slide layout.

Before starting a new run, Codex must author a planning JSON and pass it with `--planning-file`. Persist it under `~/.codex/smart-slides/plans/` so a blocked or interrupted run can reuse it. Include the existing project fields `producer_analysis`, `production_requirement_document`, `creative_plan`, `script`, `script_director`, `director_document`, and non-empty `scene_groups`. Every enabled `mg_director` must select `visual_recipe` and deliver a self-contained `composition`; copy that same director contract into the generated shot. The HTML layer executes those choices and must not reselect a PPT-derived grammar. Every shot needs topic-specific narration and render intent. The local normalizer validates scene durations, render contracts, and HTML/MG fields. Do not call an external LLM API.

For every enabled `llm_bespoke_html` shot, include a complete `html_design.custom_html` and `html_design.custom_css` in the planning file. The runtime passes these through Podcastor's original bespoke-HTML sanitizer, root guard, font normalization, canvas-fit report, and composition-execution report before it creates a project preview or a paid Jogg task. A missing or invalid bespoke layer blocks the run; it does not silently render `mg_design_doc`, a template, generic cards, a dashboard, or a faux slide.

Author the HTML as the original director pipeline requires:

- Establish the one dominant visual structure in the selected `composition.hero_frame` first, then L1, L2, and L3 information in order from [MG-VISUAL-STANDARD-v1.md](references/MG-VISUAL-STANDARD-v1.md).
- Use only `screen_slots` for visible copy. The composition must read as a complete 1920x1080 documentary frame without a B-roll aperture, media placeholder, or empty half-frame.
- Include one `ai-mg-layer` root with `data-ai-generated-html="true"`, local HTML/CSS/SVG only, and a compact `edit_schema`. Use broad paths and large semantic SVG objects when the director requires them; do not use thin-line grids or card arrays as the main visual.
- Treat `template` as an explicit operator-selected recovery mode only. It is not a normal output strategy for Smart Slides runs.

For B-roll, give every non-avatar shot a distinct, visible action or subject in `broll_prompt` and `asset_search_plan.search_queries`; adjacent shots must not recycle the same query or semantic scene. The local downloader excludes a provider asset already selected by another shot and requires a source clip long enough for the shot. Do not accept a short clip by replaying it. When no unique duration-qualified source exists, preserve the checkpoint and return `blocked_broll` instead of rendering repeated footage.

Never start paid generation with deterministic fallback prose. Without a planning file, the runner returns `blocked_planning` before project creation or Jogg submission. Author the missing plan, then continue the same run with `resume --run-id ... --planning-file ...`.

## Run

Preflight checks local tools, starts the bundled loopback-only API, and validates the configured public Jogg OpenAPI key:

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
bash "<plugin-root>/scripts/smart-slides.sh" refresh-broll --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" render --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" resume --run-id "ss-..."
bash "<plugin-root>/scripts/smart-slides.sh" resume --run-id "ss-..." --planning-file "/absolute/path/to/plan.json"
```

Import an existing Video Studio project JSON without schema migration:

```bash
bash "<plugin-root>/scripts/smart-slides.sh" import --file "/absolute/path/project.json"
```

Open `editor_url` to edit the timeline, B-roll, HTML/MG, avatar scope, narration overrides, and BGM. Open `composition_preview_url` for the extracted composition preview. `final_video_url` is a local MP4.

Use `refresh-broll` only for an explicit material redo. It clears provider-backed Pexels/Pixabay candidates and selections, preserves Jogg/avatar/voice assets and local uploads, then downloads one distinct duration-qualified source for each non-avatar shot and regenerates the preview. It never submits Jogg tasks.

## Jogg And Sound

Read [jogg-endpoints.md](references/jogg-endpoints.md) for request shapes and [jogg-workflows.md](references/jogg-workflows.md) for polling.

- Every shot uses `/v2/create_video_from_avatar` with `voice.type="script"`.
- There is no standalone TTS request.
- FFmpeg extracts audio from every completed Jogg video.
- Before local rendering, every Jogg narration track must cover at least 90% of its shot duration. The plugin blocks an underlength track instead of padding a silent tail; expand the corresponding narration and generate a new Jogg task.
- Only `avatar_mode` target shots retain a muted avatar video. Non-target Jogg video images are deleted after audio extraction.
- A saved `video_id` is a paid-task checkpoint. Always use `resume`; never resubmit it.
- A `submission_unknown` task means Jogg may have accepted the paid POST but its response was lost. Stop and report `blocked_jogg_recovery`; never clear or resubmit that task automatically.

## Authentication

Set `JOGG_API_KEY` from the Jogg OpenAPI dashboard. Smart Slides calls `https://api.jogg.ai/v2/...` with `X-Api-Key`; browser-session tokens are not accepted as a substitute. Credentials stay in process memory and never enter run state or stdout.

## Boundaries

Read [runtime-boundary.md](references/runtime-boundary.md). The only business network requests allowed are Jogg and explicitly configured Pexels/Pixabay requests. Never call Podcastor remote APIs, Hermes, COS, DeepSeek, SiliconFlow, another LLM API, standalone TTS, a remote renderer, or a runtime CDN.

Stdout is redacted JSON. Progress goes to stderr. A `blocked_planning`, `waiting_jogg`, `blocked_broll`, or `waiting_render` result is resumable and must be returned with its `run_id`. For `blocked_planning`, create the contract-compliant JSON before resuming; do not enable deterministic fallbacks for a user run.

Rendering uses the extracted Podcastor Video Studio preview/editor contract. Local Chrome rasterizes only the project-selected HTML/MG layer, then FFmpeg composes it with local B-roll, Jogg video/audio, subtitles, and BGM. Require `ffmpeg`, `ffprobe`, and local Chrome or Chromium; configure `SMART_SLIDES_CHROME_BIN` only when needed. Do not install packages or use a remote renderer at runtime.
