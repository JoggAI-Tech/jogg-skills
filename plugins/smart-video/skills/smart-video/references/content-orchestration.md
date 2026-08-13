# Content Orchestration

This reference owns the path from source material to a confirmed Smart Video
Storyboard and private production plan. It does not choose colors, typography,
layout, or animation values.

## Pipeline

```text
topic and sources
  -> compact Brief
  -> Brief confirmation
  -> hidden outline and complete script
  -> shot strategy and timed segments
  -> B-roll retrieval intent plus Slide intents
  -> complete public Storyboard
  -> Storyboard confirmation
  -> whole-video MASTER input and production plan
```

## Brief

The public Brief contains:

- goal;
- audience and starting knowledge;
- language;
- evidence boundary and explicit unknowns;
- visual tone expressed as audience-facing qualities;
- target duration;
- aspect ratio, displayed as `16:9` or `9:16`;
- B-roll availability.

Persist these as `goal`, `audience`, `starting_knowledge`, `language`,
`evidence_boundary`, `explicit_unknowns`, `visual_tone`,
`target_duration_seconds`, `aspect_ratio`, and `broll_availability`. Accept only
`16:9` or `9:16`; default to `16:9` when the user does not specify one. Display
the selected value in the public Brief and let the user revise it before Brief
confirmation. Preserve the confirmed value unchanged in the private MASTER input
and production plan.

After the Storyboard is confirmed, derive one concise private `design_domain`
from the confirmed Brief, complete script, and Slide set. It names the actual
audience domain used for UI UX Pro Max product classification, such as `language
learning education`, `financial analysis`, or `healthcare training`; it is not a
style, palette, layout, or customer choice. Keep it hidden and write it only to
the private MASTER input's Brief object. If the confirmed content does not support
one unambiguous domain, stop with `design_domain_undefined`; do not guess or use a
generic product category.

Do not expose implementation fields. A Brief revision invalidates its previous
hidden outline, script, Storyboard, and MASTER input. Never continue from stale
confirmed content.

## Script And Shot Plan

Create the complete outline before finalizing narration. Every shot has a stable
ID, title, purpose, narration, planned duration, one `shot_type`, and timed visual
segments. Use exactly:

- `avatar_only`
- `broll_only`
- `avatar_broll`
- `avatar_html`
- `broll_html`
- `html_only`

Choose a type from the communication need:

- Avatar establishes human presence, trust, emphasis, or direct instruction.
- B-roll supplies concrete real-world context or evidence.
- A Slide explains information structure that footage or a presenter cannot show clearly.
- Combined types are valid only when both media layers contribute distinct meaning.

Do not insert media merely to satisfy a diversity ratio. Preserve a user-locked
type. The requested duration is a planning target; measured output media controls
the final timeline without stretching speech or adding silent filler.

Treat the six types as independent per-shot decisions. Any type may appear at
any position, in any order, any number of times, adjacent to itself, or be absent.
Do not enforce opening or closing placement, sequence patterns, type ratios,
coverage quotas, diversity targets, or minimum/maximum counts. A confirmed
Storyboard is authoritative: never add, remove, split, merge, reorder, renumber,
relabel, or rescale its shots during production projection.

## B-roll Retrieval

For `broll_only`, `avatar_broll`, and `broll_html`, reuse the existing strategy in
[broll-selection.md](broll-selection.md). Produce two to four ordered English
queries with visible subject, action, and setting, plus `must_include`, `exclude`,
`search_language: en`, and `target_aspect_ratio` equal to the whole video. B-roll
remains supporting material.

## Avatar Placement

Apply PiP placement to `avatar_html` and `avatar_broll`. When `avatar_placement`
is absent, use the runtime's default lower-right region. When `avatar_placement`
is present, preserve the user-requested supported region or normalized bounding
box exactly. To restore the default, delete `avatar_placement`.

For `avatar_html`, direct the Slide to keep its primary claim, critical values,
essential relationship, subtitles, and selected-aspect-ratio safe area clear of
the final Avatar region. This is composition guidance, not a post-authoring hard
rejection gate. Rebuild only that Slide when its placement changes; preserve its
narration, shot type, and timing. For `avatar_broll`, change only the compositing
position; it does not regenerate B-roll. `avatar_only` remains full-frame and has
no PiP placement.

## Slide Intents

For `avatar_html`, `broll_html`, and `html_only`, the same director call that
chooses the shot type emits two source-bound objects. Do not add a separate model
call.

### Communication Intent

Require:

- `viewer_before`;
- `viewer_after`;
- `communication_operation`, such as explain, compare, prove, demonstrate,
  correct, warn, summarize, or instruct;
- exact source-authorized facts, entities, steps, evidence, and structured data;
- relationships among those objects;
- expected viewer response;
- exact narration, evidence, data, shot, segment, and time bindings.

Use `communication_operation` for the operation. Keep `required_facts` and
`relationships` as non-empty arrays, and keep `expected_viewer_response` explicit.
The `bindings` object must contain the exact shot narration, `shot_id`, non-empty
`segment_ids`, and an increasing `time_range_seconds` with `start` and `end`.
Include evidence and data identifiers or source objects when they apply; do not
invent empty identifiers for unavailable evidence.

### Visual Intent

Require:

- `render_mode`: `html_svg` or `echarts`;
- one `primary_focus`;
- visual encoding of the source-bound relationship;
- `information_priority`;
- `presentation_order`;
- a narration-anchored `semantic_timeline`;
- simplicity rules stating what to remove or subordinate;
- a complete final-frame requirement;
- the same source and timing bindings as Communication Intent.

The Visual Intent `bindings` object must contain the same `shot_id`,
`segment_ids`, `time_range_seconds`, and every additional source or evidence
binding. Except for Communication Intent's narration-only field, the two binding
objects must be byte-equivalent after canonicalization. Preserve all additional
source-bound fields from both intents. The MASTER builder consumes each complete
object rather than projecting a reduced summary.

Build `semantic_timeline` from the exact shot narration. Use
`basis: narration_relative`, one or more ordered `cues`, and
`stable_hold_start_ratio`. Every cue contains a unique `cue_id`, an exact
continuous `narration_anchor`, the semantic `visual_target`, one phase from
`establish`, `relate`, `focus`, or `resolve`, and a `start_ratio` from 0 to 1.
Place cues in spoken order and set each ratio from its anchor position in the
narration. Do not compress later ideas into the opening seconds. Start the stable
final hold from 0.75 to 0.9 after the final cue.

Visual Intent describes meaning and hierarchy, not appearance. It must not choose
a template, palette, font, coordinates, components, CSS, SVG paths, ECharts
options, easing, or transition duration. The semantic timeline identifies when
spoken ideas become eligible to appear; the authoring layer chooses the finite
visual transition.

If the script cannot support a clear intent, return `needs_script_revision` or
remove the Slide. Never invent content to keep the shot type.

## ECharts Gate

Use `echarts` only when exact structured data is itself the evidence and a chart
materially improves understanding of a trend, comparison, ranking, distribution,
correlation, hierarchy, geography, network, or flow. Preserve labels, values,
units, denominators, order, uncertainty, nodes, links, coordinates, and nulls.

An isolated number, decorative statistic, unbound relationship, incomplete data,
or a chart that adds no clarity is not eligible. Choose `html_svg` only when it is
independently the correct expression, never as a fallback after an ECharts failure.

## Public Storyboard

Display every shot with:

```text
### Shot 03 - How Stress Changes Meaning
Type: Avatar + Slide
Duration: 10s
Script: Content words usually carry the stress that reveals the sentence meaning.
Slide Design: Emphasized content words in one sentence; Relationship: content words versus function words; Order: sentence, contrast, rule.
```

For B-roll shots, add a similarly concise `B-roll` and `Purpose` line. Derive these
lines from the existing structured plan without another model call. Do not expose
raw intents, source IDs, queries, scene IDs, template IDs, MASTER details, render
mode, chart type, or JSON.

After all shots, display `Subtitles: No / Yes`, defaulting to `No`, and wait for
confirmation. A confirmation applies only to the last complete checkpoint shown.
After any shot edit, redisplay the complete Storyboard and request confirmation
again.

## Production Handoff

Project the confirmed plan only through the runtime's authoritative
`build_smart_video_planning_payload(...)` path. Do not hand-build aliases. The
public production object uses `scene_groups[].shots[]` with `shot_type`, not
`type`, and retains the confirmed shot order, narration, and duration.

Preserve the selected `aspect_ratio` and every user-provided `avatar_placement` in
the production plan. These are execution inputs, not visual suggestions. Legal
`16:9`, `9:16`, and supported Avatar positions proceed through the matching npm
execution path; never substitute another ratio or position.

Mark this projection with `planning_authority: confirmed_storyboard`. Derive
Avatar targets from `avatar_only`, `avatar_broll`, and `avatar_html`; B-roll
targets from `broll_only`, `avatar_broll`, and `broll_html`; and Slide targets
from `avatar_html`, `broll_html`, and `html_only`. These sets are independent.
Run new production with `--avatar-mode planned`.

Set the coarse `production_format` to `broll_html` when at least one confirmed
shot contains a Slide; otherwise set it to `broll`. This compatibility field
does not describe the whole video's composition and cannot override `shot_type`.

Every Slide-bearing shot must contain the current semantic director fields and a
stable `clip_id`. For current npm compatibility, its private visual reference is
always:

```json
{
  "reference_mode": "visual_recompose",
  "fallback_automatic": false,
  "free_generation_selected": true
}
```

The semantic `scene_id` and a valid scene-owned `template_id` remain required by
the current projector. Select them only from information shape and runtime
support. They are compatibility locators and must not influence palette,
typography, composition, components, or motion.

Write the exact `runtime_visual_style_profile` object from the locked MASTER
metadata to the whole-video planning document as `visual_style_profile`. This is
the bridge from the MASTER palette to the existing npm `--mg-*` variables. Do not
rewrite, approximate, or replace its values.

Before projection, compile every Visual Intent `semantic_timeline.cues[]` item to
the existing `mg_director.timeline[]` field for the same shot. Set `start_s` to
`start_ratio * duration_seconds`, copy `visual_target` to `target`, copy only
source-authorized screen text to `text`, and map phases deterministically:

```text
establish -> reveal
relate -> connect
focus -> emphasize
resolve -> resolve
```

Keep cue order and three-decimal precision. The resulting
`mg_director.timeline` must contain exactly one item per semantic cue. Stop if the
projector drops, reorders, or changes these items; do not let the HTML author
invent a replacement timeline.

After authoritative projection, author every eligible ECharts spec from the
locked MASTER and the preserved source-bound Visual Intent. Attach the declarative
JSON object to its projected shot as `shot.html_design.echarts_mg_spec` before
`run`. Do not replace the projector, alter the semantic director fields, or add
model-authored JavaScript. The trusted runtime validates the spec and materializes
its HTML during project creation.

After projection, a new Slide must yield:

```text
authoring_context.authoring_mode = full_html_recompose_v1
authoring_context.fidelity = adaptive
authoring_context.reference_mode = visual_recompose
```

If it yields a strict reference checkpoint, the plan is inconsistent with this
production path. Correct the plan before authoring. Do not submit
`strong_reference_patch_v1` and do not use a template as fallback.

Save the completed projection under the workspace `plans` directory and pass it
to `run`. Only ordinary HTML/SVG Slides enter `waiting_html`; new ECharts Slides
must already contain their spec. Fix an exact `blocked_planning` path in the same
workspace; do not alter unrelated confirmed shots.
