from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "smart-video" / "skills" / "smart-video"
SKILL = SKILL_ROOT / "SKILL.md"
REFERENCES = SKILL_ROOT / "references"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SmartVideoSkillContractTest(unittest.TestCase):
    def test_removed_storyboard_balance_mechanisms_are_absent_from_plugin_source(self) -> None:
        forbidden = (
            "_validate_" + "lightweight_mg_adjacency",
            "_enforce_" + "avatar_only_storyboard_balance",
            "_enforce_" + "full_broll_storyboard_balance",
            "_enforce_" + "lightweight_mg_budget",
            "lightweight_mg_" + "budget_report",
            "storyboard_" + "balance_guard",
        )
        roots = (
            ROOT / "plugins" / "smart-video" / "runtime",
            ROOT / "plugins" / "smart-video" / "skills",
            ROOT / "plugins" / "smart-video" / "tests",
        )
        matches: list[str] = []
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".sh", ".md", ".json"}:
                    continue
                text = _read(path)
                for symbol in forbidden:
                    if symbol in text:
                        matches.append(f"{path.relative_to(ROOT)}: {symbol}")
        self.assertFalse(matches, "\n".join(matches))

    def test_reference_set_is_minimal_and_reachable(self) -> None:
        expected = {
            "broll-selection.md",
            "content-orchestration.md",
            "echarts-authoring.md",
            "echarts-options.md",
            "html-authoring.md",
            "jogg-api.md",
            "jogg-task-lifecycle.md",
            "legacy-echarts-authoring.md",
            "legacy-echarts-options.md",
            "legacy-html-authoring.md",
            "runtime-boundary.md",
            "slide-design.md",
            "visual-knowledge.md",
            "visual-reference.md",
        }
        actual = {path.name for path in REFERENCES.glob("*.md")}
        self.assertEqual(expected, actual)

        link_pattern = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)")
        pending = [SKILL]
        visited: set[Path] = set()
        while pending:
            source = pending.pop()
            if source in visited:
                continue
            visited.add(source)
            for target in link_pattern.findall(_read(source)):
                destination = (source.parent / target).resolve()
                if destination.is_file() and destination not in visited:
                    pending.append(destination)

        reachable = {path.name for path in visited if path.parent == REFERENCES}
        self.assertEqual(expected, reachable)

    def test_merged_references_own_complete_phase_contracts(self) -> None:
        html_workflow = _read(REFERENCES / "html-authoring.md")
        for heading in ("## Inputs And Authority", "## Artifact Stages", "## HTML Contract", "## Validation"):
            self.assertIn(heading, html_workflow)

        echarts = _read(REFERENCES / "echarts-authoring.md")
        self.assertIn("## LLM Author Output", echarts)
        self.assertIn("## Declarative Breadth", echarts)
        self.assertIn("## Trusted Adapter Output", echarts)

        slide_design = _read(REFERENCES / "slide-design.md")
        self.assertIn("## Operation: compile_visual_system", slide_design)
        self.assertIn("## Operation: design_slide", slide_design)
        self.assertIn("## Failure Decision Table", slide_design)

    def test_skill_entry_stays_bounded_and_orders_preflight_before_planning(self) -> None:
        text = _read(SKILL)
        lifecycle = text[text.index("## Core Lifecycle"):text.index("Use the host-appropriate launcher")]

        self.assertLessEqual(len(text.splitlines()), 400)
        self.assertLess(lifecycle.index("`preflight`"), lifecycle.index("Generate and show only the compact Brief"))
        self.assertIn("## Storyboard Confirmation", text)
        self.assertIn("## Reference Routing", text)
        self.assertIn("Read only the reference for the current phase", text)

    def test_skill_preserves_lifecycle_and_recovery_invariants(self) -> None:
        text = _read(SKILL)
        lifecycle = text[text.index("## Core Lifecycle"):text.index("Use the host-appropriate launcher")]

        ordered_markers = [
            "`preflight`",
            "`workspace`",
            "Generate and show only the compact Brief",
            "complete Storyboard",
            "`runtime-readiness`",
            "invoke `run`",
            "`waiting_html`",
            "`html-author`",
            "`resume`",
            "`waiting_avatar_confirmation`",
            "`preview`",
            "`render`",
        ]
        positions = [lifecycle.index(marker) for marker in ordered_markers]
        self.assertEqual(positions, sorted(positions))

        for required in (
            "`submission_unknown`",
            "`blocked_jogg_recovery`",
            "never resubmit",
            "Jogg OAuth or Local Media",
            "explicitly",
            "`settings_url`",
            "`authoring_context`",
            "every required clip is approved",
            "incomplete project",
        ):
            self.assertIn(required, text)

    def test_public_storyboard_requires_complete_fields_and_independent_confirmation(self) -> None:
        skill = _read(SKILL)
        orchestration = _read(REFERENCES / "content-orchestration.md")
        normalized_skill = " ".join(skill.split())
        normalized_orchestration = " ".join(orchestration.split())

        for required in (
            "user-facing type",
            "planned duration",
            "complete narration script",
            "Subtitles: No / Yes",
            "Brief confirmation and Storyboard confirmation are separate checkpoints",
        ):
            self.assertIn(required, normalized_skill)
        for label in (
            "Avatar Only",
            "B-roll Only",
            "Avatar + B-roll",
            "Avatar + Slide",
            "B-roll + Slide",
            "Slide Only",
        ):
            self.assertIn(label, normalized_skill)
            self.assertIn(label, normalized_orchestration)
        self.assertIn("without another model call", normalized_orchestration)
        self.assertIn("After any shot edit, show the complete updated Storyboard again", normalized_orchestration)
        self.assertIn("two projected descriptions are customer-facing views only", normalized_orchestration)
        self.assertNotIn("Visual:", normalized_skill)

    def test_new_authoring_does_not_load_legacy_director_references(self) -> None:
        skill_text = _read(SKILL)
        html_workflow = _read(REFERENCES / "html-authoring.md")
        legacy_html = _read(REFERENCES / "legacy-html-authoring.md")

        self.assertIn("imported legacy", skill_text.lower())
        self.assertIn("Never load", html_workflow)
        self.assertIn("legacy", html_workflow.lower())
        self.assertIn("apply-html", legacy_html)
        self.assertIn("Do not invoke legacy `apply-html`", skill_text)
        self.assertIn("Only an imported legacy clip", skill_text)

    def test_helper_commands_are_plugin_root_relative(self) -> None:
        markdown = "\n".join(_read(path) for path in [SKILL, *sorted(REFERENCES.glob("*.md"))])

        self.assertNotIn("python3 scripts/find_echarts_examples.py", markdown)
        self.assertNotRegex(markdown, r"find_v\d+_mg_templates\.py")
        self.assertIn('python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py"', markdown)
        self.assertIn('python3 "<skill-root>/scripts/validate_slide_generation.py"', markdown)
        self.assertEqual(
            {"find_echarts_examples.py", "find_mg_templates.py"},
            {path.name for path in (SKILL_ROOT / "scripts").glob("find_*.py")},
        )

    def test_active_visual_guidance_is_not_project_specific(self) -> None:
        text = _read(REFERENCES / "visual-reference.md")
        knowledge = _read(REFERENCES / "visual-knowledge.md")

        for stale in ("Hermes", "左侧叙事区", "第一批标准母版", "500 个模板"):
            self.assertNotIn(stale, text)
        self.assertIn("Visual System", text)
        self.assertIn("18 expression grammar families", knowledge)
        self.assertIn("Automatic whole-video selection", knowledge)

    def test_slide_validation_and_runtime_authoring_are_explicit(self) -> None:
        skill = _read(SKILL)
        runtime = _read(REFERENCES / "runtime-boundary.md")
        validator = SKILL_ROOT / "scripts" / "validate_slide_generation.py"
        grammar = SKILL_ROOT / "assets" / "visual-knowledge" / "expression-grammar.json"

        self.assertTrue(validator.is_file())
        self.assertTrue(grammar.is_file())
        self.assertIn("`runtime-readiness`", skill)
        self.assertIn("`html-author` or `echarts-author`", skill)
        self.assertIn("runtime-readiness routes", runtime)
        self.assertIn("html-author", runtime)
        self.assertIn("echarts-author", runtime)

        import json

        grammar_payload = json.loads(_read(grammar))
        self.assertEqual(18, len(grammar_payload["items"]))

    def test_content_orchestration_makes_the_accepted_storyboard_authoritative(self) -> None:
        text = _read(REFERENCES / "content-orchestration.md")

        for required in ("authoritative", "`shot_type`", "`scene_role`", "independent `clip_id`"):
            self.assertIn(required, text)
        self.assertIn("must not insert presenter-only or B-roll-only shots", text)

    def test_planning_handoff_uses_the_canonical_projector_and_public_contract(self) -> None:
        skill = _read(SKILL)
        orchestration = _read(REFERENCES / "content-orchestration.md")

        self.assertIn("build_smart_video_planning_payload", skill)
        self.assertIn("build_smart_video_planning_payload", orchestration)
        for field in (
            "producer_analysis",
            "production_requirement_document",
            "script_director",
            "creative_plan",
            "director_document",
            "scene_groups",
        ):
            self.assertIn(field, orchestration)
        self.assertIn("`script` is one aggregate narration string", orchestration)
        self.assertIn("every `scene_groups[].shots[]` item", orchestration)
        self.assertIn("Use `shot_type`, never `type`", orchestration)
        self.assertIn("`blocked_planning`", orchestration)

    def test_markdown_relative_links_exist(self) -> None:
        markdown_files = [SKILL, *sorted(REFERENCES.glob("*.md"))]
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

        missing: list[str] = []
        for source in markdown_files:
            for target in link_pattern.findall(_read(source)):
                if target.startswith(("http://", "https://", "#")):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (source.parent / relative).resolve().exists():
                    missing.append(f"{source.relative_to(ROOT)} -> {target}")

        self.assertFalse(missing, "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
