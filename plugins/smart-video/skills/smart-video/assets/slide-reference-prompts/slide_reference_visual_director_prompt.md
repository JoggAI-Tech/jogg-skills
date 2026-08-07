Slide HTML reference contract for this request:

- `<reference_html mode="edit_base" authority="content">` is the complete sanitized editable source. It is exempt from the generic reference-Slide no-copy rule: treat its existing content, DOM, CSS, animations, and edit IDs as authoritative and plan only the Brief's allowed changes.
- `<reference_html mode="style_reference" content_allowed="false">` is complete visual evidence, but its visible words, numbers, names, and facts are not authorized content. Use it only for the visual usages selected in the Brief.
- For `create + strict` (`operation=create` with a `style_reference` whose `fidelity=strict`), treat the reference as a locked visual implementation, not as inspiration. Do not select a new Style Family, do not recompose the layout, and do not replace its design language. This overrides the generic Style Family fallback.
- Extract the locked composition, visual hierarchy, design tokens, palette, typography system, spacing, component geometry, shape language, inline SVG treatment, motifs, and motion into the Visual Plan with enough precision for the Renderer to preserve a recognizable implementation.
- Keep the reference's region relationships, relative scale, alignment, whitespace, focal hierarchy, recurring components, decorative system, and animation character. Adapt only what authorized new content requires for legibility and fit; do not introduce an unrelated visual direction.
- Content permission always comes from the Generation Brief. A strict visual reference never authorizes its visible copy or business facts, and the Visual Plan must remain content-safe.
- A `visual_reference` Manifest projection is optional supplemental guidance. The HTML boundary remains available when the Manifest is absent or ignored.
