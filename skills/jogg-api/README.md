# jogg-api

Unified JoggAI v2 skill for most API endpoint lookups and main workflow execution.

## Included

- One runtime entrypoint: `scripts/jogg-v2.sh`
- Endpoint mode: `--op <operation>`
- Workflow mode: `--workflow <workflow>`
- Shared polling guardrails:
  - minimum poll interval `10s`
  - bounded `max_wait_seconds`
  - bounded `max_poll_attempts`

## Local setup

1. Copy `.env.example` to `.env`
2. Fill in `JOGG_API_KEY`
3. Ensure `curl` and `jq` are available

## Quick examples

```bash
bash scripts/jogg-v2.sh --list-ops
bash scripts/jogg-v2.sh --list-workflows
```

```bash
bash scripts/jogg-v2.sh \
  --op voices-list \
  --query-json '{"language":"en-US","gender":"Male"}'
```

```bash
bash scripts/jogg-v2.sh \
  --workflow ai-scripts \
  --body-json '{
    "language":"english",
    "video_length_seconds":"30",
    "script_style":"Storytime",
    "product_info":{
      "source_type":"details",
      "data":{
        "name":"Amazing Bottle",
        "description":"Insulated bottle for commuters and gym users"
      }
    }
  }'
```

## Notes

- `jogg-lip-sync` stays independent on purpose and is not duplicated here.
- For template variables or product media with local files, use `local_path` and the runtime will upload before creating the task.
