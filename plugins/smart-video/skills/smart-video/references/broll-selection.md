# B-roll Selection

This contract keeps low-cost selection deterministic: ordered search, rule-based
filtering, and first-qualified download. It does not invoke another model or rank
candidate footage with AI.

## Input

Every B-roll shot receives:

```json
{
  "search_queries": [
    "Japanese office workers commuting Tokyo 1990s",
    "Japan recession closed storefront",
    "Tokyo business district documentary"
  ],
  "must_include": ["Japan", "real people"],
  "exclude": ["animation", "illustration", "unrelated geography"],
  "search_language": "en",
  "target_aspect_ratio": "16:9"
}
```

Set `target_aspect_ratio` from the confirmed whole-video ratio. Use `16:9` for
landscape and `9:16` for portrait; never assume landscape independently of the
project.

Queries are ordered. The first qualified candidate becomes the default, so the
first query is specific and later queries are controlled fallbacks. Adjacent
shots must not share the same primary query.

## Retrieval And Selection

Automatic retrieval requires a configured Pexels API Key. Check it after the
Storyboard establishes an actual B-roll need and before paid media submission.
When required footage is not already present, validate the saved key before any
paid Jogg submission. If the key is missing, invalid, or cannot be verified,
stop at the resumable checkpoint and provide the Pexels settings link. Do not
invent footage, remove the B-roll shot, or continue with an unrelated provider.

Index multiple shots with up to four concurrent Pexels searches. Then process
shots in Storyboard order:

1. Search only the configured Pexels video provider in this release.
2. Normalize provider metadata and prefer a native orientation matching the
   target ratio. When no native match exists, accept only a candidate with a
   verified subject-safe crop for the target canvas; do not stretch it.
3. Reject excluded concepts and known irrelevant categories using provider-owned
   titles, descriptions, tags, and keywords.
4. Prefer a different provider asset for each shot. Reuse one only when adjacent
   confirmed shots intentionally require the same observable footage.
5. Reject clips that cannot cover measured shot duration without looping.
6. Download only from approved provider domains.
7. Serially download the first candidate that succeeds for each shot.

Keep only preview metadata for other qualified candidates; do not download them.
Record intentional reuse in the selection result. Do not silently reuse a source,
loop a short clip, or invent a local fallback. Return `blocked_broll` with its
resumable checkpoint when retrieval fails.

## Audio

B-roll is muted by default. A conversational request may enable reduced source
audio for selected shots without another search or download. After the user
names the affected shots, invoke `broll-audio` for each one; use `--enable` with
a volume no greater than `0.35`, or `--disable` to restore silent B-roll. This
release does not add a fixed audio switch to the editor. Narration remains the
primary audio.

## User Replacement

A user-selected candidate overrides the automatic default for that shot. Keep
alternatives available. `refresh-broll` runs only after an explicit material
redo and preserves narration, HTML, avatar, voice, and local uploads.

## Boundary

[content-orchestration.md](content-orchestration.md) decides what footage is
needed. This contract chooses the provider result. HTML reference selection does
not participate in retrieval.
