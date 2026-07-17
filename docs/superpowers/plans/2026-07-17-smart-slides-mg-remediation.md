# Smart Slides HTML/MG Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore animated, clip-continuous, editable HTML/MG in the local plugin without Hermes, HyperFrames, cloud rendering, or new model APIs.

**Architecture:** Retain extracted Podcastor project and MG contracts. Render each MG clip locally through Chrome CDP to an alpha WebM, slice it by `bound_shots` in FFmpeg, make `edit_schema.editable_blocks` authoritative, and add per-clip creation and QA checkpoints.

**Tech Stack:** FastAPI, local Chrome/Chromium CDP pipe, FFmpeg VP9 alpha, React/TypeScript/Vite, Bash, unittest.

---

## Scope

Implement in this dependency order: P0 animated render and clip continuity; P1 semantic editing; P1 staged Codex HTML/QA; P2 reference cleanup. Do not modify `/Users/cds-dn-137/Documents/golang/operation-Podcastor` or add HyperFrames, Hermes, cloud storage, remote renderers, or external LLM requests.

### Task 1: Local Animated Alpha Renderer

**Files:** Create `plugins/smart-slides/runtime/render/chrome_cdp.py`; create `plugins/smart-slides/runtime/render/animated_overlay.py`; modify `plugins/smart-slides/runtime/render/ffmpeg_adapter.py`; test `plugins/smart-slides/tests/test_runtime.py`.

- [ ] Write `test_alpha_renderer_freezes_animation_time` with a fake CDP session. Render one second at 2 fps and assert frame times are `0`, `500`, `1000`, then assert the FFmpeg command contains `libvpx-vp9` and `yuva420p`.
- [ ] Run `PYTHONPATH=runtime ~/.codex/smart-slides/venv/bin/python -m unittest tests.test_runtime.LocalFfmpegAdapterTest.test_alpha_renderer_freezes_animation_time`; expect an import failure before implementation.
- [ ] Implement `ChromeCdpSession` with `call`, `navigate`, `evaluate`, `screenshot_png`, and `close`. Start only the configured local Chrome with `--headless=new`, `--remote-debugging-pipe`, transparent default background, and a work-local profile. Use length-prefixed JSON on stdin/stdout and reject any navigation not beginning with `file:`.
- [ ] Implement `render_alpha_webm(page_path, duration, output, frame_rate=24)`. At each frame execute `animation.pause(); animation.currentTime = FRAME_TIME_MS` for `document.getAnimations({subtree:true})` and each same-origin `srcdoc` iframe, then send the PNG bytes to one FFmpeg image pipe. The encoder command is `ffmpeg -f image2pipe -framerate 24 -i - -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -metadata:s:v:0 alpha_mode=1 -an clip.webm`.
- [ ] Replace static `_render_overlay_png()` in the normal path with alpha output. `SMART_SLIDES_HTML_RENDER_MODE=poster` remains an explicit diagnostic fallback; the default animated path must not add `animation:none!important`.
- [ ] Run `PYTHONPATH=runtime ~/.codex/smart-slides/venv/bin/python -m unittest tests.test_runtime.LocalFfmpegAdapterTest`; expect the alpha test and existing audio/video probe test to pass.

### Task 2: Preserve Multi-Shot MG Clips

**Files:** Modify `plugins/smart-slides/runtime/backend/services/video_studio_works.py`; modify `plugins/smart-slides/runtime/backend/services/video_studio_planner.py`; modify `plugins/smart-slides/runtime/render/ffmpeg_adapter.py`; test `plugins/smart-slides/tests/test_runtime.py`.

- [ ] Write `test_work_snapshot_preserves_multi_shot_mg_clip` for two sequential shots and one clip with `bound_shots: ["shot-1", "shot-2"]`. Require one snapshot clip and offsets `{shot-1: 0, shot-2: shot_1_duration}`.
- [ ] Run the test; expect failure because `_derived_mg_layer()` currently creates `bound_shots: [shot_id]`.
- [ ] Change `_derived_mg_layer()` to read declared clips from `mg_layer`, `design_plan.mg_clips`, and `render_manifest.mg_clips` before one-shot fallbacks. Deduplicate by clip ID and preserve start, end, duration, HTML/CSS, design document, schema, and all bound IDs.
- [ ] Render every clip once. Store `{clip_id, webm_path, start, end, shot_offsets}` and compose each shot with `-ss <shot_offset>` on that same alpha WebM. Reject a bound shot outside the clip interval.
- [ ] Add a moving-element fixture proving one WebM render, a non-zero second-shot offset, no animation restart, and final duration equal to narration duration.

### Task 3: Semantic, Non-Destructive Editing

**Files:** Create `plugins/smart-slides/runtime/frontend/src/features/video-studio/editSchema.ts`; create `plugins/smart-slides/runtime/frontend/src/features/video-studio/editSchema.test.ts`; modify `plugins/smart-slides/runtime/frontend/src/EditorApp.tsx`; modify `plugins/smart-slides/runtime/backend/services/video_studio_bespoke_html.py`; modify `plugins/smart-slides/runtime/backend/api/video_studio.py`; modify `plugins/smart-slides/skills/smart-slides/references/html-mg-contract.md`.

- [ ] Define `EditableBlock` as `{id,name,kind,selector,allowed,colorMode?}` where `kind` is text, visual, or group and `allowed` can include text, x, y, width, height, fontSize, scale, color, opacity, and motion.
- [ ] Test rejection of duplicate IDs, descendant selectors, zero/multiple selector matches, and a child block exposed below an editable group.
- [ ] Add `normalize_edit_schema(custom_html, edit_schema)` in the backend. It marks exactly the declared semantic selector and fails on missing or ambiguous selectors; it must not auto-label raw SVG paths when a schema exists.
- [ ] Add `html_block_overrides_by_clip` and `PATCH /projects/{project_id}/mg-clips/{clip_id}/edit-schema`. Persist only `{block_id:{changed_property:value}}`, validate properties against `allowed`, and require `colorMode: descendants` for group color propagation.
- [ ] Make `HtmlPanel` use the selected clip schema. Bind text size to CSS `font-size`, visual size to `scale`, and width/height to real element dimensions. Keep `ensureHtmlEditableBlocks` only for a visible legacy migration warning. Test that an X-only edit adds no color, opacity, motion, width, or height declaration.

### Task 4: Per-Clip Codex Creation and Visual QA

**Files:** Modify `plugins/smart-slides/scripts/smart-slides.sh`; modify `plugins/smart-slides/runtime/backend/api/video_studio.py`; modify `plugins/smart-slides/runtime/backend/services/video_studio_store.py`; modify `plugins/smart-slides/skills/smart-slides/SKILL.md`; create `plugins/smart-slides/skills/smart-slides/references/per-clip-html-workflow.md`; modify `plugins/smart-slides/tests/test-smart-slides.sh` and `plugins/smart-slides/tests/mock_server.py`.

- [ ] Persist run-state `html_clip_checkpoints` as `{status:"pending|generated|qa_failed|approved",asset_path:"",keyframes:[],attempt:0,error:""}`. It contains IDs and local paths only.
- [ ] A director-only planning file must return `waiting_html` with `pending_clip_ids`; Jogg and final render must not begin until every required clip is approved.
- [ ] Add actions `html-status`, `apply-html --clip-id --html-file`, `capture-html --clip-id --at-seconds`, and `approve-html --clip-id`. Apply normalizes one asset; capture uses Task 1; approve requires validation and at least one keyframe.
- [ ] Change Skill workflow: initial planning supplies scripts, shots, MG director contracts, and clip bindings, not all HTML/CSS. Codex authors one clip, captures entry/build/hold, inspects/repairs it, approves it, then proceeds. Resume skips approved clips and never recreates Jogg work.
- [ ] Extend mock tests to prove failed QA blocks render, resuming only touches pending clips, and request logs contain no standalone TTS, Hermes, Podcastor remote API, COS, external LLM, or remote renderer calls.

### Task 5: Reconcile References and Release

**Files:** Modify `planning-contracts.md`, `MG-VISUAL-STANDARD-v1.md`, `mg-director-visual-contract.md`, `html-mg-contract.md`, `SKILL.md`, and `extraction-manifest.json` under `plugins/smart-slides`.

- [ ] Document precedence: per-clip MG director composition > bespoke HTML/edit schema > local renderer > visual-system examples. Treat fixed PPT ratios as examples, never mandates. Require `visual_fx` to be visible in a captured QA keyframe.
- [ ] Make missing schema, missing primary visual, unsafe text, empty alpha output, unchanged entry/build/hold frames, and unapproved clips render-blocking errors. Keep subjective suggestions as warnings.
- [ ] Document `MAX_CREATIVE_PLAN_SCENES = 12` as an upstream cap; split scene groups rather than claim contradictory 12-20 retained scenes.
- [ ] Preserve source hashes in `extraction-manifest.json`; update only destination hashes and adaptation descriptions for local alpha rendering, semantic editing, and staged checkpoints.
- [ ] Run `python3 tests/test_source_parity.py`, plugin validation, `npm run build`, cachebuster, and `codex plugin add smart-slides@jogg-skills`. All must pass before delivery.

## Findings Confirmed Before Execution

- Static PNG screenshots are the direct reason CSS/SVG animation does not reach the MP4.
- The current work snapshot converts declared clips to one-shot assets.
- The editor derives blocks from DOM markers and can expose SVG children.
- `visual_fx` is already passed by the current bespoke HTML prompt, so acceptance must validate visible execution rather than duplicate prompt fields.
- The four remediation tracks are independently deployable; P0 must land first because prompt or editor work cannot restore lost motion.
