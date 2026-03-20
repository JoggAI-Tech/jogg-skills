# jogg-skills

This repository is initialized as an Agent Skills project based on the Agent Skills specification.

## Structure

```text
.agents/
  skills/
    jogg-lip-sync/
      SKILL.md
      run.sh
      .env.example
    jogg-skill-template/
      SKILL.md
      scripts/
      references/
      assets/
```

## How to add a new skill

1. Create a new directory under `.agents/skills/`.
2. Make the directory name match the `name` field in `SKILL.md`.
3. Add a `SKILL.md` file with frontmatter and step-by-step instructions.
4. Add `scripts/`, `references/`, or `assets/` only when needed.

## Try it in an Agent Skills compatible client

1. Open this repository in your editor.
2. Confirm the skill folder exists at `.agents/skills/`.
3. Use the client skill discovery command such as `/skills` if supported.
4. Invoke the skill with a prompt matching its description.

## Current scaffold

- `jogg-skill-template` is a reusable template you can copy and adapt into domain-specific skills for JoggAI.
- `jogg-lip-sync` is a runnable skill for creating or checking Jogg lip sync tasks with video and audio inputs.

## jogg-lip-sync

`jogg-lip-sync` is organized at `.agents/skills/jogg-lip-sync/` and includes:

- `SKILL.md` for activation and execution instructions.
- `run.sh` as the skill runner.
- `.env.example` as the local environment template.

### Local setup

1. Copy `.agents/skills/jogg-lip-sync/.env.example` to `.agents/skills/jogg-lip-sync/.env`.
2. Fill in `JOGG_API_KEY`.
3. Ensure `curl` and `jq` are available in your shell.

### Example prompts

- `Run lip sync with this video and audio`
- `Check the status of lip sync task <task-id>`
- `Create a lip sync result from this mp4 and mp3`
