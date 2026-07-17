# Smart Slides Visual Style Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Smart Slides project a reproducible, executable visual identity and reject HTML/MG assets that drift into arbitrary neon colors, fonts, glow, or thin HUD styling.

**Architecture:** Add a local style-profile catalog between the existing Podcastor MG director contract and bespoke HTML validator. A project selects one profile, `material_id` applies a bounded finish override, every clip receives the resolved tokens, and the validator checks authored HTML/CSS before the existing sanitizer and canvas/composition checks run.

**Tech Stack:** Python 3 standard library, extracted Podcastor planner and bespoke HTML services, Bash lifecycle runner, unittest, local Chrome, FFmpeg.

---

## File Map

- Create `plugins/smart-slides/runtime/backend/services/video_studio_visual_styles.py`: profile catalog, deterministic selection, legacy palette normalization, CSS variables, contrast and authored-style validation.
- Create `plugins/smart-slides/tests/test_visual_style_profiles.py`: selection, propagation, CSS-token and glow-policy tests.
- Modify `plugins/smart-slides/runtime/backend/services/video_studio_planner.py`: persist profile data and expose it in clip/render contracts.
- Modify `plugins/smart-slides/runtime/backend/services/video_studio_bespoke_html.py`: inject profile CSS and merge style QA into existing bespoke validation.
- Modify `plugins/smart-slides/scripts/smart-slides.sh`: resolve the project profile while validating pre-project per-clip HTML.
- Modify Smart Slides skill references: document profile selection, token usage, material overrides, and research-derived constraints.
- Modify `plugins/smart-slides/extraction-manifest.json`: record the new local-only module and adapted destinations.

### Task 1: Profile Catalog And Selection

**Files:** Create `plugins/smart-slides/runtime/backend/services/video_studio_visual_styles.py`; test `plugins/smart-slides/tests/test_visual_style_profiles.py`.

- [ ] **Step 1: Write failing selection tests**

```python
def test_news_topic_selects_editorial_profile(self):
    profile = visual_styles.resolve_visual_style_profile(topic="AI 科技热点新闻")
    self.assertEqual(profile["id"], "editorial_tech_news")

def test_explicit_profile_wins(self):
    profile = visual_styles.resolve_visual_style_profile(topic="科技新闻", requested="technical_blueprint")
    self.assertEqual(profile["id"], "technical_blueprint")
```

- [ ] **Step 2: Run tests and confirm the missing-module failure**

Run: `PYTHONPATH=plugins/smart-slides/runtime plugins/smart-slides/.venv/bin/python -m unittest plugins.smart-slides.tests.test_visual_style_profiles -v`

Expected: FAIL because `video_studio_visual_styles` does not exist.

- [ ] **Step 3: Implement three profiles and deterministic normalization**

Implement `editorial_tech_news`, `technical_blueprint`, and `archival_documentary`, each with semantic palette roles, accent budget, local font stacks, line weights, glow policy, motion personality, material overrides, and WCAG contrast metadata. Map a legacy five-color list in the fixed order `surface, ink, primary, highlight, danger` only when it passes contrast.

- [ ] **Step 4: Run the focused tests**

Run: `PYTHONPATH=plugins/smart-slides/runtime plugins/smart-slides/.venv/bin/python -m unittest plugins.smart-slides.tests.test_visual_style_profiles -v`

Expected: PASS.

### Task 2: Planner And Clip Contract Propagation

**Files:** Modify `plugins/smart-slides/runtime/backend/services/video_studio_planner.py`; test `plugins/smart-slides/tests/test_visual_style_profiles.py` and `plugins/smart-slides/tests/test_mg_director_contract.py`.

- [ ] **Step 1: Add failing propagation tests**

```python
def test_requirement_and_overlay_share_profile(self):
    requirement = planner.normalize_requirement_document({"html_mg_direction": {"visual_style_profile_id": "technical_blueprint"}}, "芯片架构", "broll_html")
    self.assertEqual(requirement["html_mg_direction"]["visual_style_profile"]["id"], "technical_blueprint")
    contract = planner._html_overlay_contract_for_clip("芯片架构", clip, [shot])
    self.assertEqual(contract["visual_style_profile"]["id"], "technical_blueprint")
```

- [ ] **Step 2: Run tests and confirm missing profile fields**

Run: `PYTHONPATH=plugins/smart-slides/runtime plugins/smart-slides/.venv/bin/python -m unittest plugins.smart-slides.tests.test_visual_style_profiles -v`

Expected: FAIL on missing `visual_style_profile`.

- [ ] **Step 3: Persist and propagate the profile**

Normalize it in `html_mg_direction` and `html_mg_style`, preserve it in `mg_director`, add it to `html_overlay_contract_v1`, `design_plan`, and `render_manifest`, and expose CSS variable names plus the selected `material_id` override.

- [ ] **Step 4: Run planner tests**

Run: `PYTHONPATH=plugins/smart-slides/runtime plugins/smart-slides/.venv/bin/python -m unittest plugins.smart-slides.tests.test_visual_style_profiles plugins.smart-slides.tests.test_mg_director_contract -v`

Expected: PASS.

### Task 3: Authored HTML Style QA

**Files:** Modify `plugins/smart-slides/runtime/backend/services/video_studio_bespoke_html.py`; modify `plugins/smart-slides/scripts/smart-slides.sh`; test `plugins/smart-slides/tests/test_visual_style_profiles.py` and `plugins/smart-slides/tests/test-smart-slides.sh`.

- [ ] **Step 1: Add failing validator tests**

```python
def test_rejects_undeclared_literal_color(self):
    report = visual_styles.validate_authored_style('<main class="ai-mg-layer"></main>', '.hero{color:#22d3ee}', self.profile, material_id="editorial_color_field")
    self.assertFalse(report["ok"])

def test_endpoint_glow_is_bounded(self):
    report = visual_styles.validate_authored_style('<main class="ai-mg-layer"></main>', '.mg-endpoint{filter:drop-shadow(0 0 8px var(--mg-primary))}', self.profile, material_id="luminous_data")
    self.assertTrue(report["ok"])
```

- [ ] **Step 2: Run tests and confirm validation does not exist**

Run: `PYTHONPATH=plugins/smart-slides/runtime plugins/smart-slides/.venv/bin/python -m unittest plugins.smart-slides.tests.test_visual_style_profiles -v`

Expected: FAIL on missing validator.

- [ ] **Step 3: Implement style QA and CSS injection**

Reject undeclared color literals, non-token font families, too many semantic color roles, root-sized accent fills, and glow outside the material/profile policy. Inject immutable `--mg-*` variables after the extracted Podcastor fallback CSS, merge the style report into `ai_html_generation.validation`, and pass the plan-level profile into the pre-project `apply-html` checkpoint path.

- [ ] **Step 4: Update shell fixtures to use semantic variables**

Replace literal test colors with `var(--mg-ink)`, `var(--mg-primary)`, and profile font variables. Assert failed style QA leaves the clip in `qa_failed` and does not start Jogg.

- [ ] **Step 5: Run focused Python and Bash tests**

Run: `PYTHONPATH=plugins/smart-slides/runtime plugins/smart-slides/.venv/bin/python -m unittest plugins.smart-slides.tests.test_visual_style_profiles plugins.smart-slides.tests.test_mg_director_contract -v`

Run: `bash plugins/smart-slides/tests/test-smart-slides.sh`

Expected: PASS.

### Task 4: Skill Contract And Release

**Files:** Create `plugins/smart-slides/skills/smart-slides/references/visual-style-profiles.md`; modify `SKILL.md`, `planning-contracts.md`, `html-mg-contract.md`, `mg-director-visual-contract.md`, `podcastor-template-style.md`, and `extraction-manifest.json`.

- [ ] **Step 1: Document project-level profile selection**

Require one profile per project, canonical five-color ordering for an explicit palette, semantic CSS variables for every clip, restrained color use, contrast thresholds, and motion hierarchy. Cite the Urban Institute, Datawrapper, CMU, peer-reviewed palette, and motion-design-system sources already captured in `.firecrawl/`.

- [ ] **Step 2: Reconcile the Podcastor finish reference**

Mark its navy translucent values as legacy fallback only. Profile tokens control current output; `material_id` changes texture and emphasis within that profile rather than inventing another palette.

- [ ] **Step 3: Update extraction metadata**

Add `video_studio_visual_styles.py` to `local_only`, update adapted destination hashes, and describe style-profile propagation without changing the recorded source commit or source hashes.

- [ ] **Step 4: Run all verification**

Run: `bash plugins/smart-slides/tests/run-tests.sh`

Run: `python3 /Users/cds-dn-137/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/smart-slides/skills/smart-slides`

Run: `python3 /Users/cds-dn-137/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/smart-slides`

Expected: all checks pass.

- [ ] **Step 5: Refresh the local plugin installation**

Run: `python3 /Users/cds-dn-137/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py plugins/smart-slides`

Run: `codex plugin add smart-slides@jogg-skills`

Expected: the marketplace-backed plugin reinstalls from the current local source.
