---
name: direct-slide-art
description: Create concise whole-video and per-slide art direction from a confirmed Smart Video Brief, script, Communication Intent, and Visual Intent. Use inside the Smart Video workflow after Storyboard confirmation and before UI UX Pro Max adaptation or Slide authoring. Do not use for semantic planning, HTML implementation, B-roll, Avatar, audio, timeline assembly, or rendering.
---

# Direct Slide Art

Act as the visual designer between the confirmed Storyboard and Slide
implementation. Translate existing meaning into an original, concrete design
direction without classifying the meaning again.

Read [visual-language.md](references/visual-language.md) before directing a video.

## Required Input

Require the complete confirmed:

- Brief, including audience, goal, tone, language, and source boundary;
- narration script;
- ordered set of Slide-bearing shots;
- `communication_intent` for every Slide-bearing shot;
- `visual_intent` for every Slide-bearing shot.

Stop when any Slide lacks those intents or when their facts, relationships,
bindings, or timeline conflict. Do not repair upstream meaning in this Skill.

## Authority

Treat upstream intent as semantic authority:

- `required_facts` and `relationships` define what may be shown;
- `primary_focus` and `information_priority` define hierarchy;
- `presentation_order` and `semantic_timeline` define reveal order;
- `render_mode` defines HTML/SVG or ECharts and may not be changed;
- `shot_type` and runtime composition rules remain outside this Skill.

Decide only the visual language, composition treatment, hierarchy, graphic
metaphor, and design character. Do not introduce a new fact, relationship,
content object, step, category, comparison, or sequence.

## Direction Method

1. Read the complete video before directing any individual Slide.
2. Form one original whole-video art direction from the confirmed audience,
   purpose, tone, evidence character, and content density.
3. Use the visual knowledge as design vocabulary, not as a finite style list.
   Synthesize compatible palette, typography, material, geometry, density, and
   motion traits. Do not select or emit a named preset.
4. For each Slide, preserve the supplied semantic operation and actual content
   objects. Describe a composition that makes those supplied objects and
   relationships immediately legible.
5. Make each Slide direction concrete enough to implement: identify the dominant
   visual anchor, spatial organization, hierarchy, graphic treatment, and how the
   supplied presentation order becomes visible.
6. Keep each direction concise. Do not restate the script, schema, global safety
   rules, CSS implementation, or runtime behavior.
7. Review the complete set. Keep the shared art direction while avoiding a
   mechanically repeated layout.

Do not infer composition from object count alone. Three objects may be a
comparison, evidence set, hierarchy, cause set, or sequence; preserve the
relationship already declared upstream.

## Output Contract

Return exactly one JSON object with this shape and no surrounding explanation:

```json
{
  "schema_id": "smart-video.slide-art-direction.v1",
  "version": 1,
  "video_id": "same stable video ID supplied by Smart Video",
  "whole_video": "Two to four concise sentences defining the original visual language shared by the video.",
  "slides": [
    {
      "shot_id": "shot-04",
      "design_direction": "One to three concise sentences describing the concrete visual treatment for this supplied Slide intent."
    }
  ]
}
```

Include exactly one `slides[]` entry for every supplied Slide-bearing shot, in the
same order, with unchanged `shot_id` values. Keep `whole_video` and every
`design_direction` source-safe and implementation-independent.

## Prohibited Output

Do not output:

- a style-family or template choice;
- a second semantic classification;
- HTML, CSS, SVG, JavaScript, ECharts JSON, or implementation tokens;
- palette hex values, font downloads, component libraries, or remote assets;
- web-page patterns such as navigation, CTA sections, forms, or interaction;
- customer-facing rationale, alternatives, or questions;
- B-roll, Avatar, opacity, safe-area, audio, or compositing instructions.
