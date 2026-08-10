# Visual knowledge

The formal library contains 4 selectable visual prototypes and 18 expression grammar families.

## Evidence boundary

- Weak or missing evidence is omitted or recorded as a coverage gap. Fallback is forbidden.
- Measured intervals and clean-room qualitative profiles are descriptive design knowledge.
- Accessibility, local-only execution, final-hold stability, source fidelity, and non-overlap are normative obligations, not independent empirical evidence.
- Locked benchmark inputs are coverage probes only and never define the taxonomy.
- No source HTML, CSS, SVG, mood, industry, premium, or universal-winner label is carried into production.

## Unsupervised prototype qualification

The inventory contains 271 measured 16:9 samples, 54 numeric features, and 103 equal-weight evidence families.

Model selection chose k=4, silhouette=0.445309, median family-resampling ARI=0.969691, and p10 ARI=0.857777. The criterion uses stability and silhouette, not a minimum-cluster-fraction gate.

All 6 k=4 centroid pairs have positive distance. These unsupervised results and direct source review qualify four candidates; no full-data cluster label is treated as independent test truth.

## Automatic whole-video selection

The customer does not choose a prototype or author numeric targets. The system validates the complete confirmed Brief and source-bound Slide set, derives a measurable qualitative-semantic profile from object, relationship, priority, order, duration, background, and tone signals, then selects one evidence-qualified prototype by normalized distance. No candidate returns `coverage_gap_no_prototype`; an equal best score returns `ambiguous_visual_system_intent`. There is no topic, industry, population, benchmark, ID, or fallback tie-break.

## Visual System compilation and trust boundary

`compile_visual_system` is an internal whole-video builder operation. It consumes the complete confirmed Brief, complete semantic Slide set, system family decision, and current knowledge assets once, then emits one locked Visual System. The public per-Slide request cannot invoke or steer that operation: it carries only the locked system ID, version, and SHA-256 plus the current Slide source payload. The public CLI and reusable request API accept one immutable raw artifact byte snapshot, compute SHA-256 internally from those exact bytes, parse duplicate-safe JSON from the same bytes, validate the complete locked object, copy it into independent validated state, and check the current Slide against the artifact's source/environment binding. Parsed objects and caller-supplied artifact hashes are not accepted as separable authority.

The semantic-critic tuple and compiler provenance are traceability records, not cryptographic authentication and not proof that a model understood natural language. This Skill makes no local-attacker authenticity guarantee. Substituted or stale bytes fail in the supplied locked-artifact workflow; execution readiness additionally requires the direct loopback nonce challenge specified in [runtime-boundary.md](runtime-boundary.md).

The compiler generates concrete palette, contrast, typography, spacing, composition, material, ECharts, and motion tokens inside the selected measured profile. Every one of the 19 intent dimensions has a concrete token binding. The validator enforces actual contrast, local fonts/resources, measured ranges, source fidelity, non-overlap, final hold, and provenance. Generated choices are recorded as design decisions rather than presented as empirical facts; source tokens are not copied.

Whole-video semantic load adjusts density only. Effective load is clamped to 4..400; group gap decreases linearly from 32.00px to 20.00px, section and safe-area values are derived from that gap, and two-decimal outputs remain strictly monotonic and collision-free for every adjacent integer in the effective range. Complete-input hashes never perturb typography or spacing.

The four prototypes are macro structural anchors rather than four fixed finished styles. A separate clean-room synthesis asset contributes palette, typography, material, geometry, and motion family traits plus measured envelopes to token generation and validation. It records 24 reviewed Visual System catalog entries, an explicit census of all 18 directly reviewed style families, 30 measured reference layouts, and 216 measured scene candidates. 16 candidates are retained as executable trait bundles; 0 are excluded as measured redundancies; `crimson-night-glass`, `jewel-deco` remain coverage gaps because no matching audited local layout proves material, geometry, and motion. No redundancy equivalence is asserted without measured qualitative-dimension evidence. Whole-system catalog evidence supports only directly persisted palette and typography fields; material, geometry, and motion traits retain layout-level evidence and are never upgraded to whole-system facts. Every family/dimension census status is derived from explicit evidence refs and reconciled with the refs actually used by retained executable bundles; retained motion is `direct_layout_level`, never `direct_catalog_field`, because its executable evidence is `layout_template`. An upstream system semantic critic emits a controlled family identity bound to the exact confirmed `brief.visual_tone` hash. Production accepts exactly one retained identity and its evidence bundle, rejects stale, ambiguous, unsupported, and unresolved identities, and never falls through to literal substring matching or nearest composable substitution. Concrete tokens remain new complete-input-derived design decisions within the selected family evidence and macro prototype boundaries; no source color, font, markup, or composition is copied. No unexecuted observed-association claim is used as selection evidence.

## Prototype profiles

### unified-cluster-1

- high occupancy.
- large primary object.
- moderate panel load.
- approximately five-second build.
- Background adaptation is a normative Slide Design capability, not prototype evidence.
- Numeric intent dimensions: 19.

### unified-cluster-2

- dense structured composition.
- higher geometry load.
- higher connector load.
- deeper material.
- short reveal.
- Background adaptation is a normative Slide Design capability, not prototype evidence.
- Numeric intent dimensions: 19.

### unified-cluster-3

- low primary-object occupancy.
- high text share.
- strong display-to-body hierarchy.
- longer build.
- Background adaptation is a normative Slide Design capability, not prototype evidence.
- Numeric intent dimensions: 19.

### unified-cluster-4

- sparse composition.
- narrow palette.
- large body text.
- flat/minimal framing.
- Background adaptation is a normative Slide Design capability, not prototype evidence.
- Numeric intent dimensions: 19.

## Expression grammars

The full ZIP semantic corpus contributes 72 scenes and 216 candidate records across 18 generic topology families. Each signature preserves controlled operation, relationship kind, direction, role bindings to stable content-object IDs, visual encoding, source render metadata, exact contract/composition locators and hashes, and a counterexample. The three lenses are variants, not independent examples. Production grammar uniqueness is renderer-independent topology matching; the requested `html_svg` or `echarts` author mode is validated separately and locked into each Slide binding rather than presented as ZIP taxonomy evidence.

Metric relationships use `smart-video.source-bound-metric-relationship.v1`: every role binds a distinct structured source fact and an exact metric identity (canonical metric, display name, dimension, and unit). Existing `subtract` and `sum` equations remain closed arithmetic in one shared identity and unit. A source-stated approximate percentage uses the separate `divide_percent` equation with exactly two operand roles, one distinct result role, and a required strict comparison object `{ "mode": "rounded", "decimal_places": d }`. Every ratio fact must carry the source-bound field `"uncertainty": "approximate_from_source"`; free-text approximation is not evidence. The numerator and denominator must share all four identity fields, the denominator must be strictly positive, and the result must be a distinct source-bound structured metric with dimension `ratio` and unit `percent`. The result text's numeric token must have exactly `d` decimal places. Using decimal arithmetic, the validator accepts `numerator / denominator * 100` only in the deterministic interval `[result - 0.5 * 10^-d, result + 0.5 * 10^-d)`; it applies no other tolerance, conversion, inference, or complementary value. All bound roles must be exactly the equation's two operands and result. This is deterministic object/provenance validation, not a claim of deterministic natural-language understanding.

- `focus-assertion`: 5 scenes, 15 source signatures, operation `focus_assertion`.
- `definition-classification`: 2 scenes, 6 source signatures, operation `definition_classification`.
- `question-resolution`: 2 scenes, 6 source signatures, operation `question_resolution`.
- `correction-reversal`: 2 scenes, 6 source signatures, operation `correction_reversal`.
- `comparison-contrast`: 9 scenes, 27 source signatures, operation `comparison_contrast`.
- `transformation-change`: 2 scenes, 6 source signatures, operation `transformation_change`.
- `quantitative-rank-summary`: 2 scenes, 6 source signatures, operation `quantitative_rank_summary`.
- `distribution-association`: 3 scenes, 9 source signatures, operation `distribution_association`.
- `trend-forecast`: 2 scenes, 6 source signatures, operation `trend_forecast`.
- `part-whole-contribution`: 3 scenes, 9 source signatures, operation `part_whole_contribution`.
- `chronology-schedule`: 7 scenes, 21 source signatures, operation `chronology_schedule`.
- `linear-process-progression`: 5 scenes, 15 source signatures, operation `linear_process_progression`.
- `causal-mechanism`: 2 scenes, 6 source signatures, operation `causal_mechanism`.
- `cycle-feedback`: 3 scenes, 9 source signatures, operation `cycle_feedback`.
- `evidence-binding`: 8 scenes, 24 source signatures, operation `evidence_binding`.
- `spatial-geography-route`: 6 scenes, 18 source signatures, operation `spatial_geography_route`.
- `hierarchy-layers`: 3 scenes, 9 source signatures, operation `hierarchy_layers`.
- `entity-network-dependency`: 6 scenes, 18 source signatures, operation `entity_network_dependency`.

## Locked benchmark coverage

The 16 locked benchmark Slides are coverage probes classified only after the generic taxonomy existed. All 16/16 have one source-supported primary grammar; mixed tasks preserve secondary relationships. Their labels do not become taxonomy evidence.

Four usable benchmark design-system records are retained over two locked topics: two production Visual Systems compiled from the ordinary qualitative confirmed Brief and complete source-bound semantic Slide set, plus two independent `ui-ux-pro-max` MASTER outputs. The direct records are not production compiler output and carry no production prototype claim. Both lanes bind the same locked input hash.

## Catalog drift boundary

- `server-v4-main-template-api`: 9 canonical item hashes.
- `server-v4-reference-layout-api`: 30 canonical item hashes.
- `semantic-v8-family-16x9:refined-catalog`: 216 canonical item hashes.

A fetch failure or canonical item drift blocks validation.

## Version contract

`generation-manifest.json.expression_grammar_version` must equal `5.0.0`, the current grammar asset version and request selection version.
`visual-prototypes.json.version` is `4.0.0`.
`synthesis-traits.json.version` is `2.0.0`.
