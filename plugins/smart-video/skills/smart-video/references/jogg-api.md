# Jogg API

Smart Video never calls Jogg Web Controllers or `/v2` endpoints. The loopback
runtime is the only component that knows OAuth credentials and calls these paths
on the configured issuer.

## OAuth2

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/.well-known/openid-configuration` | Discover browser authorization metadata |
| `GET` | `/oauth2/authorize` | Start Authorization Code + PKCE |
| `POST` | `/oauth2/token` | Exchange a code or refresh access |
| `POST` | `/oauth2/revoke` | Revoke local authorization |
| `GET` | `/oauth2/userinfo` | Validate the bearer token |

The runtime creates state and the PKCE verifier. Only the browser URL reaches
Settings. Tokens stay in macOS Keychain or Windows DPAPI and never enter shell,
frontend, logs, or run state.

## Capabilities And Catalogs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/plugin/v1/capabilities` | Discover token-visible capabilities |
| `GET` | `/plugin/v1/capabilities/:id` | Read strict input schema, scopes, and limits |
| `GET` | `/plugin/v1/account/context` | Account and Space context |
| `GET` | `/plugin/v1/quota/summary` | Quota summary |
| `GET` | `/plugin/v1/entitlements/snapshot` | Entitlements |
| `GET` | `/plugin/v1/catalog/voices` | Voice catalog |
| `GET` | `/plugin/v1/catalog/avatars` | Avatar catalog |
| `GET` | `/plugin/v1/catalog/assets` | Asset catalog |
| `GET` | `/plugin/v1/catalog/templates` | Template catalog |
| `GET` | `/plugin/v1/catalog/templates/:id` | Template detail |
| `GET` | `/plugin/v1/catalog/visual-styles` | Visual style catalog |
| `GET` | `/plugin/v1/catalog/music` | Music catalog |
| `GET` | `/plugin/v1/catalog/materials` | Material catalog |
| `GET` | `/plugin/v1/catalog/fonts` | Font catalog |
| `GET` | `/plugin/v1/catalog/material-categories` | Material categories |
| `GET` | `/plugin/v1/catalog/broll` | B-roll catalog search |

Capability metadata is discovery-only. All writes use `Idempotency-Key`. TTS,
ASR, and avatar generation return unified Tasks rather than Operations.

## Generation

| Capability | Method | Path |
| --- | --- | --- |
| `source.product.extract` | `POST` | `/plugin/v1/products/extract` |
| `script.generate` | `POST` | `/plugin/v1/scripts/generate` |
| `audio.tts.synthesize` | `POST` | `/plugin/v1/audio/tts/synthesize` |
| `audio.asr.transcribe` | `POST` | `/plugin/v1/audio/asr/transcribe` |
| `audio.align.forced` | `POST` | `/plugin/v1/audio/align/forced` |
| `image.generate` | `POST` | `/plugin/v1/images/generate` |
| `video.generate.from-text` | `POST` | `/plugin/v1/videos/text/generate` |
| `video.generate.from-image` | `POST` | `/plugin/v1/videos/image/generate` |
| `avatar.photo.generate` | `POST` | `/plugin/v1/avatars/photo/generate` |
| `avatar.motion.create` | `POST` | `/plugin/v1/avatars/motion/create` |
| `avatar.speech.generate` | `POST` | `/plugin/v1/avatars/speech/generate` |
| `lipsync.generate` | `POST` | `/plugin/v1/videos/lipsync/generate` |

Smart Video uses:

| Capability | Required input | Result |
| --- | --- | --- |
| `voice.catalog.list` | none | visible voices |
| `avatar.catalog.list` | none | visible avatars |
| `audio.tts.synthesize` | `text`, API-optional `voice_id` | Task with audio `url`, optional `subtitle_url` |
| `audio.asr.transcribe` | `audio_artifact_id` | Task with transcript `url` |
| `avatar.speech.generate` | `avatar_id` and exactly one input mode | Task with video `url` |

The underlying TTS API permits omitting `voice_id` to use the Space-visible
default. Smart Video must not use that API default: its production workflow
requires the explicit Voice ID confirmed by the user. Avatar text mode requires
`text` and `voice_id`; audio mode requires `audio_artifact_id` and excludes text.
Optional fields are `avatar_source`, `aspect_ratio`, `screen_style`, `caption`,
and `video_name`.

```json
{
  "task_id": "opaque-task-id",
  "status": "processing | succeeded | failed",
  "progress": 0,
  "url": "",
  "subtitle_url": ""
}
```

Only succeeded Tasks contain short-lived URLs. Download them immediately; never
persist or log them, and refetch the Task on resume.

## Tasks And Artifacts

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/plugin/v1/tasks/:id` | Poll a TTS, ASR, or avatar Task |
| `POST` | `/plugin/v1/artifact-uploads` | Create upload target for caller media |
| `POST` | `/plugin/v1/artifact-uploads/:id/complete` | Validate and create Artifact |
| `GET` | `/plugin/v1/artifacts/:id` | Read safe metadata |
| `GET` | `/plugin/v1/artifacts/:id/download` | Get short-lived download URL |

Artifact IDs represent caller-owned input media, such as audio uploaded for ASR
or avatar audio mode. They are not the result contract for TTS, ASR, or avatar
Tasks. `/operations/:id` is read-only compatibility for older checkpoints.

For caller audio, the loopback runtime exposes:

| Method | Loopback path | Input | Result |
| --- | --- | --- | --- |
| `POST` | `/api/v1/jogg/audio/artifacts/upload` | multipart `file` | `{ "audio_artifact_id": "..." }` |

The runtime creates the remote upload target, performs signed PUT, and completes
the Artifact internally. Signatures never reach browser state, run state, shell
output, or logs.
