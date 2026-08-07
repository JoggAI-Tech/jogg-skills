# Jogg Task Lifecycle

## Authorization

1. Settings creates a short-lived Authorization Code + PKCE request for
   `jogg-skills`.
2. Jogg Web authenticates the user, presents scopes, and requires Space
   selection.
3. Jogg redirects to the loopback callback. The runtime exchanges the code with
   its private verifier and stores the opaque refresh bundle in macOS Keychain
   or Windows DPAPI.
4. The runtime refreshes expiring access before capability requests and never
   exposes tokens to Skills, scripts, frontend state, or run JSON.

## Shot Audio

1. Resolve a selected voice from the catalog, or omit `voice_id` for the service
   default.
2. Write a `submitting` checkpoint, then submit TTS with a stable idempotency key.
3. Persist the returned `task_id` and poll the Task until terminal.
4. Download the transient audio and optional subtitle URL immediately.
5. Store Task ID and local paths, never signed URLs.

## Avatar Shots

1. Complete Shot Audio first so local narration owns timeline timing.
2. For shots selected by `avatar_mode`, submit avatar text mode with `avatar_id`,
   `text`, and `voice_id` under a separate stable idempotency key.
3. Poll and download video locally. Artifact input mode is valid only for a
   caller-owned uploaded `audio_artifact_id`.
4. Non-avatar shots stop after Shot Audio and never create an avatar Task.

## ASR

Upload caller-owned audio to the loopback multipart endpoint, submit the returned
Artifact ID to ASR, then poll and download the transcript. A TTS Task URL is not
an Artifact ID and cannot be used for ASR or avatar audio mode.

## Submission Uncertainty

Write `submitting` before every paid network request. If the response is lost,
preserve its idempotency key and mark `submission_unknown`; do not submit again.
The run enters `blocked_jogg_recovery` until the existing remote result can be
reconciled or the operator explicitly resolves it. This protects against paid
duplicate work.

If a request is known to have failed before acceptance, it may be resubmitted
with the same idempotency identity according to the server error. A missing
`task_id` alone does not prove failure.

## Local Media

Local Media is a pre-submission alternative selected explicitly in Settings.
macOS uses the managed native speech bridge; Windows uses Edge TTS and managed
offline ASR. Both use the npm-managed on-device avatar renderer. Outputs remain under
the unique project workspace.

Never switch a run to Local Media after any Jogg Task, Operation, Artifact, or
historical video checkpoint exists. Such a run remains a Jogg reconciliation
case.

## Finalization

Downloaded media drives local timing, caption cues, HTML preview, editor state,
and FrameVideo rendering. Timeline JSON, source media, preview frames, edits,
and final MP4 are not uploaded to Jogg.
