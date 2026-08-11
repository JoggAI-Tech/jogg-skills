"""Repository-level installation contract tests for the Smart Video plugin."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

from smartvideo_test_runtime import INSTALL_ROOT, RUNTIME_PACKAGE_ROOT


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "smart-video"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SmartVideoCrossPlatformContractTests(unittest.TestCase):
    def test_plugin_uses_official_jogg_metadata_and_brand_assets(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "smart-video")
        self.assertEqual(manifest["interface"]["displayName"], "Smart Video")
        self.assertEqual(
            manifest["author"],
            {
                "name": "JoggAI",
                "email": "support@jogg.ai",
                "url": "https://app.jogg.ai/",
            },
        )
        self.assertEqual(manifest["homepage"], "https://app.jogg.ai/")
        self.assertEqual(manifest["repository"], "https://github.com/JoggAI-Tech/jogg-skills")
        self.assertEqual(manifest["license"], "UNLICENSED")
        self.assertEqual(manifest["interface"]["developerName"], "JoggAI")
        self.assertEqual(manifest["interface"]["websiteURL"], "https://app.jogg.ai/")
        self.assertEqual(manifest["interface"]["brandColor"], "#2E5CFF")
        icon_path = "./assets/branding/jogg-icon.png"
        for field in ("composerIcon", "logo", "logoDark"):
            relative = manifest["interface"][field]
            self.assertEqual(relative, icon_path)
            self.assertTrue((PLUGIN_ROOT / relative).is_file(), relative)
        default_prompts = manifest["interface"]["defaultPrompt"]
        self.assertTrue(default_prompts)
        self.assertTrue(
            all(
                isinstance(prompt, str) and prompt.strip() and prompt.isascii()
                for prompt in default_prompts
            )
        )

    def test_plugin_contains_only_agent_assets_and_thin_launchers(self) -> None:
        for removed in (
            "runtime",
            "local-speech",
            "local-avatar-0603",
            "framevideo-editor",
            "assets/video_studio_bgm",
            "assets/fonts",
            "assets/avatar-packs",
            "tests",
            "npm",
            "extraction-manifest.json",
        ):
            self.assertFalse((PLUGIN_ROOT / removed).exists(), removed)

        expected_scripts = {
            "install-node-official.sh",
            "smart-video.sh",
            "smart-video.cmd",
            "smart-video.ps1",
            "video-studio.sh",
        }
        self.assertEqual(expected_scripts, {path.name for path in (PLUGIN_ROOT / "scripts").iterdir()})
        size = sum(path.stat().st_size for path in PLUGIN_ROOT.rglob("*") if path.is_file())
        self.assertLess(size, 800 * 1024 * 1024)

    def test_runtime_bom_pins_the_complete_package_set(self) -> None:
        plugin = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        bom = json.loads((PLUGIN_ROOT / "runtime-bom.json").read_text(encoding="utf-8"))
        release = json.loads((PLUGIN_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"].split("+", 1)[0], "0.8.11")
        self.assertEqual(bom["plugin_version"], "0.8.11")
        self.assertEqual(release["version"], "0.8.11")
        expected = {
            "@joggai/smartvideo-avatar",
            "@joggai/smartvideo-editor",
            "@joggai/smartvideo-registry",
            "@joggai/smartvideo-renderer",
            "@joggai/smartvideo-runtime",
            "@joggai/smartvideo-speech",
        }
        self.assertEqual(bom["aggregate"], {"name": "@joggai/smartvideo", "version": "0.1.4"})
        self.assertEqual(set(bom["packages"]), expected)
        self.assertEqual(
            bom["packages"],
            {
                "@joggai/smartvideo-avatar": "0.1.0",
                "@joggai/smartvideo-editor": "0.1.1",
                "@joggai/smartvideo-registry": "0.1.0",
                "@joggai/smartvideo-renderer": "0.1.2",
                "@joggai/smartvideo-runtime": "0.1.2",
                "@joggai/smartvideo-speech": "0.1.0",
            },
        )
        self.assertEqual(bom["avatar_execution"], "jogg_remote_task_driver")
        self.assertEqual(
            bom["packaged_assets"],
            {
                "owner": "@joggai/smartvideo-runtime@0.1.2",
                "font": "assets/fonts/albert-sans/AlbertSans.ttf",
                "bgm_manifest": "assets/video_studio_bgm/manifest.json",
                "bgm_track_count": 10,
            },
        )
        self.assertEqual(release["install_contract"], "npm_managed")
        self.assertEqual(
            bom["distribution"],
            {
                "mode": "npm_registry",
                "registry": "https://registry.npmjs.org/",
                "package": "@joggai/smartvideo@0.1.4",
                "upstream_cli": "@joggai/smartvideo-cli@0.0.7",
            },
        )
        self.assertEqual(
            bom["managed_tools"]["macos_ffmpeg"],
            {
                "version": "9.0",
                "source_page": "https://ffmpeg.org/download.html",
                "build_provider": "https://evermeet.cx/ffmpeg",
                "architecture": "x86_64",
                "ffmpeg_sha256": "b1bd0cbaa0c889a08589dc1d14e4a08eebf425b8726c31a7e270e08552d0f271",
                "ffprobe_sha256": "66a5102de63ce1c6a203d05a463ac836100eba9403d16968674366de17452da6",
            },
        )
        self.assertEqual(
            release["plugin_runtime_files"],
            [
                "scripts/smart-video.sh",
                "scripts/install-node-official.sh",
                "scripts/smart-video.cmd",
                "scripts/smart-video.ps1",
                "scripts/video-studio.sh",
            ],
        )
        self.assertEqual(release["runtime_bom"]["sha256"], _sha256(PLUGIN_ROOT / "runtime-bom.json"))
        optional = release["optional_avatar_resources"]
        self.assertEqual(optional["mode"], "managed_on_demand")
        self.assertEqual(optional["managed_root"], "~/.codex/smartvideo/resources/avatar-packs")
        self.assertEqual(optional["download_page_url"], "https://docs.jogg.ai/avatar-resources")
        self.assertEqual(
            [item["resource_id"] for item in optional["resources"]],
            ["classroom-presenter", "office-presenter"],
        )
        self.assertEqual(
            bom["optional_resources"]["avatar_packs"]["resource_ids"],
            ["classroom-presenter", "office-presenter"],
        )
        self.assertEqual(
            bom["optional_resources"]["avatar_packs"]["install_commands"],
            {
                "classroom-presenter": "npx --yes @joggai/smartvideo@latest resources install classroom-presenter",
                "office-presenter": "npx --yes @joggai/smartvideo@latest resources install office-presenter",
            },
        )

        self.assertEqual(
            release["npm_runtime"],
            {
                "registry": "https://registry.npmjs.org/",
                "package": "@joggai/smartvideo",
                "version": "0.1.4",
            },
        )
        self.assertFalse((PLUGIN_ROOT / "npm").exists())

    def test_release_hashes_reference_plugin_and_npm_owned_assets(self) -> None:
        manifest = json.loads((PLUGIN_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        runtime_root = RUNTIME_PACKAGE_ROOT
        for relative, record in manifest["runtime_assets"].items():
            path = runtime_root / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(record["sha256"], _sha256(path))

        self.assertFalse((PLUGIN_ROOT / "assets" / "fonts").exists())
        self.assertEqual(
            len(list((runtime_root / "assets" / "video_studio_bgm" / "tracks").glob("*.mp3"))),
            10,
        )

        semantic = PLUGIN_ROOT / "skills" / "smart-video" / "assets" / "semantic-mg-references"
        records = manifest["reference_assets"]["semantic_mg_reference_catalog"]
        for key, filename in (
            ("scene_mapping_sha256", "scene-template-map.json"),
            ("template_index_sha256", "index.json"),
            ("semantic_adaptation_sha256", "semantic-unit-adaptation.json"),
        ):
            self.assertEqual(records[key], _sha256(semantic / filename))

    def test_shell_is_an_atomic_npm_forwarder(self) -> None:
        runner = (PLUGIN_ROOT / "scripts" / "smart-video.sh").read_text(encoding="utf-8")
        self.assertLess(len(runner.splitlines()), 270)
        for required in (
            "@joggai/smartvideo",
            "SMARTVIDEO_PACKAGE_SPEC",
            "load_runtime_contract",
            "install-node-official.sh",
            'bom.aggregate?.name !== process.env.SMARTVIDEO_EXPECTED_NAME',
            "npm install",
            'runtime_root_ready "$staging"',
            "active-runtime.json",
            "SMARTVIDEO_PLUGIN_ROOT",
            'SMARTVIDEO_OAUTH_CLIENT_ID="smart-video"',
            "exec \"$binary\"",
        ):
            self.assertIn(required, runner)
        self.assertIn('if runtime_ready; then', runner)
        self.assertNotIn("SMARTVIDEO_BUNDLED_PACKAGE", runner)
        self.assertNotIn("brew install", runner)
        self.assertNotIn("brew upgrade", runner)
        for migrated in ("ensure_plugin_assets()", "apply_html_asset()", "wait_for_plugin_task()"):
            self.assertNotIn(migrated, runner)
        self.assertNotIn('SMARTVIDEO_ASSETS_ROOT="$PLUGIN_ROOT/assets"', runner)

        install_doc = (PLUGIN_ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("https://ffmpeg.org/download.html", install_doc)
        self.assertIn("FFmpeg is also managed without Homebrew", install_doc)

        node_installer = (PLUGIN_ROOT / "scripts" / "install-node-official.sh").read_text(
            encoding="utf-8"
        )
        for required in (
            "https://nodejs.org/dist",
            "SHASUMS256.txt",
            "EXPECTED_SHA",
            "ACTUAL_SHA",
            'NODE_HOME/current',
        ):
            self.assertIn(required, node_installer)
        self.assertNotIn("brew", node_installer.lower())

        helper = (
            PLUGIN_ROOT / "skills" / "smart-video" / "scripts" / "find_echarts_examples.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"paths",', helper)
        self.assertIn('"--json",', helper)
        self.assertIn('json.loads(completed.stdout)["SMARTVIDEO_RUNTIME_ROOT"]', helper)
        self.assertNotIn("active-runtime.json", helper)
        self.assertNotIn('install_root / "' + "node_modules" + '"', helper)

        readiness = (
            PLUGIN_ROOT
            / "skills"
            / "smart-video"
            / "scripts"
            / "slide_validation"
            / "runtime_readiness.py"
        ).read_text(encoding="utf-8")
        self.assertIn('bom["packages"]["@joggai/smartvideo-runtime"]', readiness)
        self.assertNotIn("EXPECTED_RUNTIME_VERSION", readiness)

        skill = (PLUGIN_ROOT / "skills" / "smart-video" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("invoke `upgrade` once", skill)
        self.assertIn("independently versioned child packages", skill)

    def test_windows_entrypoint_retains_host_bootstrap(self) -> None:
        cmd = (PLUGIN_ROOT / "scripts" / "smart-video.cmd").read_text(encoding="utf-8")
        powershell = (PLUGIN_ROOT / "scripts" / "smart-video.ps1").read_text(encoding="utf-8")
        self.assertIn("-ExecutionPolicy Bypass", cmd)
        self.assertIn("smart-video.ps1", cmd)
        self.assertIn('if ($action -in @("bootstrap", "install-deps", "upgrade"))', powershell)
        self.assertIn("smart-video.cmd", powershell)
        self.assertIn("smart-video.sh", powershell)
        for required in (
            "Ensure-WindowsHostTools",
            "Get-WindowsHostReport",
            "Convert-ToGitBashPath",
            "Git.Git",
            "Python.Python.3.12",
            "OpenJS.NodeJS.LTS",
            "Gyan.FFmpeg",
            "jqlang.jq",
            "Google.Chrome",
        ):
            self.assertIn(required, powershell)

    def test_uninstalled_doctor_is_read_only_machine_json(self) -> None:
        if platform.system() != "Darwin":
            self.skipTest("macOS shell launcher is exercised on the release host")
        with tempfile.TemporaryDirectory(prefix="smartvideo-doctor-") as home:
            completed = subprocess.run(
                ["bash", str(PLUGIN_ROOT / "scripts" / "smart-video.sh"), "doctor"],
                env={**os.environ, "HOME": home},
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "dependencies_missing")
        self.assertEqual(report["required"], "@joggai/smartvideo@0.1.4")
        self.assertIn("bootstrap", report["bootstrap_command"])
        self.assertIn("smart-video.sh", report["bootstrap_command"])

    def test_release_has_no_developer_machine_paths_or_generated_data(self) -> None:
        forbidden = (b"cds-dn-137", b"/Documents/golang/", b"/Documents/jogg-skills/")
        offenders: list[str] = []
        for path in PLUGIN_ROOT.rglob("*"):
            if not path.is_file():
                continue
            content = path.read_bytes()
            if any(value in content for value in forbidden):
                offenders.append(str(path.relative_to(PLUGIN_ROOT)))
        self.assertEqual(offenders, [])
        self.assertFalse(any(PLUGIN_ROOT.rglob("*.onnx")))
        tracked = subprocess.run(
            ["git", "ls-files", "plugins/smart-video/**/*.pyc"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(tracked.stdout.strip(), "")

    def test_managed_npm_package_set_matches_bom(self) -> None:
        bom = json.loads((PLUGIN_ROOT / "runtime-bom.json").read_text(encoding="utf-8"))
        expected = {bom["aggregate"]["name"]: bom["aggregate"]["version"], **bom["packages"]}
        for name, version in expected.items():
            package_dir = INSTALL_ROOT / "node_modules" / "@joggai" / name.removeprefix("@joggai/")
            metadata = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["name"], name)
            self.assertEqual(metadata["version"], version)

    def test_runtime_and_tests_do_not_read_a_developer_package_checkout(self) -> None:
        checkout_name = "-".join(("jogg", "npm"))
        forbidden = (
            "JOGG_" + "NPM_ROOT",
            "/".join(("", "golang", checkout_name)),
            '"packages"' + ' / "smartvideo',
        )
        offenders: list[str] = []
        candidates = list((REPOSITORY_ROOT / "tests").glob("*.py"))
        candidates.extend((PLUGIN_ROOT / "scripts").glob("*"))
        candidates.extend((PLUGIN_ROOT / "skills" / "smart-video" / "scripts").glob("*"))
        for path in candidates:
            if not path.is_file() or path == Path(__file__):
                continue
            content = path.read_text(encoding="utf-8")
            if any(token in content for token in forbidden):
                offenders.append(str(path.relative_to(REPOSITORY_ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
