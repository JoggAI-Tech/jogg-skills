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


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "smart-video"
NPM_ROOT = Path(
    os.environ.get("JOGG_NPM_ROOT", REPOSITORY_ROOT.parent / "golang" / "jogg-npm")
).expanduser().resolve()


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
            "tests",
            "npm",
            "extraction-manifest.json",
        ):
            self.assertFalse((PLUGIN_ROOT / removed).exists(), removed)

        expected_scripts = {
            "smart-video.sh",
            "smart-video.cmd",
            "smart-video.ps1",
            "video-studio.sh",
        }
        self.assertEqual(expected_scripts, {path.name for path in (PLUGIN_ROOT / "scripts").iterdir()})
        size = sum(path.stat().st_size for path in PLUGIN_ROOT.rglob("*") if path.is_file())
        self.assertLess(size, 800 * 1024 * 1024)

        catalog_path = PLUGIN_ROOT / "assets" / "avatar-packs" / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema"], "smartvideo_avatar_catalog_v1")
        self.assertEqual(catalog["default_avatar_id"], "ce6b414b061c44744f95854cc030ac38")
        self.assertEqual(
            {item["avatar_id"] for item in catalog["items"]},
            {"ce6b414b061c44744f95854cc030ac38"},
        )
        for item in catalog["items"]:
            payload_root = catalog_path.parent / item["payload_root"]
            integrity = json.loads((payload_root / "integrity.json").read_text(encoding="utf-8"))
            self.assertEqual(integrity["schema"], "smartvideo_encrypted_assets_v1")
            self.assertEqual(integrity["bundle_id"], item["bundle_id"])
            self.assertEqual(integrity["asset_kind"], "templates")
            self.assertEqual(len(integrity["files"]), item["file_count"])
            self.assertEqual(len(list((payload_root / "payload").rglob("*.enc"))), item["file_count"])
            self.assertFalse(any(payload_root.rglob("*.onnx")))
            self.assertFalse(any(payload_root.rglob("*.mp4")))

    def test_runtime_bom_pins_the_complete_package_set(self) -> None:
        bom = json.loads((PLUGIN_ROOT / "runtime-bom.json").read_text(encoding="utf-8"))
        release = json.loads((PLUGIN_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        expected = {
            "@joggai/smartvideo-avatar",
            "@joggai/smartvideo-editor",
            "@joggai/smartvideo-registry",
            "@joggai/smartvideo-renderer",
            "@joggai/smartvideo-runtime",
            "@joggai/smartvideo-speech",
        }
        self.assertEqual(bom["aggregate"], {"name": "@joggai/smartvideo", "version": "0.1.2"})
        self.assertEqual(set(bom["packages"]), expected)
        self.assertEqual(
            bom["packages"],
            {
                "@joggai/smartvideo-avatar": "0.1.0",
                "@joggai/smartvideo-editor": "0.1.0",
                "@joggai/smartvideo-registry": "0.1.0",
                "@joggai/smartvideo-renderer": "0.1.2",
                "@joggai/smartvideo-runtime": "0.1.0",
                "@joggai/smartvideo-speech": "0.1.0",
            },
        )
        self.assertEqual(bom["avatar_execution"], "jogg_remote_task_driver")
        self.assertEqual(
            bom["packaged_assets"],
            {
                "owner": "@joggai/smartvideo-runtime@0.1.0",
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
                "package": "@joggai/smartvideo@0.1.2",
                "upstream_cli": "@joggai/smartvideo-cli@0.0.7",
            },
        )
        self.assertEqual(
            release["plugin_runtime_files"],
            [
                "scripts/smart-video.sh",
                "scripts/smart-video.cmd",
                "scripts/smart-video.ps1",
                "scripts/video-studio.sh",
            ],
        )
        self.assertEqual(release["runtime_bom"]["sha256"], _sha256(PLUGIN_ROOT / "runtime-bom.json"))
        avatar_catalog = release["plugin_avatar_catalog"]
        self.assertEqual(avatar_catalog["root"], "assets/avatar-packs")
        self.assertEqual(avatar_catalog["catalog_sha256"], _sha256(PLUGIN_ROOT / avatar_catalog["root"] / "catalog.json"))
        self.assertEqual(len(avatar_catalog["templates"]), 1)
        for item in avatar_catalog["templates"]:
            self.assertEqual(
                item["integrity_sha256"],
                _sha256(PLUGIN_ROOT / avatar_catalog["root"] / item["payload_root"] / "integrity.json"),
            )

        self.assertEqual(
            release["npm_runtime"],
            {
                "registry": "https://registry.npmjs.org/",
                "package": "@joggai/smartvideo",
                "version": "0.1.2",
            },
        )
        self.assertFalse((PLUGIN_ROOT / "npm").exists())

    def test_release_hashes_reference_plugin_and_npm_owned_assets(self) -> None:
        manifest = json.loads((PLUGIN_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        runtime_root = NPM_ROOT / "packages" / "smartvideo-runtime"
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
        self.assertLess(len(runner.splitlines()), 230)
        for required in (
            "@joggai/smartvideo",
            "SMARTVIDEO_PACKAGE_SPEC",
            "npm install",
            "active-runtime.json",
            "SMARTVIDEO_PLUGIN_ROOT",
            "SMARTVIDEO_AVATAR_CATALOG_PATH",
            "exec \"$binary\"",
        ):
            self.assertIn(required, runner)
        self.assertIn('if runtime_ready; then', runner)
        self.assertNotIn("SMARTVIDEO_BUNDLED_PACKAGE", runner)
        for migrated in ("ensure_plugin_assets()", "apply_html_asset()", "wait_for_plugin_task()"):
            self.assertNotIn(migrated, runner)
        self.assertNotIn('SMARTVIDEO_ASSETS_ROOT="$PLUGIN_ROOT/assets"', runner)

    def test_windows_entrypoint_retains_host_bootstrap(self) -> None:
        cmd = (PLUGIN_ROOT / "scripts" / "smart-video.cmd").read_text(encoding="utf-8")
        powershell = (PLUGIN_ROOT / "scripts" / "smart-video.ps1").read_text(encoding="utf-8")
        self.assertIn("-ExecutionPolicy Bypass", cmd)
        self.assertIn("smart-video.ps1", cmd)
        self.assertIn('if ($action -in @("bootstrap", "install-deps"))', powershell)
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
        self.assertEqual(report["required"], "@joggai/smartvideo@0.1.2")
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

    def test_all_npm_package_sources_exist(self) -> None:
        bom = json.loads((PLUGIN_ROOT / "runtime-bom.json").read_text(encoding="utf-8"))
        self.assertTrue((NPM_ROOT / "packages" / "smartvideo" / "package.json").is_file())
        for name, version in bom["packages"].items():
            package_dir = NPM_ROOT / "packages" / name.removeprefix("@joggai/")
            metadata = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["name"], name)
            self.assertEqual(metadata["version"], version)


if __name__ == "__main__":
    unittest.main()
