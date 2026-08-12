# Whole-Video Design MASTER

Generate one design MASTER after the Storyboard is confirmed and before any Slide
is authored. The MASTER gives every Slide a shared visual language while leaving
each shot free to express its own semantic relationship.

## Input

Write one private JSON input with this exact top-level shape. The shown Brief
fields are required; preserve any additional confirmed fields unchanged:

```json
{
  "schema_id": "smart-video.slide-master-input.v2",
  "version": 2,
  "video_id": "stable-video-id",
  "project_name": "Readable project name",
  "brief": {
    "goal": "Confirmed outcome",
    "audience": "Confirmed audience",
    "starting_knowledge": "What the audience already knows",
    "language": "Confirmed language",
    "aspect_ratio": "16:9",
    "evidence_boundary": "Confirmed source boundary",
    "explicit_unknowns": ["An unsupported conclusion that must not be implied"],
    "design_domain": "language learning education",
    "visual_tone": "Confirmed audience-facing tone",
    "target_duration_seconds": 60,
    "broll_availability": "Confirmed availability and source boundary"
  },
  "script": "Complete confirmed narration",
  "art_direction": {
    "schema_id": "smart-video.slide-art-direction.v1",
    "version": 1,
    "video_id": "stable-video-id",
    "whole_video": "Exact whole-video direction returned by $direct-slide-art",
    "slides": [
      {
        "shot_id": "shot-04",
        "design_direction": "Exact per-Slide direction returned by $direct-slide-art"
      }
    ]
  },
  "slides": []
}
```

Copy `<workspace_dir>/plans/slide-art-direction.json` into `art_direction`
unchanged. Its `video_id` must match the MASTER input. Its ordered `slides[]`
must contain exactly one entry for every Slide-bearing shot and must match the
MASTER input's Slide order and `shot_id` values.

Each `slides[]` item contains at least the following fields. Preserve additional
source objects, evidence, structured data, and bindings unchanged:

```json
{
  "shot_id": "shot-04",
  "shot_type": "avatar_html",
  "duration_seconds": 10,
  "communication_intent": {
    "viewer_before": "The viewer cannot distinguish the two concepts",
    "viewer_after": "The viewer can distinguish the two concepts",
    "communication_operation": "explain",
    "required_facts": ["Exact source-authorized fact"],
    "relationships": ["Concept A differs from concept B in the sourced way"],
    "expected_viewer_response": "Apply the distinction to the next example",
    "bindings": {
      "narration": "Exact narration for this shot",
      "shot_id": "shot-04",
      "segment_ids": ["shot-04-segment-01"],
      "time_range_seconds": {"start": 30, "end": 40}
    }
  },
  "visual_intent": {
    "render_mode": "html_svg",
    "primary_focus": "One dominant relationship",
    "information_priority": ["first", "second", "third"],
    "presentation_order": ["establish", "relate", "conclude"],
    "semantic_timeline": {
      "basis": "narration_relative",
      "cues": [
        {
          "cue_id": "shot-04-cue-01",
          "narration_anchor": "Concept A",
          "visual_target": "first concept",
          "phase": "establish",
          "start_ratio": 0.18
        },
        {
          "cue_id": "shot-04-cue-02",
          "narration_anchor": "Concept B",
          "visual_target": "second concept and contrast",
          "phase": "relate",
          "start_ratio": 0.56
        }
      ],
      "stable_hold_start_ratio": 0.82
    },
    "relationship": "comparison",
    "simplicity": "Remove any element that does not explain the comparison",
    "final_frame": "The complete comparison and conclusion remain visible",
    "bindings": {
      "shot_id": "shot-04",
      "segment_ids": ["shot-04-segment-01"],
      "time_range_seconds": {"start": 30, "end": 40}
    }
  }
}
```

Every `narration_anchor` must be exact continuous text from the bound narration.
Cues and `start_ratio` values follow that text's spoken order. The
`stable_hold_start_ratio` begins only after the last cue and reserves the final
readable frame. These fields are semantic timing authority, not visual styling.

Use the complete Brief, complete script, exact art direction, and every complete
Slide intent. The builder binds all of them into the immutable input hash and
preserves unknown source-bound Slide fields. Product classification uses only the
explicit private `design_domain`; it never asks the search engine to guess a
product category from the narration. Style refinement consumes the art director's
whole-video and per-Slide directions together with the confirmed visual tone and
Slide relationships. Do not build one MASTER per shot.

## Generation

Run:

```bash
python3 "<plugin-root>/skills/smart-video/scripts/build_slide_master.py" \
  --input "<workspace_dir>/plans/slide-master-input.json" \
  --output-dir "<workspace_dir>/design"
```

The builder verifies the bundled private UI UX Pro Max inventory and data before
generation. It performs no network request and does not load the public UI UX Pro
Max Skill. It applies the UI UX Pro Max product reasoning, style, color,
typography, and chart domains, then writes exactly one
`<workspace_dir>/design/MASTER.md`. Its website `landing` result has no Slide
design authority and is never emitted into the MASTER.

The builder may stop for malformed input, a missing or changed private dependency,
an empty or zero-match core search, an unmapped runtime style, incomplete UI UX Pro
Max output, absent chart guidance, or an inaccessible output path. It invalidates
an existing output before regeneration, so a failed rebuild cannot leave an old
MASTER available. It writes a temporary sibling and atomically replaces the final
path only after the complete file is written; a failed write removes the partial
temporary file. Report the exact issue. Do not reuse another video's MASTER and
do not continue with a template, previous Visual System, or default palette.

## Authority

The MASTER owns whole-video:

- palette and runtime semantic color mapping;
- typographic roles and hierarchy;
- spacing rhythm and density;
- shape and material character;
- line and depth character;
- motion personality;
- chart styling guidance;
- fixed safe area and composition profiles.

Communication Intent and Visual Intent own each shot's information, relationship,
priority, reading order, simplification, and final meaning. Art Direction owns the
original visual treatment without changing that meaning. The Slide designer
combines all three authorities. It does not select a template or copy a source
layout.

The MASTER contains only the fixed-canvas adaptation. Website structure, CTA,
forms, navigation, breakpoints, remote fonts, hover, focus, and interaction output
must not appear and cannot influence a Slide.

## Runtime Palette Bridge

The metadata header contains an exact `runtime_visual_style_profile` derived from
the UI UX Pro Max palette, an explicit complete mapping of bundled style names to
the three current npm material profiles, and the current npm color contract. An
unknown style name stops generation; there is no default profile. Write this object to
the whole-video production plan as `visual_style_profile` without modification.

The profile converts MASTER colors to:

```text
--mg-surface
--mg-surface-recessed
--mg-ink
--mg-muted
--mg-primary
--mg-highlight
--mg-danger
--mg-outline
```

Slides use only these variables for colors. The current npm runtime supplies local
font variables. UI UX Pro Max font names remain hierarchy guidance only when the
font is not locally available; never download a font or author `@import`.

## Locking

Keep the generated bytes unchanged for the current video. Every Slide reads the
same file. A single-shot visual edit does not rebuild it. Rebuild only when the
confirmed Brief, complete script, Slide set, or art direction changes.
