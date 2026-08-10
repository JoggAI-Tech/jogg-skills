# New Slide HTML Authoring

Use this workflow only for a new Slide with an authoring-ready contract from
[slide-design.md](slide-design.md) and preserved `render_mode: html_svg`. Imported
clips use [legacy-html-authoring.md](legacy-html-authoring.md) instead. Never load
or apply legacy template, `authoring_context`, patch, fallback, free-generation,
or `apply-html` rules to a new Slide.

## Inputs And Authority

Require one request conforming to
`assets/contracts/slide-generation-request.v1.schema.json`. Author only from its
`source_content`, `source_data`, source bindings, and locked Visual System. Preserve
every authorized value, label, unit, null, uncertainty, attribution, order, and
relationship exactly. Do not complete missing information or copy sample content.

Preserve the request's `design_strategy`, `render_mode`, shot type, identity,
provenance, and source hashes. Never infer, repair, switch, or omit them. Reject
`public_projection` at any depth.

Choose concrete layout and timing only within `16:9`, the safe area, duration,
background, selected grammar, and locked Visual System. Use one primary visual
anchor, restrained information reveal, and a complete stable final hold. Keep
B-roll recognizable in `broll_html` while the Slide remains primary. Do not create
dashboard chrome, an app screen, or a marketing page unless the source meaning
requires that exact form. Do not show implementation, feature, control, or shortcut
instructions.

## Artifact Stages

1. **LLM author:** write one local UTF-8 HTML artifact containing HTML, CSS, and
   optional inline SVG only. Do not write JavaScript.
2. **Trusted local adapter:** normalize or pass through the safe HTML without
   adding scripts. Record the adapter artifact only after that trusted step exists.
3. **Post-render:** validate report shape and objective facts from a real local PNG,
   then require the approved runtime identity and a runtime attestation linking the
   author, adapter, screenshot, final timeline time, and observed root.

The author artifact and `generation-manifest.json` retain
`final_frame_review_status: pending_render`. A model must not claim a rendered pass.

## HTML Contract

Emit one complete document with exactly one `html`, `head`, and `body`. For
`html_svg`, the only `head` element child is one direct nonvisual `style`. The
generated root is a direct child of `body`, and its only direct element children
are the distinct backdrop and content, in that order:

```html
<html>
<head><style>/* finite root-scoped CSS */</style></head>
<body><main
  id="slide-root"
  data-smart-video-slide="true"
  data-design-strategy="smart_video_slide_design"
  data-design-version="1.0.0"
  data-render-mode="html_svg"
  data-manifest-id="manifest-001"
  data-video-id="video-001"
  data-shot-id="shot-001"
  data-segment-id="segment-001"
  data-slide-id="slide-001"
  data-clip-id="clip-001"
>
  <div class="slide-backdrop"></div>
  <div class="slide-content">...</div>
</main>
</body>
</html>
```

No visual/content element or non-whitespace text may occur outside `#slide-root`.
The trusted ECharts adapter may additionally place only its three exact bundled
scripts as direct `body` children outside the root and may use zero or one direct
nonvisual `head > style`. No third root child is allowed. Every element carrying
`data-content-id`, `data-source-annotation-id`, `data-source-pointer`, or
`data-source-value-json` must be a descendant of the one direct `.slide-content`
child.

Copy all attribute values from the request and manifest. The benchmark uses its
canonical benchmark ID/version, never production values. Do not serialize
`selection_source` into a visual attribute; the validator obtains it from the
canonical request tuple.

Do not use script tags, handlers, canvas, iframes, frames, objects, embeds, images,
media, forms, controls, navigation/resource-loading elements, imports, or external
assets. `meta`, `base`, `link`, `area`, and `portal` are forbidden. Parse every
attribute: style attributes, event attributes, `contenteditable`, `draggable`,
`tabindex`, `autofocus`, `accesskey`, and resource-bearing attributes such as
`src`, `srcset`, `poster`, `background`, `formaction`, `action`, `ping`, `cite`, and
`manifest` are forbidden. `href` and SVG `xlink:href` may contain only a local
fragment reference. Reject relative paths as well as remote, protocol-relative,
data, blob, JavaScript, and file URLs. Every `url()` is forbidden in CSS and every
HTML or SVG attribute value. The only allowed CSS at-rule is finite `@keyframes`;
every selector must be exactly `#slide-root` or a descendant/child selector rooted
there, with no pseudo-selector or generated `content`. Do not use random values,
infinite animation, hidden final content, or root opacity. Apply any transparency
only to `.slide-backdrop`; keep `.slide-content` fully legible. Inline SVG must
remain static markup and may not reference an external resource.

Use the existing execution-layer composition profiles without moving or resizing
Avatar or B-roll:

| Shot type | Backdrop composition profile |
| --- | --- |
| `html_only` | Use `0.95-0.99`; default to `0.99`. |
| `avatar_html` | Use `0.95-0.99` on the full-canvas backdrop. The runtime composites its fixed lower-right Avatar above the Slide; keep primary information outside that runtime-owned region without moving, resizing, or independently validating the Avatar geometry. |
| `broll_html` | Use `0.20-0.55`; default to `0.35`, with B-roll recognizable and Slide information primary. |

Declare the applicable canonical number or percentage on `.slide-backdrop`.
Background opacity must never reach `1`, `1.0`, or `100%`; those values fail the
composition gate. This upper bound applies to background compositing only. Text,
source-bearing HTML, inline SVG, and chart content remain fully opaque.

Every element marked with source content and every ancestor through
`.slide-content` and `#slide-root` must remain rendered and visible. `hidden`,
`aria-hidden="true"`, `display="none"`, `visibility="hidden"` or `collapse`, and
non-opaque source surfaces fail, including SVG presentation attributes. When
specified on a source-bearing element or one of its ancestors, `opacity` must be
a canonical fully opaque number (`1`, an equivalent decimal such as `1.0`, or
`100%`); computed, variable, exponent, and partially opaque values fail closed.
`display` and `visibility` must use an explicitly admitted visible keyword.
`filter`, `clip-path`, `mask`, `mask-image`, and `transform` must be absent or
`none`. In particular, static transforms on source surfaces are not accepted
because static validation cannot prove their final in-bounds geometry. Inline
`style` remains forbidden. These restrictions apply only to source-bearing
surfaces and their ancestors; a decorative element that contains no source fact
or source binding may be hidden.

CSS values use a closed local function policy. Color gradients, color functions,
finite transforms, `calc()`, `min()`/`max()`/`clamp()`, and `var()` are admitted;
unknown functions fail closed. Resource-producing functions including `url()`,
`image-set()`, `-webkit-image-set()`, `image()`, `cross-fade()`, `paint()`, and
`element()` are forbidden. Relative filename strings are also forbidden in CSS.

Before URL, import, resource, interaction, attribute-value, and selector checks,
decode CSS escapes deterministically: 1-6 hexadecimal digits with one optional
following CSS whitespace character, or one escaped non-newline character. Escapes
cannot conceal `url()`, a scheme/path, an at-rule, an interactive selector, or an
out-of-root selector. After escape decoding, remove CSS comments from the
normalized safety view of both stylesheet text and every HTML/SVG attribute value;
comments cannot split `url()` or another forbidden token. This normalization is
only for validation and does not alter the authored artifact.

Before contract-specific recursion, every JSON input is checked with an iterative
budget: maximum nesting depth 128, 100,000 values, 1,000,000 characters per string
or object key, and 10,000 items per array. Render screenshots are limited before
read/decompression allocation to 16 MiB compressed bytes, 8192 pixels on either
axis, 20,000,000 pixels, and 64 MiB decoded scanline bytes.

Every CSS animation must have a finite single iteration, a retained final state,
and a final keyframe. It must finish no later than the start of the manifest's
positive `stable_hold` phase. A source-surface animation may use admitted opacity
or transform values before the final keyframe only when that final keyframe
explicitly proves canonical `opacity: 1` and `transform: none`; unsupported
visibility properties remain forbidden throughout the animation. Meaning and
complete evidence must remain visible in the final frame without hover, click,
scrolling, narration, or animation replay.

Every `source_content.screen_content` item has a stable `content_id` and nonempty
`source_binding_ids`. Render each item exactly once, in request order, with exact
normalized text on an element marked `data-content-id="<content_id>"`. No extra
visible text is allowed. If `source_data` is nonempty, `html_data_bindings` must
cover every scalar leaf by RFC 6901 pointer exactly once. A content target also
carries its exact `data-source-pointer`; a nonvisual source-authorized annotation
carries `data-source-annotation-id`, `data-source-pointer`, and an exact JSON value
in `data-source-value-json`. Missing, duplicate, reordered, invented, or drifted
content or data fails validation, including nulls, units, attribution, list order,
nodes, links, and coordinates.

## Manifest And Hashes

Write `generation-manifest.json` against
`assets/contracts/generation-manifest.v1.schema.json`. Include complete identity,
canonical strategy, locked Visual System identity/version, `16:9`, shot type,
preserved render mode, provenance/source hashes, duration, contiguous motion
phases, positive stable hold, pending render status, and stage-specific artifact
paths and SHA-256 hashes.

Every motion phase contains both `animation_name` and `echarts_action`. For
`html_svg`, an active phase has a nonempty CSS `animation_name` and
`echarts_action: null`; the final `stable_hold` has both fields set to `null`.
Do not place an ECharts action in an HTML phase. The animation name must resolve
to the authored finite CSS animation with the same phase timing.

`selection_provenance_sha256` preserves the upstream RFC 8785 JCS definition. The
stdlib validator admits only null, booleans, strings without surrogates, arrays,
and objects with string keys. Numeric JSON values are outside this Task 5 boundary;
upstream counts and versions must be canonical strings. The validator rejects all
integers and floats rather than risking lexical-number ambiguity. It sorts object
names by UTF-16 code units and emits RFC 8785-compatible JSON string escapes with
Unicode preserved. This is an exact RFC 8785 subset and does not rename or redefine
`selection_provenance_sha256`.

Task 5 source and artifact hashes use the separate
`smart-video-canonical-json-v1` profile: parsed JSON values, UTF-8, Unicode
preserved, object keys sorted, no insignificant whitespace, and non-finite numbers
rejected through Python stdlib `json.dumps` with `ensure_ascii=False`,
`allow_nan=False`, `sort_keys=True`, and `separators=(",", ":")`. This scoped
profile never defines or replaces selection provenance JCS.

## Validation

Run author validation before adaptation:

```bash
python3 "<skill-root>/scripts/validate_slide_generation.py" \
  --phase pre-adapter \
  --request "/absolute/path/request.json" \
  --manifest "/absolute/path/generation-manifest.json" \
  --author "/absolute/path/slide.html"
```

At `pre-adapter`, the manifest adapter record is absent or null. Run `pre-render`
only after a real `trusted_local_adapter` HTML record and exact file hash exist in
the manifest, and
run `post-render` only with a report conforming to
`assets/contracts/render-report.v1.schema.json`. Validation verifies its identity,
shape, screenshot path/hash/byte count/dimensions, PNG chunks and decoding, and at
least one visible nontransparent pixel. Caller-authored check values are not proof
of overflow, overlap, clipping, contrast/legibility, final-frame completeness, or
strategy/root agreement. The `runtime_errors` and `resource_loads` checks must
also pass. Their capture-owned evidence lives only inside
`runtime_attestation.observed_root.browser_failures`; do not duplicate it at the
report root. Every failure count must be zero, details must be empty, and the
capture context must be `adapter_page`. The runtime attestation must exactly match the approved
identity in `assets/runtime/trusted-runtime-identity.v1.json`, both artifact hashes,
the screenshot hash, manifest duration, strategy root, render mode, and observed
settled state. The report, request, manifest, and author output all remain
`pending_render`; a `VALID` result authorizes the evidence bundle but does not let a
model or caller rewrite those source statuses.

Static validation authorizes the artifact, not runtime support. Submit HTML through
the dedicated `html-author` endpoint, not legacy `apply-html`. Apply
`unsupported_render_runtime` when adapter persistence, approved runtime identity,
real rendering, or attestation cannot be proved. Do not route to legacy execution
or another render mode.
