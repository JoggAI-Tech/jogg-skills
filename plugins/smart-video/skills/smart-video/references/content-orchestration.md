# Content Orchestration

This is the content-planning contract for new Smart Video runs. Internal
schema identifiers are implementation details; do not expose them as product
versions or ask users to choose one.

## Pipeline

```text
topic and references
  -> compact public Brief
  -> user confirmation
  -> hidden outline + semantic shot skeleton
  -> section-batched narration and visual strategy
  -> user confirmation with subtitle choice
  -> HTML-ready semantic requests for information-layer segments
  -> Smart Video production payload
```

The npm-managed content-planning pipeline is authoritative. Its host adapter is the
only boundary into the existing Smart Video project payload.

## Brief And Hidden Outline

Normalize topic, references, audience, tone, language, and target duration.
Generate only the compact public Brief before confirmation.

```text
confirmed Brief revision N -> hidden outline revision N -> storyboard binds both
```

A Brief edit before confirmation does not generate an outline. After confirmation,
a changed Brief invalidates its previous outline and Storyboard. Reject stale
expected revisions before a model call. Expose only the public Brief view; never
expose the outline, revisions, raw prompts, or private orchestration.

## Script And Shot Orchestration

Plan the complete semantic shot skeleton before finalizing section narration.
Shots use exactly one strategy:

- `avatar_only`
- `broll_only`
- `avatar_broll`
- `avatar_html`
- `broll_html`
- `html_only`

Every shot has a purpose, planned duration, final narration, selected strategy,
alternatives, selection reason, and timed visual segments. Boundaries follow a
complete information action rather than an arbitrary timer. Shots may exceed 15
seconds and are protected only by a hidden 60-second safety limit. TTS-measured
actual duration later replaces planned duration on the final timeline.

Once accepted, the orchestration is authoritative. Runtime normalization and
voice-duration hydration preserve every shot's `shot_type`, `scene_role`, order,
and independent `clip_id`. Adjacent `html_only`, `broll_html`, and `avatar_html`
shots are valid. The runtime must not insert presenter-only or B-roll-only shots
to satisfy a diversity ratio; diversity remains a planning preference, and an
explicit user edit overrides that preference.

`avatar_html` requires avatar and Slide segments. `broll_html` requires B-roll
and Slide segments. `html_only` has no avatar or B-roll dependency and uses the
layer order `html, captions`. Present these three types to users as `Avatar +
Slide`, `B-roll + Slide`, and `Slide Only`. Choose `html_only` for self-contained comparisons,
timelines, processes, data relationships, systems, maps, evidence, or structured
highlights when footage and presenter presence add no meaning. Do not use it for
connective narration. Only HTML segments enter the semantic-to-visual handoff.

## Public Storyboard Contract

Project the public Storyboard from the existing shot plan without another model
call. Before displaying it, verify that the complete plan satisfies every explicit
media requirement in the confirmed Brief; for example, a Brief that requires
Slides cannot produce an all-Avatar or all-B-roll Storyboard. Each displayed shot
must include:

1. Shot number and a readable title from its existing purpose.
2. The user-facing type mapped from the exact production `shot_type`.
3. The current planned duration, never a fixed 5-second or 15-second display value.
4. The complete narration script, never a summary or excerpt.

Keep visual intent, visual segments, B-roll search intent, and Slide semantics in
the private planning bundle. They remain available to the Skill's authoring and
production phases but are not fields in the public Storyboard.

Use exactly these mappings:

| Internal type | User-facing type |
| --- | --- |
| `avatar_only` | `Avatar Only` |
| `broll_only` | `B-roll Only` |
| `avatar_broll` | `Avatar + B-roll` |
| `avatar_html` | `Avatar + Slide` |
| `broll_html` | `B-roll + Slide` |
| `html_only` | `Slide Only` |

Show `Subtitles: No / Yes` after all shots and default it to `No`. Brief and
Storyboard confirmations are independent. A confirmation applies only to the
last complete public checkpoint shown to the user. An incomplete Storyboard
cannot be confirmed, and production cannot start before complete Storyboard
confirmation.

After confirmation, project the same shot types, order, scripts, and planned
durations into production. Do not silently rewrite them for diversity, break up
consecutive Slide shots by inserting Avatar or B-roll, or let runtime defaults
replace confirmed types. If a confirmed shot cannot be produced, identify that
shot and ask for a decision instead of silently degrading it.

## B-roll Intent

Every B-roll segment provides two to four ordered English stock-footage queries.
The first is most specific; later queries relax context without changing the
subject. Each describes a visible subject, action, setting, and known place or
period. Do not use narration sentences, abstract claims, or camera jargon.

The payload also includes:

- `must_include`: visible concepts that shape retrieval;
- `exclude`: wrong subjects, formats, geography, or periods;
- `search_language: en` for provider compatibility.

Avoid duplicate adjacent primary queries during planning, but treat this as a
local diagnostic rather than a whole-Storyboard failure. Retrieval and replacement
behavior is defined in [broll-selection.md](broll-selection.md).

## Single-Shot Edits

Accept natural-language edits to one shot's type, duration, script, or visual
intent. Replan only the changed shot and lock a user-selected type. Preserve every
other shot's ID, type, script, order, and planned duration. A visual-only edit
preserves narration exactly. Changing a non-Slide type to `Avatar + Slide`,
`B-roll + Slide`, or `Slide Only` creates an HTML-ready narration proposal for
that shot only and requires user confirmation before replacement. A B-roll edit
regenerates ordered search intent for that shot only.

After any shot edit, show the complete updated Storyboard again, including the
subtitle choice, and wait for a new Storyboard confirmation before production.

## HTML-Ready Gate

Every HTML segment must satisfy:

- the information task is highlights, compare, timeline, process, data,
  systems, maps, or evidence;
- the narration binding is an exact meaningful substring of narration;
- one primary claim is present;
- required entities, relations, evidence, or structured data are present;
- the HTML window is at least 2.5 seconds and remains inside its shot;
- semantic input contains no palette, layout, motion, font, typography, or
  template instruction.

Do not invent facts to make a shot eligible. Use a non-HTML strategy or return
`needs_script_revision` when the source cannot support a concrete information
object.

## Handoff

After confirmation, emit one `HtmlGenerationRequest` per HTML segment with
stable shot/segment IDs, segment-relative timing, source-bound semantic content,
shot type, and background rule. Content planning must not choose a palette,
composition, visual profile, or animation. Continue with
[visual-reference.md](visual-reference.md).

Project the confirmed bundle with
`build_smart_video_planning_payload(planning, orchestration, visual_decisions, ...)`.
This is the only authoritative projector. Never manually translate the Storyboard
or guess key names. Keep the hidden outline, revisions, raw prompts, and private
orchestration beside the plan rather than in frontend or project payloads.

The projected public planning file uses these exact underscore keys:

```text
topic
production_format
target_duration_seconds
selected_production_option
producer_analysis
production_requirement_document
script_director
script
creative_plan
director_document
scene_groups
```

`script` is one aggregate narration string. It is never an object containing
`shots`. `scene_groups` is a non-empty array; every `scene_groups[].shots[]` item
is a complete shot object, never a shot ID. Each shot contains:

```text
id
title
narration
duration_seconds
shot_type
scene_role
visual_role
broll_prompt
asset_search_plan
information_layer
mg_director
html_design
```

Use `shot_type`, never `type`. Do not substitute `producer`, `requirement`, or
`director` for their canonical top-level documents. A Slide-capable shot also
contains an enabled `information_layer`, the current `semantic_mg_director`
contract with stable `clip_id`, semantic `scene_id`, `story_contract`,
`information_object_plan`, `visual_reference`, `screen_slots`, timing and
background rule, plus a matching `html_design.clip_id`. These remain private
production inputs and are not added to the user-visible Storyboard.

Save the projected object to `<workspace_dir>/plans/production-plan.json`, then
pass that path to `run`. The runtime validates it before creating a project or
submitting paid media. Treat `blocked_planning` as a resumable correction state:
fix the exact reported JSON path and resume with the corrected planning file.
Imported historical directors remain readable and are never migrated
automatically.
