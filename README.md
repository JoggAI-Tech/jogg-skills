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
```

## Install

Install this skills repository with:

```bash
npx skills add JoggAI-Tech/jogg-skills
```

## Current scaffold

- `jogg-api` is the main JoggAI v2 skill for endpoint execution and workflow routing.
- `jogg-lip-sync` is a runnable skill for creating or checking Jogg lip sync tasks with video and audio inputs.
- `jogg-hot-topic-video` is a no-code workflow for researching real hot topics, drafting sourced video content, and operating the visible Jogg web app after user confirmation.

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
