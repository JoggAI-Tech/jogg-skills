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
  -> section-batched narration + one director call per batch
  -> B-roll retrieval + separate Communication Intent and Visual Intent
  -> user confirmation with subtitle choice
  -> source-bound semantic requests for Slide segments
  -> Smart Video production payload
```

The npm-managed content-planning pipeline is authoritative. Its host adapter is the
only boundary into the existing Smart Video project payload.

## Brief And Hidden Outline

Normalize topic, references, audience, tone, language, and target duration.
Generate only the compact public Brief before confirmation. Preserve these public
fields through confirmation:

- `goal`: the outcome the video must achieve;
- `audience`: the intended viewers and relevant starting context;
- `evidence_boundary`: authorized sources, claims, data, and explicit unknowns;
- `visual_tone`: a concise audience-facing tone, without design implementation;
- `broll_availability`: whether source-authorized stock footage may be used.

Do not expose or add strategy, prototype, grammar, Visual System, render mode, or
other private design fields to the Brief.

```text
confirmed Brief revision N -> hidden outline revision N -> storyboard binds both
```

A Brief edit before confirmation does not generate an outline. Bind every hidden
outline and later plan to the exact confirmed Brief revision. After confirmation,
a changed Brief invalidates its previous outline and every later plan, including
the Storyboard and director output. Reject stale expected revisions before a model
call. Expose only the public Brief view; never expose the outline, revisions, raw
prompts, or private orchestration.

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

Keep shot type independent from Slide render mode. `avatar_html`, `broll_html`,
and `html_only` may each carry `html_svg` or `echarts` when the semantic gate
permits it. Never create parallel types such as `avatar_echarts` or
`broll_echarts`.

## Director Contract

Use one universal director schema for business, training, tutorial, narrative,
and other content. In the same director call that finalizes the shot strategy,
return B-roll retrieval where allowed and, for every Slide-bearing shot, two
separate objects named `communication_intent` and `visual_intent`. Do not make a
second model call to split the intents.

Require each `communication_intent` to contain:

- `viewer_before`;
- `viewer_after`;
- `communication_operation`;
- `content_objects`: exact source-authorized facts, entities, steps, evidence, or
  structured data;
- `relationships`;
- `expected_response`;
- `source_bindings`.

Require each `visual_intent` to contain:

- `render_mode`: `html_svg` or `echarts`;
- `primary_focus`;
- `visual_encoding`;
- `information_priority`;
- `presentation_order`;
- `simplicity_rules`;
- `final_frame_requirement`;
- `public_projection`;
- `source_bindings`.

In both objects, require the same source-binding shape:

- `narration_excerpt`: an exact meaningful substring of final shot narration;
- `evidence_ids`: exact authorized IDs when evidence applies;
- `data_sources`: exact authorized sources when data applies;
- `shot_time_window`: exact `start_seconds` and `end_seconds`;
- `segment_time_window`: exact `start_seconds` and `end_seconds` inside the shot.

The two intent objects must bind to the same confirmed source, narration revision,
shot, segment, and time window. Never bind to an inferred source or an unconfirmed
script. Derive Communication Intent first and Visual Intent second within the same
director call.

After the complete confirmed Brief and source-bound Slide set exist, run the
separate whole-video `visual-style-semantic-critic@1.0.0`. It emits a controlled
`qualitative_family_intent` with an exact `brief.visual_tone` hash binding, one
resolved family ID or an explicit ambiguity/coverage result, and no concrete
tokens. This is an internal system decision, never a customer family selector and
never part of per-Slide director output. Production must not reproduce this
semantic operation with substring lists or nearest-trait fallback; it validates
the structured result and fails closed when the critic cannot resolve one family.
The critic ID/version is traceability provenance, not authentication or proof of
semantic correctness. The family manifest is consumed only by the internal
whole-video Visual System builder. Public Storyboard and per-Slide requests carry
no family, critic, candidate, or prototype fields; they reference the resulting
locked Visual System artifact by ID, version, and hash.

Emit B-roll and Slide `public_projection` fields in that same director call. Bind
each projection field to its corresponding structured retrieval or intent
semantics in the private source-bound orchestration bundle. Link each projection
record by stable shot ID, stable segment ID, and the same source bindings used by
the corresponding semantics. Treat `public_projection` as display-only input to
the public Storyboard projector. Remove it before semantic selection or any
production handoff; never carry the public text downstream as linkage or use it as
a production semantic input. Do not add a model call.

Allow only a small optional `outcome_fields` object with domain-neutral outcomes
such as `learning_objective` or `user_action`. Do not create industry-specific
fields or parallel schemas. Keep color, typography, visual styling, concrete
composition, pixel geometry, CSS, SVG, JavaScript, and ECharts options out of both
intents.

If authorized source material cannot support a clear `communication_intent`,
return `needs_script_revision` or cancel the Slide. Never guess the communication
purpose or let the visual or design layer invent it.

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

Keep internal relationships and other production semantics in their structured
form; never serialize them directly into the public Storyboard. Use only these
customer-readable projection inputs:

- `broll_retrieval.public_projection.visible_footage`;
- `broll_retrieval.public_projection.supporting_purpose`;
- `visual_intent.public_projection.primary_focus`;
- `visual_intent.public_projection.information_relationship`;
- `visual_intent.public_projection.presentation_order`.

Require every applicable input to be a non-empty, trimmed, single-line scalar
string in the confirmed Brief language. Reject arrays, objects, JSON serialization,
line breaks, leading or trailing whitespace, semicolons, and terminal sentence
punctuation such as `.`, `!`, `?`, `。`, `！`, or `？`. Reject invalid input; do not
normalize, summarize, or rewrite it.

For `broll_only`, `avatar_broll`, and `broll_html`, serialize exactly:

```text
B-roll: {visible_footage}; Purpose: {supporting_purpose}.
```

For `avatar_html`, `broll_html`, and `html_only`, serialize exactly:

```text
Slide Design: {primary_focus}; Relationship: {information_relationship}; Order: {presentation_order}.
```

Use this complete v1 locale map. Accept only the exact, case-sensitive locale
values shown; normalize by exact lookup only.

| Canonical locale | Accepted locale values | B-roll label | Purpose label | Slide label | Relationship label | Order label |
| --- | --- | --- | --- | --- | --- | --- |
| `en` | `en`, `en-US`, `en-GB` | `B-roll` | `Purpose` | `Slide Design` | `Relationship` | `Order` |
| `zh-CN` | `zh-CN`, `zh`, `zh-Hans`, `zh-SG` | `B-roll` | `作用` | `Slide 设计` | `信息关系` | `呈现顺序` |

For normalized `zh-CN`, serialize exactly:

```text
B-roll: {visible_footage}; 作用: {supporting_purpose}.
Slide 设计: {primary_focus}; 信息关系: {information_relationship}; 呈现顺序: {presentation_order}.
```

Keep public field values in the confirmed Brief language. Preserve the approved
field order, fixed delimiters `: ` and `; `, and exactly one final period for both
canonical locales. For any locale outside the exact map and alias set, block public
Storyboard projection and show this untyped blocking message: `Cannot display the
Storyboard for locale "{locale}". Supported Storyboard locales: en, zh-CN.` Never
fall back to English and never model-generate labels or lines. Omit a line when its
medium is absent; reject the plan when a required projection field is missing.

Keep raw intents, visual segments, queries, evidence IDs, strategy choice,
prototype, grammar, Visual System, `render_mode`, chart type, and implementation
details in the private planning bundle. Do not expose JSON or internal intent names.
The two projected descriptions are customer-facing views only and must never be
read back as production inputs.

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

End the Storyboard with: `You can confirm the Storyboard or change any shot's
type, duration, script, B-roll, or Slide Design where present.` Accept
natural-language changes, but never ask the user to choose a strategy, design
mode, template, palette, render mode, or chart type.

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

Accept natural-language edits to one shot's type, duration, script, B-roll, or
Slide Design. Replan only the changed shot and lock a user-selected type. Preserve
every other shot's ID, type, script, order, and planned duration. A visual-only edit
preserves narration exactly. Changing a non-Slide type to `Avatar + Slide`,
`B-roll + Slide`, or `Slide Only` creates a Slide-ready narration proposal for
that shot only and requires user confirmation before replacement. A B-roll edit
regenerates ordered search intent for that shot only.

After any shot edit, show the complete updated Storyboard again, including the
subtitle choice, and wait for a new Storyboard confirmation before production.

## Slide Input Gate

Every Slide segment must satisfy:

- the information task is highlights, compare, timeline, process, data,
  systems, maps, or evidence;
- the narration binding is an exact meaningful substring of narration;
- one primary claim is present;
- entities and relations required by the intent are present;
- exact authorized evidence and structured data are present only when the content
  or intent depends on them;
- the HTML window is at least 2.5 seconds and remains inside its shot;
- semantic input contains no palette, layout, motion, font, typography, or
  template instruction.

Do not invent facts to make a shot eligible. Cancel the Slide for that shot or
return `needs_script_revision` when the source cannot support a concrete
information object.

## ECharts Semantic Gate

Permit `visual_intent.render_mode: echarts` only when exact source-authorized
structured data expresses a chart-worthy trend, comparison, ranking,
distribution, correlation, hierarchy, geography, network, or flow and a chart
materially improves understanding of that relationship. Preserve labels, values,
units, denominators, order, uncertainty, nodes, links, coordinates, and nulls as
supplied by the source.

Reject `echarts` for isolated numbers, mere numeric mentions, unsupported inferred
relationships, contradictory or incomplete data, or a chart that adds no clarity.
Use `html_svg` only when it is independently valid for the confirmed intent; do
not treat it as a fallback for a failed ECharts plan. Planning emits no ECharts
option, HTML, CSS, SVG, or JavaScript.

## Contract Validation

Validate the same universal director contract against representative business,
training, tutorial, and narrative shots. Do not create four schemas.

| Example | Source-bound relationship | Valid outcome |
| --- | --- | --- |
| Business | Multi-period trend or category comparison | `echarts` only with complete authorized data |
| Training | Rule, consequence, or before/after understanding | `html_svg`; optional `learning_objective` |
| Tutorial | Ordered steps and resulting user action | `html_svg`; optional `user_action` |
| Narrative | Timeline, cause, contrast, or turning point | `html_svg`, or `echarts` only with qualifying structured data |

Before accepting a director plan, enforce all of these checks:

- Reject B-roll fields unless `shot_type` is `broll_only`, `avatar_broll`, or
  `broll_html`, and reject a B-roll shot when confirmed `broll_availability`
  disallows it.
- Reject Slide fields unless `shot_type` is `avatar_html`, `broll_html`, or
  `html_only`, and require them for each of those types.
- Reject `echarts` when the source supplies only an isolated number or fails any
  semantic gate condition.
- Reject either intent when its exact narration, evidence/data when applicable,
  shot time, or segment time binding is absent, stale, outside the shot, or
  inconsistent with the other intent.
- Reject any public Storyboard projection that exposes design strategy, benchmark,
  prototype, grammar, Visual System, render mode, chart type, internal intent
  names, source IDs, queries, JSON, or implementation fields.

## Handoff

After confirmation, emit one private source-bound planning request per Slide
segment with stable shot/segment IDs, segment-relative timing, semantic content,
shot type, and background rule. Content planning must not choose a palette,
composition, visual profile, or animation. Continue with
[visual-reference.md](visual-reference.md). Do not claim that a runtime persists
or executes the new intent or Slide design contracts until its direct readiness
challenge succeeds.

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

Save the projected object to `<workspace_dir>/plans/production-plan.json`. After
runtime readiness succeeds, pass that path to `run`. The runtime validates the plan,
creates the project, and stops at `waiting_html` before paid media. Author and
submit each new Slide through its dedicated route; do not use legacy `apply-html`
or `apply-echarts`. Missing adapter, persistence, render, or attestation facts stop
with `unsupported_render_runtime`.
Treat `blocked_planning` as a resumable correction state: fix the exact reported
JSON path and resume with the corrected planning file. Imported historical
directors remain readable and are never migrated automatically.
