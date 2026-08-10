# Slide Design

This dedicated layer turns confirmed Smart Video meaning into an authoring-ready
Slide design contract for information overlays above Avatar or B-roll and for
Slide-only shots. It is not a web-page designer, template resolver, HTML author,
runtime executor, or independent animation product.

Read [visual-knowledge.md](visual-knowledge.md) and
[visual-reference.md](visual-reference.md) first. This layer has exactly two
operations: `compile_visual_system` and `design_slide`.

## New And Legacy Precedence

For every new Slide that has a Slide design contract, that contract is authoritative
for Communication Intent, Visual Intent, composition semantics, Visual System,
render mode, and motion intent.

Current runtime `authoring_context` may contribute only still-supported execution
facts: stable IDs, ratio, duration, layer order and background capability,
safe-area and canvas bounds, checkpoint state, and capture settings. It must not
override, replace, or infer design choices. Resolve a conflict through the Failure
Decision Table; runtime data never wins by precedence.

Imported legacy clips without a new Slide design contract remain a separate
compatibility path. Do not create a new contract for them implicitly, apply new
precedence retroactively, or auto-migrate them.

The controlled v1 contract requires separate `html-author` and `echarts-author`
endpoints plus an approved runtime identity and post-render attestation. The
bundled runtime implements those capabilities, but the running service must answer
the Skill validator's fresh loopback nonce with its exact verified identity,
routes, and capabilities. A
missing endpoint, caller-authored report, redirect, hash mismatch, or replay
returns `unsupported_render_runtime`; it never permits a legacy path. This local
challenge has the explicit trust boundary in [runtime-boundary.md](runtime-boundary.md).

## Canonical Strategy Contract

Every machine contract uses exactly:

```yaml
design_strategy:
  id: smart_video_slide_design
  version: 1.0.0
  selection_source: production_default
```

This is the only strategy tuple accepted by production schemas and validators.
Independent comparison output is an external audit snapshot, not a second
production strategy. Its ingestion boundary verifies the exact ui-ux-pro-max
dependency tree and exact MASTER output hash, and prohibits prototype IDs, trait
selection, or a production Visual System object. Production never compiles, accepts,
or converts that snapshot. The public Storyboard exposes no strategy selection.

## System-Owned Selection Provenance

`selection_provenance` is compiler output, not a caller input. The system derives
it from the complete `visual_system_input`, generated grammar decisions, generated
prototype selection, current library hashes, and canonical strategy. It carries
exact Brief, semantic Slide-set, relationship-evidence, and compiler-input hashes.
The manifest copies only the compiled system's `selection_provenance_sha256`.

The compiler hashes provenance with its documented JCS-safe domain and validates it
inside the locked Visual System. A caller cannot replace provenance, assert a
compiler hash, or use a self-reported count/hash summary as authority.
These hashes and the semantic-critic ID/version are traceability controls, not
cryptographic authentication or proof of natural-language understanding.

## Operation: compile_visual_system

This internal builder-only operation is the only owner of whole-video Visual
System compilation. It is not exposed by the public per-Slide validate/render CLI.
Require:

- one immutable `visual_system_input` containing the ordinary qualitative
  confirmed Brief and complete source-bound semantic Slide set;
- one system-generated `qualitative_family_intent` emitted by the upstream
  `visual-style-semantic-critic@1.0.0`, bound to the exact confirmed
  `brief.visual_tone` hash, and resolved to exactly one controlled retained family;
- every Slide's confirmed Communication Intent and director Visual Intent,
  including exact relationship evidence spans;
- every Slide background, finite positive duration, simplicity rules,
  final-frame requirement, and source bindings;
- ratio exactly `16:9`;
- current grammar/prototype asset versions and hashes;
- the sole canonical production `design_strategy`.

Reject `public_projection`, caller `grammar_id`, caller `prototype_id`, caller
numeric target intervals, caller provenance, and stale `visual_system_input_sha256`.

The operation runs the semantic critic, derives the whole-video semantic design
profile, selects exactly one evidence-qualified prototype or returns an explicit
coverage/ambiguity code, creates selection provenance, and generates concrete
tokens. A single Slide cannot substitute for a known multi-Slide video.

Natural-language family interpretation belongs to that upstream semantic critic,
not to the deterministic production validator. The validator checks the exact tone
binding, critic provenance tuple, controlled census identity, resolution cardinality, and
applicability boundaries. It returns `ambiguous_visual_style_traits` for multiple
formal candidates and `coverage_gap_no_style_traits` for unsupported or unresolved
results. It never uses literal-substring family matching, nearest-family selection,
or composable trait substitution.

For `paired_metric`, `target_actual`, and `parts`, the semantic critic requires a
closed source-bound metric relationship. Every role resolves through an exact JSON
Pointer to a distinct numeric fact; source binding and fact must agree on canonical
metric ID, display name, dimension, and unit; the bound role text must carry that
display name, unit, and only that value. Declared `subtract` and `sum` equations
retain their shared-identity, shared-unit arithmetic contract. A `divide_percent`
equation has exactly two operand roles and one distinct result role: both operands
share all identity fields, the denominator is strictly positive, and the result is
a distinct source-bound structured metric with dimension `ratio` and unit `percent`.
Every ratio fact must carry the exact source-bound field
`"uncertainty": "approximate_from_source"`; free-text approximation is not evidence. Its only
comparison form is `{ "mode": "rounded", "decimal_places": d }`; `d` must equal
the result text's numeric-token precision, and decimal arithmetic must place
`numerator / denominator * 100` in
`[result - 0.5 * 10^-d, result + 0.5 * 10^-d)`. No extra roles, tolerance, unit
conversion, inferred complement, or fallback are allowed. The validator proves
this object binding and arithmetic contract; it does not infer metric identity or
unit compatibility from broad words.

For `chronology_schedule`, date-like text is never relationship proof. Each role
event must resolve through an exact JSON Pointer to a distinct chronology fact whose
label and display time occur in that role object's exact evidence span. All facts
must share one chronology identity and strictly ordered finite normalized values.
A separate source-bound ordering record must list the same event IDs and roles in
the same direction and bind its relation statement to authoritative content.

The remaining qualitative topology operations require a
`smart-video.source-bound-formal-relationship.v1` record from the upstream
semantic critic. Every role object resolves through a distinct participant source
record; the relation record must reconcile the exact participant IDs and order,
operation-specific relation type, relationship kind, direction, role/object
cardinality, cycle closure, and an exact authoritative relation statement. Broad
keywords are never relationship proof. The deterministic validator proves these
formal bindings, not natural-language understanding or critic authenticity.

Successful output is one locked whole-video Visual System with schema ID
`smart-video.visual-system.v1` that validates against
`assets/contracts/visual-system.v1.schema.json` and contains:

- stable system identity, version, `locked: true`, and `aspect_ratio: 16:9`;
- immutable system-generated prototype selection, system-generated
  `selection_provenance`, and `selection_provenance_sha256`;
- concrete implementation-ready color tokens for surface, text, emphasis, muted,
  alert, and chart roles;
- concrete local font stacks and role sizes for display, title, body, label,
  numeric, and source content;
- concrete spacing scale, density budget, grouping policy, and safe-area values;
- concrete material, shape, edge, connector, depth, and restraint tokens;
- concrete ECharts tokens for series, text, axes, grid, marks, and labels;
- concrete motion timing ranges and final-hold limits;
- a decision trace covering the qualitative Brief, complete Slide IDs, semantic
  profile, candidate scores, selected prototype, background adaptation, measured
  prior evidence, verified runtime capabilities, hard quality gates, and one
  source/environment binding for every Slide;
- explicit generated-decision provenance with `source_token_copy: false`.

The schema requires concrete palette and chart role values, visible-role and
dominant-color targets, contrast targets, six typography roles with local font
stacks/sizes/weights, spacing/grouping/safe areas,
density/alignment/largest-object targets, material/shape/edge/connector/restraint
tokens and count priors, complete ECharts series/text/axes/grid/marks/labels
tokens, motion ranges, and final hold. A semantic-only object is invalid. The
Skill validator checks schema conformance, hierarchy, local-only font stacks,
ordered ranges, complete evidence trace, and every concrete same-metric token
binding.

Measured ranges are design boundaries, not caller facts and not exact token
prescriptions. Generate concrete choices from the complete qualitative/semantic
input inside those boundaries and record token provenance. Exact colors, fonts,
spacing, and styles remain system design decisions; validators check binding,
ranges, actual contrast, local resources, non-overlap, and stable final hold.

Semantic load controls density through one documented monotonic formula. Clamp
effective load to `4..400`, map group gap linearly from `32.00px` down to
`20.00px`, and derive section gaps and safe areas from that value. At two-decimal
precision every adjacent integer load in the effective range must produce a
distinct smaller group gap. Do not use input hashes to perturb font sizes or
spacing.

Accessibility, local-only execution, final-hold stability, source fidelity, and
non-overlap are mandatory independent gates. Fonts and assets must be local. Do
not copy an exact source palette, font declaration, markup, or source-specific
token set. Do not introduce a technique absent from both measured supported
dimensions and verified local capabilities.

Resolve the system once against the complete video. Background adaptation for
`self_contained_slide`, `avatar_visible_backplate`, and
`broll_visible_backplate` is normative capability and does not masquerade as
prototype evidence. Do not emit per-Slide geometry or per-Slide motion here.

## Operation: design_slide

Require one locked Visual System from `compile_visual_system`, its internally
validated `selection_provenance_sha256`, and one Slide's complete confirmed
source and narration, Communication Intent,
grammar-resolved Visual Intent, grammar, background, duration, and `16:9` ratio.
Also require exact authorized evidence and structured data when the confirmed
content or intent depends on them.

At the public boundary the per-Slide request carries only the locked system
`id`, `version`, and SHA-256. The CLI reads a separate locked artifact, verifies
the exact artifact bytes, and passes that immutable byte snapshot to the reusable
validator. The validator computes SHA-256 internally, duplicate-safe parses the
same bytes, validates the complete Visual System, and retains an independent copy
before checking this Slide's source-content hash, source-data hash, shot type,
render mode, and duration against the corresponding compiled binding. A parsed
Visual System plus caller-supplied hash is not an accepted API. A public request containing family,
critic, prototype, or whole-video compiler input fields is schema-invalid.

The locked Visual System must validate against `smart-video.visual-system.v1` and
include every concrete implementation-ready token group. A semantic-only system
is invalid and maps to `blocked_missing_locked_visual_system`.

Reject any `design_slide` input containing `public_projection`. Preserve linkage
through stable shot/segment IDs and source bindings only, never through public
projection text.

Visual Intent must contain the preserved director `render_mode`, primary focus,
visual encoding, information priority, presentation order, simplicity rules,
final-frame requirement, source bindings, plus the selected grammar ID and its
evidenced information relationship and direction. Director Visual Intent owns
information priority and presentation order. The grammar owns only its ID and
evidenced relationship classification; the Visual System cannot override either
source.

`design_slide` owns capacity assessment, background feasibility, and motion phases.
The semantic ECharts gate owns chart eligibility. This operation validates those
results against actual source-bound content, the locked system, and the controlled
runtime; it never invents them in the expression grammar.

Apply the Failure Decision Table before design. Without the correct locked Visual
System, do not choose or emit color, typography, material, geometry, render mode,
or motion. This operation never selects a prototype and never compiles or revises
the Visual System.

For a valid input, combine source truth, the selected grammar, and the locked
Visual System. Validate and implement the already selected and preserved
`render_mode`, which must be exactly one render enum:

- `html_svg`: HTML+CSS with optional inline SVG;
- `echarts`: controlled declarative ECharts JSON, only when grammar, data, and
  controlled-runtime gates pass.

Inline SVG is part of `html_svg`, never a third render mode.
Never reselect or switch `render_mode` in `design_slide`.

For a valid input, instantiate per-Slide geometry and timing from the locked
Visual System tokens and their ranges. Bind concrete palette, font, spacing,
shape, depth, chart, and motion choices by token reference. Do not alter a
whole-video token or create a new token at Slide scope.

## Authoring-Ready Slide Contract

Emit one structured contract containing:

- identity: video, shot, segment, Slide, and stable clip identifiers;
- canonical `design_strategy`, semantically unchanged `selection_provenance`, and
  unchanged `selection_provenance_sha256`;
- locked Visual System identity/version and immutable prototype reference;
- exact references to the locked concrete Visual System tokens used by the
  Slide and any per-Slide geometry or timing values instantiated within them;
- `source_bindings`: authoritative references for copy, values, units, relations,
  evidence, attribution, uncertainty, and upstream-supplied geometry or timing;
- `screen_content`: exact source-authorized visible copy, data values and units,
  labels, attribution and source cues, and optionality. Every entry points to one
  or more `source_bindings` entries and contains no geometry or timing;
- environment: `16:9`, confirmed duration, shot background, protected-region
  intent, accepted runtime execution facts, and the existing composition profile:
  `html_only` background `0.95-0.99` (default `0.99`), `avatar_html` full-canvas
  background `0.95-0.99` beneath the runtime-owned fixed lower-right Avatar, or
  `broll_html` background `0.20-0.55` (default `0.35`); no background reaches
  `1.00`;
- Communication Intent and the preserved director Visual Intent with the selected
  grammar ID and evidenced relationship classification;
- `render_mode`: exactly `html_svg` or `echarts`;
- semantic objects and relations;
- composition semantics: relative hierarchy, grouping, reading path, layer intent,
  and protected-region intent;
- for `avatar_html`, keep the primary claim, critical values, labels, and essential
  relationship geometry outside the runtime-owned `host_right` Avatar region. This
  is a design constraint supplied by the existing execution context, not a second
  geometry contract or a deterministic collision gate;
- motion intent: ordered semantic phases, one visual anchor, relative phase weight
  and priority, affected objects, property families limited to `transform` and
  `opacity`, optional meaningful inline-SVG stroke progression for `html_svg`, and
  stable complete-hold intent. Property values and timing remain unspecified;
- Visual Critic results, corrections, unresolved failures, and
  `final_frame_review_status: pending_render`.

Do not include `public_projection` or its text in the authoring-ready Slide
contract.

The contract is authoring-ready, not runtime-executable. Never emit guessed
percentages, pixel values, exact seconds, CSS selectors, fixed layout slots, or
concrete colors and fonts not supplied by the locked Visual System. If authoritative
upstream input explicitly supplies geometry or timing, preserve it as a source
binding; do not reinterpret or complete it by guessing.

Task 5 authoring materializes concrete geometry and exact deterministic timing
from the Slide's locked token references and allowed ranges within ratio, duration,
safe-area, background, grammar, and Visual System constraints. It never changes
the whole-video token set, then validates author output and any trusted
adapter/render evidence that exists.
Task 3 defines no fixed layout or timing resolver, and static validation does not
claim runtime support.

## Motion Intent

Use semantic phases such as establish, relate, focus, resolve, and hold only when
they improve comprehension. Keep one visual anchor stable. Specify order, relative
weight, priority, and affected semantic objects. Allow ordinary motion property
families `transform` and `opacity` only. For `html_svg`, also allow meaningful
inline-SVG stroke progression. Task 3 leaves all property values and timing
unspecified; Task 5 owns concrete authoring. No scrolling, interaction, hover
dependency, looping, random timing, perpetual motion, or meaning that exists only
mid-animation is allowed.

## Visual Critic

Review the authoring-ready contract for:

- fidelity to source meaning, values, units, order, attribution, uncertainty, and
  evidence direction;
- one unmistakable primary focus;
- director-preserved information priority and presentation order, plus the
  design-owned semantic phase order;
- simplicity and removal of objects without an information role;
- protected-region intent and planned background legibility;
- planned final-frame completeness without interaction or narration alone;
- consistency with the locked Visual System;
- implementation feasibility through the selected render enum.

Before render, the critic may pass these design-intent gates but must set
`final_frame_review_status: pending_render`. It cannot report rendered completeness,
fit, contrast, or legibility as passed. Post-render validation requires objective
PNG facts and the directly linked trusted renderer attestation. Source artifacts
remain `pending_render`; acceptance is represented by validator success, not by
rewriting model-authored status fields.

## Failure Decision Table

This table is the single authoritative mapping from condition to typed code and the
sole precedence definition. Evaluate it top-to-bottom; the first matching row wins.
Do not assign codes elsewhere, offer an unordered menu, silently change confirmed
state, or continue into a later row.

| Precedence | Operation or phase | Typed code | Exclusive condition | Required action |
| --- | --- | --- | --- | --- |
| 1 | Selection prerequisites | `blocked_incomplete_slide_set` | Confirmed Brief or complete confirmed Slide set is unavailable. | Return to planning; do not select a grammar or prototype or compile a system. |
| 2 | Selection prerequisites | `invalid_source_or_intent` | Brief and Slide set are complete, but confirmed source or narration, source-bound director Communication Intent or Visual Intent, or exact authorized data/evidence when the content or intent depends on them is missing, invalid, or contradictory. | Return to source/director; produce no visual selection or design. |
| 3 | Strategy validation | `invalid_design_strategy` | Rows 1-2 pass, but `design_strategy` is not exactly the sole production ID, version, and selection-source tuple. | Stop semantic selection; do not switch or repair the strategy implicitly. |
| 4 | Selection prerequisites | `unsupported_aspect_ratio` | Rows 1-3 pass, but ratio is not `16:9`. | Report a coverage gap; produce no selection, system, or design. |
| 5 | Visual-knowledge validation | `visual_knowledge_integrity_failed` | Strategy and ratio pass, but library schema, version, aspect-ratio declaration, or integrity-anchor verification fails. | Stop semantic selection; do not use or repair the library implicitly. |
| 6 | Slide-environment validation | `invalid_slide_environment` | Library integrity passes, but any Slide lacks a confirmed background or finite positive duration. | Return to director/planning before grammar or prototype selection. |
| 7 | Grammar selection | `coverage_gap_no_grammar` | Rows 1-6 pass, but no approved grammar preserves a Slide's Communication Intent and director Visual Intent; no grammar-resolved Visual Intent has been emitted for that Slide. | Report the coverage gap; emit no grammar-resolved Visual Intent and invent nothing. |
| 8 | Prototype selection | `coverage_gap_no_prototype` | Every Slide has a grammar and Visual Intent, but no approved prototype supports the complete video. | Report the coverage gap; invent nothing. |
| 9 | Internal Visual input binding | `blocked_stale_visual_selection` | Internal `visual_system_input_sha256` differs from the complete qualitative Brief and semantic Slide objects, or a requested Slide/environment differs from the locked artifact binding. | Rebuild the authoritative whole-video input and artifact; do not accept caller hash summaries. |
| 10 | Internal provenance validation | `selection_provenance_integrity_failed` | Compiler-generated provenance or its JCS hash is internally inconsistent. | Stop compilation; do not accept replacement caller provenance. |
| 11 | Public locked artifact binding | `blocked_locked_visual_system_mismatch` | The public reference does not match the separate artifact bytes, identity, strategy, or ratio. | Discard the substituted/stale artifact and rebuild it through the internal whole-video compiler. |
| 12 | `design_slide` | `blocked_missing_locked_visual_system` | Compile inputs passed, but the correct locked Visual System is missing, unlocked, stale, or belongs to another confirmed video. | Return to `compile_visual_system`; emit no Slide design choices. |
| 13 | `design_slide` capacity | `capacity_local_redesign_required` | Capacity is exceeded, but the same confirmed shot, content, order, narration, and duration can recompose within the grammar/system. | Revise local composition semantics only. |
| 14 | Selection or design change | `storyboard_reconfirmation_required` | Resolution changes Slide count, shot type, order, narration, or duration. | Return to Storyboard, display the complete revision, and require reconfirmation. |
| 15 | `design_slide` critic | `design_gate_revision_required` | A Visual Critic design gate fails under the same confirmed contract and locked system. | Revise the same Slide without changing strategy, prototype, system, or confirmed Storyboard. |
| 16 | Execution boundary | `unsupported_render_runtime` | Static authoring may have succeeded, but current adapter, persistence, or render execution facts are unsupported or conflict with the authoritative design contract. | Stop execution; preserve validated author artifacts and do not switch strategy, render mode, or use legacy authoring rules. |

## Anti-Patterns

- No single-Slide prototype or Visual System invention.
- No category-to-style or category-to-prototype mapping.
- No guessed left/right fractions, percentages, coordinates, pixels, timestamps,
  concrete colors, fonts, selectors, or implementation geometry.
- No template hunt, copied UI database, source reconstruction, dashboard chrome,
  web-page interaction, remote assets, arbitrary JavaScript, or GSAP.
- No hidden fallback, strategy substitution, legacy-rule override, or premature
  final-frame pass.
