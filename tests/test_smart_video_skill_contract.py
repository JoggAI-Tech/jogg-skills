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
            "runtime-boundary.md",
            "slide-design.md",
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
        for heading in ("## Checkpoint", "## Asset", "## MASTER Application", "## Safety", "## Submit And Inspect"):
            self.assertIn(heading, html_workflow)

        echarts = _read(REFERENCES / "echarts-authoring.md")
        for heading in ("## Design Source", "## Spec", "## Contract", "## Attach And Inspect"):
            self.assertIn(heading, echarts)

        slide_design = _read(REFERENCES / "slide-design.md")
        for heading in ("## Inputs", "## Design Method", "## Visual Quality", "## Slide Motion Intent", "## Handoff"):
            self.assertIn(heading, slide_design)

    def test_skill_entry_stays_bounded_and_orders_preflight_before_planning(self) -> None:
        text = _read(SKILL)
        lifecycle = text[text.index("## Lifecycle"):text.index("## Shot Types")]

        self.assertLessEqual(len(text.splitlines()), 400)
        self.assertLess(lifecycle.index("`preflight`"), lifecycle.index("Build the Brief"))
        self.assertIn("Wait for Brief confirmation", lifecycle)
        self.assertIn("Show the complete Storyboard and wait for confirmation", lifecycle)
        self.assertIn("## Reference Routing", text)

    def test_skill_preserves_lifecycle_and_recovery_invariants(self) -> None:
        text = _read(SKILL)
        lifecycle = text[text.index("## Lifecycle"):text.index("## Shot Types")]

        ordered_markers = [
            "`preflight`",
            "`workspace`",
            "Build the Brief",
            "complete Storyboard",
            "`--avatar-mode",
            "invoke `run`",
            "`waiting_html`",
            "`apply-html`",
            "`resume`",
            "`preview`",
            "`render`",
        ]
        positions = [lifecycle.index(marker) for marker in ordered_markers]
        self.assertEqual(positions, sorted(positions))

        recovery = "\n".join(
            (
                text,
                _read(REFERENCES / "jogg-task-lifecycle.md"),
                _read(REFERENCES / "runtime-boundary.md"),
                _read(REFERENCES / "html-authoring.md"),
            )
        )
        for required in (
            "`submission_unknown`",
            "`blocked_jogg_recovery`",
            "never resubmit",
            "`settings_url`",
            "`authoring_context`",
            "incomplete project",
        ):
            self.assertIn(required, recovery)

    def test_public_storyboard_requires_complete_fields_and_independent_confirmation(self) -> None:
        skill = _read(SKILL)
        orchestration = _read(REFERENCES / "content-orchestration.md")
        normalized_skill = " ".join(skill.split())
        normalized_orchestration = " ".join(orchestration.split())

        self.assertIn("user-facing type", normalized_skill.casefold())
        for required in ("stable ID", "title", "purpose", "narration", "planned duration", "Subtitles: No / Yes"):
            self.assertIn(required, normalized_orchestration)
        self.assertIn("Wait for Brief confirmation", normalized_skill)
        self.assertIn("Show the complete Storyboard and wait for confirmation", normalized_skill)
        for label in (
            "Avatar Only",
            "B-roll Only",
            "Avatar + B-roll",
            "Avatar + Slide",
            "B-roll + Slide",
            "Slide Only",
        ):
            self.assertIn(label, normalized_skill)
        for shot_type in ("avatar_only", "broll_only", "avatar_broll", "avatar_html", "broll_html", "html_only"):
            self.assertIn(f"`{shot_type}`", normalized_orchestration)
        self.assertIn("without another model call", normalized_orchestration)
        self.assertIn("After any shot edit, redisplay the complete Storyboard", normalized_orchestration)
        self.assertIn("Do not expose raw intents", normalized_orchestration)
        self.assertNotIn("Visual:", normalized_skill)

    def test_new_authoring_does_not_restore_legacy_reference_documents(self) -> None:
        skill_text = _read(SKILL)
        html_workflow = _read(REFERENCES / "html-authoring.md")

        self.assertIn("Import historical projects", skill_text)
        self.assertIn("new Slide", html_workflow)
        self.assertFalse(any(REFERENCES.glob("legacy-*.md")))

    def test_helper_commands_are_plugin_root_relative(self) -> None:
        markdown = "\n".join(_read(path) for path in [SKILL, *sorted(REFERENCES.glob("*.md"))])

        self.assertNotIn("python3 scripts/find_echarts_examples.py", markdown)
        self.assertNotRegex(markdown, r"find_v\d+_mg_templates\.py")
        self.assertIn('python3 "<plugin-root>/skills/smart-video/scripts/find_echarts_examples.py"', markdown)
        self.assertIn('python3 "<plugin-root>/skills/smart-video/scripts/build_slide_master.py"', markdown)
        self.assertEqual(
            {"find_echarts_examples.py", "find_mg_templates.py"},
            {path.name for path in (SKILL_ROOT / "scripts").glob("find_*.py")},
        )

    def test_active_visual_guidance_is_not_project_specific(self) -> None:
        text = "\n".join(
            (_read(REFERENCES / "visual-reference.md"), _read(REFERENCES / "slide-design.md"))
        )

        for stale in ("Hermes", "左侧叙事区", "第一批标准母版", "500 个模板"):
            self.assertNotIn(stale, text)
        self.assertIn("Visual System", text)

    def test_slide_validation_and_runtime_authoring_are_explicit(self) -> None:
        runtime = _read(REFERENCES / "runtime-boundary.md")
        validator = SKILL_ROOT / "scripts" / "slide_validation" / "cli.py"
        contracts = SKILL_ROOT / "scripts" / "slide_validation" / "contracts.py"

        self.assertTrue(validator.is_file())
        self.assertTrue(contracts.is_file())
        self.assertIn('"runtime-readiness"', _read(validator))
        self.assertIn("apply-html", runtime)
        self.assertIn("echarts_mg_spec", runtime)

    def test_content_orchestration_makes_the_accepted_storyboard_authoritative(self) -> None:
        text = _read(REFERENCES / "content-orchestration.md")

        for required in ("authoritative", "`shot_type`", "stable `clip_id`"):
            self.assertIn(required, text)
        self.assertIn("Do not insert media merely to satisfy a diversity ratio", text)

    def test_planning_handoff_uses_the_canonical_projector_and_public_contract(self) -> None:
        skill = _read(SKILL)
        orchestration = _read(REFERENCES / "content-orchestration.md")

        self.assertIn("content-orchestration.md", skill)
        self.assertIn("build_smart_video_planning_payload", orchestration)
        for field in ("scene_groups", "shot_type", "clip_id", "runtime_visual_style_profile"):
            self.assertIn(field, orchestration)
        self.assertIn("with `shot_type`, not", orchestration)
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
