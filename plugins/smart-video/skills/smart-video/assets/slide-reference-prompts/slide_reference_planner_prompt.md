Slide HTML reference contract for this request:

- `html_available=true` and `editable_html=true` mean the backend already loaded that Slide's complete editable HTML and will supply a sanitized copy downstream. The body is deliberately hidden from the Planner.
- `current_html_exists` refers only to the request's explicit `html_source`, not to Slide attachments.
- Determine fidelity from the user's requested preservation boundary. Do not use keyword matching or require a particular phrase.
- Use `fidelity=strict` when the referenced Slide's visual implementation is a constraint: the new result must remain recognizably derived from its composition, hierarchy, design tokens, component geometry, and motion language even when the topic or visible content changes.
- A new topic or new content with that strict visual preservation boundary means `operation=create`, usage `style`, `layout`, `motion`, and `component`, `fidelity=strict`, `content_allowed=false`, and `allowed_changes=[]`. It must not become strict_edit merely because its visual fidelity is strict.
- Use `fidelity=normal` when the reference guides the design but recomposition, adaptation, or omission is allowed. When the preservation boundary is ambiguous, default to `fidelity=normal`.
- Use `fidelity=loose` only when the reference supplies a general direction, mood, or inspiration and substantial visual differences are allowed.
- Classify edits by the existing target/action boundary. When the primary action mutates existing content or object in the referenced editable Slide, including but not limited to remove, replace, hide, move, or another targeted mutation, use `operation=strict_edit`, `content_policy=preserve_current`, `usage=base`, and `fidelity=strict`. This is not create + strict.
- For that strict edit, `allowed_changes` must be non-empty and contain only the requested targets and requested properties. Property mapping: replace or clear existing visible text -> text_content; remove existing object or region -> structure; hide without removal -> style; move or resize -> layout.
- Use a user-supplied `data-ai-edit-block` ID when present; otherwise carry an unambiguous semantic target from the request. Because the Planner cannot inspect the HTML body, do not invent an exact edit-block ID.
- A Slide selected as `base` is authoritative during the edit. Preserve its visible content, semantic structure, DOM, CSS, animations, and edit IDs except for the explicitly allowed target/property pairs.
