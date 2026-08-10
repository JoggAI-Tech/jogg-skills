# Visual Reference

This layer validates the complete qualitative visual input and produces system-owned
grammar and prototype decisions. The customer supplies neither `grammar_id`,
`prototype_id`, numeric visual targets, nor concrete styling.

Read [visual-knowledge.md](visual-knowledge.md) for the measured libraries and
[slide-design.md](slide-design.md) for compilation and Slide design.

## Authoritative Input

`visual_system_input` is immutable and contains:

- the complete confirmed Brief: topic, goal, audience, evidence boundary,
  qualitative visual tone, B-roll availability and note, language, `16:9`, and
  confirmed revision;
- the complete source-bound semantic Slide set;
- for every Slide: narration, source excerpt, primary claim, content objects,
  Communication Intent, director Visual Intent, exact source bindings and data
  where applicable, shot/background, duration, explicit rules, and rule results;
- current local runtime capabilities, compatibility/risk results, and exact
  grammar/prototype asset versions and hashes.

Director Visual Intent must preserve controlled
`communication_operation_enum`, `primary_relationship`,
`secondary_relationships`, `visual_encoding_enum`, `render_mode`,
`primary_focus`, `information_priority`, `presentation_order`,
`simplicity_rules`, `final_frame_requirement`, and `source_bindings`.
Relationships bind roles to stable content-object IDs and exact authoritative
content spans. Concrete style remains outside director output.
Director Visual Intent owns information priority and presentation order; the
Visual System compiler owns concrete styling decisions.

Reject `public_projection`, caller grammar/prototype IDs, caller numeric target
intervals, semantic summaries used in place of complete objects, unsupported
ratios, incomplete Slide sets, stale hashes, incompatible explicit rules, missing
runtime capabilities, and hard risk conflicts. Fallback is forbidden.

## Semantic Critic

For each Slide:

1. Validate every content object and role against an exact source binding.
2. Validate each relationship evidence span against the authoritative narration,
   excerpt, claim, or content-object text.
3. For `paired_metric`, `target_actual`, and `parts`, require every role to bind a
   distinct structured source fact. Its source binding carries the exact canonical
   metric ID, display name, dimension, and unit; those fields must equal the fact,
   and the display name/unit/value must occur in the bound role text. A declared
   `subtract` or `sum` equation must reconcile in one shared identity and unit. A
   `divide_percent` equation instead requires exactly two same-identity operands, a
   strictly positive denominator, and one distinct source-bound `ratio`/`percent`
   result. Every ratio fact must carry the exact source-bound field
   `"uncertainty": "approximate_from_source"`; free-text approximation is not
   evidence. Its
   strict `{ "mode": "rounded", "decimal_places": d }` comparison must match the
   result text's numeric-token precision and places the computed percentage in
   `[result - 0.5 * 10^-d, result + 0.5 * 10^-d)` with no extra tolerance or conversion.
4. Compare the controlled operation, relationship kind, direction, ordered roles,
   and visual encoding against the full approved 18-family topology library.
   Validate `html_svg` or `echarts` separately as the controlled author mode and
   lock it into the whole-video artifact's per-Slide binding.
5. Require exactly one signature.
6. Criticize that controlled classification against the actual authoritative
   content. A chronology classification requires one structured event record per
   role object, with an exact source pointer and span, a shared chronology identity,
   an explicit finite normalized order value, and a distinct source-bound ordering
   statement. The validator checks strict ordering against the relationship role
   sequence. Unrelated date or edition-year mentions cannot establish chronology.
7. For correction, definition, question/resolution, process, causal, network,
   evidence, spatial, hierarchy, cycle, transformation, rank, distribution, and
   trend operations, require one typed relation record plus distinct source-bound
   participant records. Validate exact participant order, topology fields,
   cardinality, cycle closure, and authoritative relation statement. A keyword in
   unrelated text is not relationship proof.
8. Emit `grammar_id` and grammar provenance as system output.

This critic does not claim deterministic natural-language understanding. It checks
complete object binding, controlled taxonomy, exact provenance, and supported
semantic evidence. Ambiguous or weakly supported content is omitted through
`coverage_gap_no_grammar`; it is never patched or relabeled to pass.
The critic ID/version tuple is provenance only. It is not cryptographic
authentication and does not prove that a model understood the text.

## Prototype Selection

After all Slides have a grammar, the system derives one whole-video semantic design
profile from the qualitative Brief and measurable structure: object, relationship,
priority, and order counts; text load; duration; background modes; structural
operations; and restrained-tone signals.

The selector compares that profile with all four evidence-qualified measured
prototype profiles. It selects the unique normalized minimum, returns
`coverage_gap_no_prototype` when no qualified candidate exists, and returns
`ambiguous_visual_system_intent` for an equal best score. It has no topic,
industry, category, benchmark, population, prototype-ID, or fallback tie-break.
The selected ID and candidate scores are system outputs recorded in provenance.

The four prototypes are macro structural anchors, not four finished styles. The
compiler also consumes the current aggregate synthesis-trait asset: 24 Visual
System catalog records were reviewed, 18 directly support reusable catalog
observations, 30 reference layouts and 216 scene candidates provide measured
envelopes across palette, typography, material, geometry, and motion, and six
component-only Visual System records remain an explicit coverage gap. Only
directly persisted catalog palette and typography fields are treated as
whole-system evidence; material, geometry, and motion claims keep their true
layout evidence level. Concrete tokens are newly generated from the complete
Brief, complete semantic Slide set, strategy, and selected structural envelope;
source colors, font names, markup, and compositions are not copied.
The qualitative census retains 16 executable families and records
`crimson-night-glass` and `jewel-deco` as coverage gaps. It asserts no measured
redundancy exclusions. Family applicability and mutual exclusions are executable
through a source-bound family identity emitted by an upstream system semantic
critic. The production selector validates the exact tone hash and accepts exactly
one retained family; ambiguous, unsupported, unresolved, or stale results fail
explicitly. It does not parse tone with literal substrings or substitute a nearest
cross-family trait combination. The validator proves object binding and controlled
identity, not deterministic natural-language understanding.

`html_only`, `avatar_html`, and `broll_html` remain supported environments.
Their backplate adaptation is a normative Slide Design obligation, not empirical
prototype qualification and not a reason to eliminate every prototype.

## Provenance

The system computes hashes internally from the actual Brief and semantic Slide
objects. Generated provenance records:

- current grammar, prototype, and synthesis-trait asset hashes;
- exact Brief and semantic Slide-set hashes;
- each system-generated grammar ID, signature evidence ID, semantic input hash,
  relationship-evidence hash, and critic source;
- the system-selected prototype and selector version;
- the canonical production design strategy.

Provenance is generated inside the compiled Visual System. The production request
does not accept a caller-authored provenance object or hash as authority. The
manifest carries the compiled system's `selection_provenance_sha256` and current
`expression_grammar_version`.

The internal builder API is not the public render boundary. A public per-Slide
request carries only the locked Visual System `id`, `version`, and exact artifact
SHA-256. The CLI and reusable request validator accept only one immutable raw
artifact byte snapshot, compute its SHA-256 internally, parse duplicate-safe JSON
from those same bytes, and retain an independent copy of the validated locked
object. They do not accept a parsed object and caller hash as separate authority.
The current Slide's source hashes, shot type, render mode, and duration are then
checked against its compiled binding. Per-Slide requests and the public
Storyboard never expose family candidates, critic IDs, prototype IDs, or complete
Visual System inputs.

## Strategy

Production uses only `smart_video_slide_design@1.0.0` with `production_default`.
Independent design comparisons are ingested as external audit snapshots after exact
dependency and source-output hashing; they are not Visual Systems and cannot enter a
production request, manifest, author artifact, render report, or compiler call.

## Prohibitions

- No template recovery, catalog fallback, strategy switching, or patch-style
  bypass.
- No caller prototype, grammar, interval, palette, typography, material, or motion
  control at this boundary.
- No copied source HTML, CSS, SVG, private server paths, source visual tokens, or
  unsupported facts.
- No single-Slide substitute for the complete confirmed Slide set.
- No claim that one prototype is universally better or that full-data cluster
  labels are held-out truth.
