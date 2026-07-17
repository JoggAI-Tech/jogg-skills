# jogg-skills

This repository is initialized as an Agent Skills project based on the Agent Skills specification.

## Structure

```text
skills/
  jogg-api/
    SKILL.md
    scripts/jogg-v2.sh
    references/
  jogg-lip-sync/
    SKILL.md
    run.sh
    .env.example
  trend-to-video/
    SKILL.md
    evals/
```

## Install

Install the repository Skills with:

```bash
npx skills add JoggAI-Tech/jogg-skills
```

Smart Slides is an optional Codex plugin in the same repository at
[`plugins/smart-slides`](plugins/smart-slides). Register the repository marketplace and install it with:

```bash
codex plugin marketplace add JoggAI-Tech/jogg-skills --ref main
codex plugin add smart-slides@jogg-skills
```

## Product site

Open [`index.html`](index.html) for the JoggAI product introduction,
official feature examples, and the Jogg Skills installation entry point.

## Current scaffold

- `jogg-api` is the main JoggAI v2 skill for endpoint execution and workflow routing.
- `jogg-lip-sync` is a runnable skill for creating or checking Jogg lip sync tasks with video and audio inputs.
- `trend-to-video` is a no-code workflow for researching real hot topics, drafting sourced video content, and operating the visible Jogg web app after user confirmation.

## jogg-api

`jogg-api` is organized at `skills/jogg-api/` and includes:

- `SKILL.md` for intent routing across JoggAI v2 APIs and workflows
- `scripts/jogg-v2.sh` as the unified runtime
- `references/endpoints.md` for endpoint lookup
- `references/workflows.md` for workflow lookup

### Local setup

1. Copy `skills/jogg-api/.env.example` to `skills/jogg-api/.env`.
2. Fill in `JOGG_API_KEY`.
3. Ensure `curl` and `jq` are available in your shell.

## jogg-lip-sync

`jogg-lip-sync` is organized at `skills/jogg-lip-sync/` and includes:

- `SKILL.md` for activation and execution instructions.
- `run.sh` as the skill runner.
- `.env.example` as the local environment template.

### Local setup

1. Copy `skills/jogg-lip-sync/.env.example` to `skills/jogg-lip-sync/.env`.
2. Fill in `JOGG_API_KEY`. 
3. Ensure `curl` and `jq` are available in your shell.

Get `JOGG_API_KEY`:

- Buy an API plan: https://www.jogg.ai/api-pricing/
- See how to find your API key: https://docs.jogg.ai/api-reference/v2/QuickStart/GettingStarted

### Example prompts

- `Run lip sync with this video and audio`
- `Check the status of lip sync task <task-id>`
- `Create a lip sync result from this mp4 and mp3`

## trend-to-video

`trend-to-video` is a no-code workflow for turning current, source-grounded
topics into Jogg videos through the visible web app.

It can:

- research and rank 3-5 credible hot-topic candidates across selectable categories;
- draft an Avatar Video or a two-host Video Podcast from verified source material;
- recommend available Jogg avatars, voices, layouts, aspect ratios, and subtitles;
- operate `https://app.jogg.ai` after the user confirms the final script and settings.

It requires Firecrawl for research and a browser session with Jogg access. The user
completes registration, login, CAPTCHA, 2FA, and purchase confirmation. The skill
does not write application code, call Jogg APIs, run helper scripts, bypass access
controls, or publish videos externally.

### Example prompts

- `Track today's AI and business hot topics and give me options for a Jogg video.`
- `Turn this verified story into a 30-second English Avatar Video with subtitles.`
- `Create a two-host Jogg Video Podcast from this current business trend.`
