# jogg-skills

This repository is initialized as an Agent Skills project based on the Agent Skills specification.

## Structure

```text
skills/
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

- `jogg-lip-sync` is a runnable skill for creating or checking Jogg lip sync tasks with video and audio inputs.

## jogg-lip-sync

`jogg-lip-sync` is organized at `skills/jogg-lip-sync/` and includes:

- `SKILL.md` for activation and execution instructions.
- `run.sh` as the skill runner.
- `.env.example` as the local environment template.

### Local setup

1. Copy `skills/jogg-lip-sync/.env.example` to `skills/jogg-lip-sync/.env`.
2. Fill in `JOGG_API_KEY`.
3. Ensure `curl` and `jq` are available in your shell.

### Example prompts

- `Run lip sync with this video and audio`
- `Check the status of lip sync task <task-id>`
- `Create a lip sync result from this mp4 and mp3`
