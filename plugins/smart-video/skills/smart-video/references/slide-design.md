# Slide Design

Design each Slide directly from the locked whole-video MASTER and the current
shot's source-bound intents. A Slide is the HTML overlay layer in the video, not a
web page, application screen, or standalone animation.

## Inputs

Require:

- unchanged `MASTER.md`;
- shot type and duration;
- exact narration and screen-authorized copy;
- Communication Intent;
- Visual Intent;
- the exact whole-video and current-shot Art Direction embedded in `MASTER.md`;
- source evidence and structured data when applicable;
- current npm `authoring_context` and background rule.

Stop when an input conflicts or lacks the facts needed for the intended
relationship. Do not repair meaning in the design layer.

## Design Method

1. Read the current shot's Art Direction. Treat it as visual authority while
   preserving the Communication and Visual Intents as semantic authority.
2. State the single idea the viewer must retain at the stable final frame.
3. Identify the minimum supplied objects and relationships needed to express it.
4. Realize the directed composition without reclassifying the relationship or
   replacing it with a familiar layout.
5. Establish one dominant visual anchor and one unambiguous reading path.
6. Apply the MASTER palette, type roles, spacing rhythm, material, and motion
   character.
7. Remove labels, containers, icons, lines, and decoration that do not clarify the
   information.
8. Verify the final frame communicates the complete meaning without relying on
   motion history.

Do not reuse one layout merely for consistency. Consistency comes from the
MASTER; composition comes from the shot's semantics.

Stop when Art Direction contradicts a supplied fact, relationship, render mode,
priority, presentation order, or semantic timeline. Do not silently reinterpret
either authority.

## Visual Quality

- Prefer one clear visual sentence over a dashboard of small facts.
- Use scale, position, grouping, alignment, and contrast before adding containers.
- Avoid generic card grids, browser chrome, app navigation, CTA sections, form
  patterns, ornamental labels, and decorative charts.
- Use inline SVG when a relationship is clearer as geometry than as boxes and text.
- Keep text concise but never remove a source-required qualifier, unit, uncertainty,
  or attribution.
- Keep charts focused on the data relationship; do not chart isolated values.
- Use whitespace deliberately. Empty space must support hierarchy, not reveal an
  unfinished composition.
- Keep accents scarce enough that the primary focus remains obvious.

## Safe Area

Every Slide uses the safe area from its locked MASTER.

For `16:9` at `1920x1080`:

```text
top: 64px
right: 96px
bottom: 64px
left: 96px
```

Use these as content insets, not as a visible frame.

For `9:16` at `1080x1920`:

```text
top: 96px
right: 54px
bottom: 96px
left: 54px
```

Use the `avatar_html` shot's final Avatar placement. A missing
`avatar_placement` means the runtime's default lower-right region; a present field
is the user's requested override. Keep the primary claim, critical values, and
essential relationship outside that region during authoring, but do not turn this
guidance into a hard post-authoring rejection gate. Do not draw an Avatar
placeholder. B-roll creates no additional safe area.

## Composition Profiles

| Shot type | Backdrop opacity | Layer relationship |
| --- | ---: | --- |
| `html_only` | `0.95-0.99`, default `0.99` | Slide is self-contained |
| `avatar_html` | `0.95-0.99`, default `0.99` | Avatar remains above the Slide |
| `broll_html` | `0.20-0.55`, default `0.35` | B-roll remains recognizable below the Slide |

Apply opacity only to `.mg-backdrop`. `.mg-content` remains fully opaque. The
backdrop must never reach `1.00`.

## Slide Motion Intent

Motion exists to control reading order and explain change. Use only the phases
needed by the shot, such as establish, relate, focus, resolve, and hold.

Read the Visual Intent's `semantic_timeline` before designing motion. Each cue's
exact `narration_anchor` determines when its `visual_target` becomes eligible to
appear. Convert its relative position with:

```text
delay_seconds = start_ratio * duration_seconds
```

Keep cue order unchanged. Do not reveal a later target before its narration
anchor, and do not place all cues near zero merely to finish entrances early.
Begin the complete stable frame at `stable_hold_start_ratio * duration_seconds`.

- Keep one anchor stable.
- Animate transform and opacity; inline SVG may also use finite stroke progress.
- Complete each entrance after its semantic cue and early enough to reach the
  declared stable hold.
- Never loop, scroll, depend on hover, use random timing, or hide final meaning in
  an intermediate frame.
- Do not animate every object independently when grouping communicates the same
  relationship more clearly.

The LLM authors CSS motion for HTML/SVG. For ECharts, it authors declarative data
and transition intent only; the existing runtime owns JavaScript and timing.

## Handoff

Preserve the director's `render_mode`. Use [html-authoring.md](html-authoring.md)
for `html_svg` and [echarts-authoring.md](echarts-authoring.md) for `echarts`.
Never switch modes because authoring fails.
