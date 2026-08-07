Slide HTML reference contract for this request:

- `<reference_html mode="edit_base" authority="content">` is the complete sanitized editable source and is authoritative for strict edits.
- `<reference_html mode="style_reference" content_allowed="false">` supplies complete visual evidence only. Its visible copy and business facts must not enter the output unless another authorized source independently supplies them.
- For `create + strict` (`operation=create` with a `style_reference` whose `fidelity=strict`), use the complete reference HTML as the visual implementation baseline. Transform it minimally instead of redesigning from scratch; the Visual Plan is an extraction of that baseline and must not override it with a new style.
- Preserve the recognizable DOM and composition, CSS tokens, palette, typography hierarchy, spacing system, layout proportions, component geometry, borders, radii, shadows, shape language, inline SVG treatment, motifs, and motion implementation. Do not recompose, substitute an unrelated component system, or simplify away distinctive visual features.
- Replace or remove reference-visible content according to the Generation Brief and use only authorized content. You must not copy names, words, numbers, facts, metrics, dates, labels, conclusions, or other business content from the reference unless an authorized source independently supplies the same content.
- New content may cause only necessary text-fit adjustments such as line wrapping, bounded type-size adaptation within the reference hierarchy, or local container fitting. Do not use content length as permission to redesign the composition.
- `visual_reference` Manifest data is optional supplemental guidance and never overrides the associated HTML boundary or Brief.
