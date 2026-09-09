"""Exercise plugin storage routing without installing or starting services."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "smart-video"


class SmartVideoStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="smartvideo-storage-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cwd = self.root
        self.home = self.root / "user home"
        self.home.mkdir()
        self.storage = self.root / "workspace" / "video data"
        self.runtime = self.root / "runtime"
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("SMARTVIDEO_", "SMART_VIDEO_", "npm_config_"))
        }
        self.env.update(HOME=str(self.home), SMARTVIDEO_HOME=str(self.storage))
        self.env.pop("OS", None)
        self.runner = PLUGIN_ROOT / "scripts" / "smart-video.sh"
        self.install_fixture()

    def install_fixture(self) -> None:
        bom = json.loads((PLUGIN_ROOT / "runtime-bom.json").read_text())
        packages = {bom["aggregate"]["name"]: bom["aggregate"]["version"], **bom["packages"]}
        for name, version in packages.items():
            manifest = self.runtime / "node_modules" / name / "package.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps({"name": name, "version": version}))
        binary = self.runtime / "node_modules" / ".bin" / "smartvideo"
        binary.parent.mkdir(parents=True)
        binary.write_text(
            "#!/usr/bin/env node\n"
            "const args = process.argv.slice(2);\n"
            f"if (args[0] === '--version') console.log({json.dumps(bom['aggregate']['version'])});\n"
            "else console.log(JSON.stringify({args, home:process.env.SMARTVIDEO_HOME}));\n"
        )
        binary.chmod(0o755)
        self.env["SMARTVIDEO_INSTALL_ROOT"] = str(self.runtime)

    def run_command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.runner), *args], env=self.env, cwd=self.cwd,
            capture_output=True, text=True, timeout=30, check=False,
        )

    def test_custom_home_routes_settings_and_preserves_space_arguments(self) -> None:
        result = self.run_command("settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["args"], ["--config", str(self.storage / "config.json"), "settings"])
        self.assertEqual(report["home"], str(self.storage))
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse(list(self.storage.glob(".smartvideo-write-check.*")))

    def test_explicit_config_wins_without_changing_resource_root(self) -> None:
        config = self.root / "separate config" / "custom.json"
        result = self.run_command("--config", str(config), "preflight")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "args": ["--config", str(config), "preflight"], "home": str(self.storage),
        })

    def test_doctor_does_not_create_storage_or_parent(self) -> None:
        result = self.run_command("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.storage.parent.exists())
        self.assertIn(str(self.storage / "config.json"), json.loads(result.stdout)["args"])

    def test_empty_or_missing_override_keeps_legacy_default(self) -> None:
        for value in (None, ""):
            with self.subTest(value=value):
                if value is None:
                    self.env.pop("SMARTVIDEO_HOME", None)
                else:
                    self.env["SMARTVIDEO_HOME"] = value
                self.env["CODEX_HOME"] = str(self.root / "unrelated codex home")
                result = self.run_command("doctor")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["home"], str(self.home / ".codex" / "smartvideo"))
                self.assertFalse((self.home / ".codex").exists())

    def test_node_only_commands_do_not_receive_config_prefix(self) -> None:
        for args in (("paths", "--json"), ("resources", "list", "--json")):
            with self.subTest(args=args):
                result = self.run_command(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["args"], list(args))

    def test_permission_failure_explains_path_and_recovery(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root bypasses Unix permission checks")
        self.storage.mkdir(parents=True)
        self.storage.chmod(0o500)
        self.addCleanup(self.storage.chmod, 0o700)
        for action in ("preflight", "settings", "bootstrap", "doctor"):
            with self.subTest(action=action):
                result = self.run_command(action)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("smartvideo_storage_unavailable", result.stderr)
                self.assertIn(str(self.storage), result.stderr)
                self.assertIn("SMARTVIDEO_HOME", result.stderr)
                self.assertIn("Codex", result.stderr)

    def test_actual_write_denial_is_caught_even_with_writable_mode_bits(self) -> None:
        tools = self.root / "tools"
        tools.mkdir()
        mktemp = tools / "mktemp"
        mktemp.write_text("#!/bin/sh\nprintf 'Permission denied\\n' >&2\nexit 1\n")
        mktemp.chmod(0o755)
        self.env["PATH"] = str(tools) + os.pathsep + self.env["PATH"]
        result = self.run_command("preflight")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("smartvideo_storage_unavailable", result.stderr)
        self.assertIn("Permission denied", result.stderr)

    def test_invalid_config_argument_stops_before_storage_creation(self) -> None:
        result = self.run_command("--config")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--config requires a file path", result.stderr)
        self.assertFalse(self.storage.parent.exists())

    def test_relative_home_is_resolved_before_delegation(self) -> None:
        self.env["SMARTVIDEO_HOME"] = "workspace/video data"
        result = self.run_command("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["home"]).resolve(), self.storage.resolve())

    def test_windows_paths_are_converted_for_shell_and_native_runtime(self) -> None:
        native_home = "C:/Users/Test User/Documents/Codex/.smartvideo"
        self.install_cygpath_fixture(self.storage, native_home)
        self.env.update(OS="Windows_NT", SMARTVIDEO_HOME=native_home.replace("/", "\\"))
        result = self.run_command("settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "args": ["--config", native_home + "/config.json", "settings"], "home": native_home,
        })
        self.assertTrue(self.storage.is_dir())

    def install_cygpath_fixture(self, shell_root: Path, native_root: str) -> None:
        tools = self.root / "tools"
        tools.mkdir()
        cygpath = tools / "cygpath"
        cygpath.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            f"shell_home = {str(shell_root)!r}\n"
            f"native_home = {native_root!r}\n"
            "value = sys.argv[-1].replace('\\\\', '/')\n"
            "if sys.argv[1] == '-au':\n"
            "    value = value.replace(native_home, shell_home, 1)\n"
            "else:\n"
            "    value = value.replace(shell_home, native_home, 1)\n"
            "print(value)\n"
        )
        cygpath.chmod(0o755)
        self.env["PATH"] = str(tools) + os.pathsep + self.env["PATH"]

    def test_windows_automatically_prefers_userprofile_over_git_bash_home(self) -> None:
        native_profile = "C:/Users/Test User"
        profile = self.root / "Windows profile"
        profile.mkdir()
        self.install_cygpath_fixture(profile, native_profile)
        self.env.pop("SMARTVIDEO_HOME")
        self.env.update(OS="Windows_NT", USERPROFILE=native_profile.replace("/", "\\"))
        result = self.run_command("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "args": ["--config", native_profile + "/.codex/smartvideo/config.json", "doctor"],
            "home": native_profile + "/.codex/smartvideo",
        })
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((profile / ".codex").exists())

    def deny_default_home(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root bypasses Unix permission checks")
        self.env.pop("SMARTVIDEO_HOME", None)
        self.home.chmod(0o500)
        self.addCleanup(self.home.chmod, 0o700)

    def test_automatic_fallback_uses_current_workspace(self) -> None:
        self.deny_default_home()
        result = self.run_command("settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = (self.root / ".smartvideo").resolve()
        self.assertEqual(Path(json.loads(result.stdout)["home"]).resolve(), expected)
        self.assertTrue(expected.is_dir())
        self.assertFalse((self.home / ".codex").exists())
        self.assertIn("Existing Home data has not been moved", result.stderr)

    def test_automatic_doctor_fallback_does_not_create_directories(self) -> None:
        self.deny_default_home()
        result = self.run_command("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["home"]).resolve(), (self.root / ".smartvideo").resolve())
        self.assertFalse((self.root / ".smartvideo").exists())
        self.assertFalse((self.home / ".codex").exists())

    def test_workspace_root_is_reused_from_subdirectories_when_home_recovers(self) -> None:
        selected = self.root / ".smartvideo"
        self.cwd = selected / "data" / "project" / "plans"
        self.cwd.mkdir(parents=True)
        self.env.pop("SMARTVIDEO_HOME")
        result = self.run_command("settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["home"]).resolve(), selected.resolve())
        self.assertFalse((self.home / ".codex").exists())

    def test_explicit_home_wins_over_existing_workspace_root(self) -> None:
        (self.root / ".smartvideo").mkdir()
        result = self.run_command("settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["home"], str(self.storage))

    def test_unwritable_existing_workspace_root_does_not_switch_to_home(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root bypasses Unix permission checks")
        selected = self.root / ".smartvideo"
        selected.mkdir()
        selected.chmod(0o500)
        self.addCleanup(selected.chmod, 0o700)
        self.env.pop("SMARTVIDEO_HOME")
        result = self.run_command("preflight")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("smartvideo_storage_unavailable", result.stderr)
        self.assertFalse((self.home / ".codex").exists())

    def test_both_locations_denied_produce_clear_error(self) -> None:
        self.deny_default_home()
        blocked_workspace = self.root / "blocked workspace"
        blocked_workspace.mkdir()
        blocked_workspace.chmod(0o500)
        self.addCleanup(blocked_workspace.chmod, 0o700)
        self.cwd = blocked_workspace
        result = self.run_command("preflight")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("smartvideo_storage_unavailable", result.stderr)
        self.assertIn(str(blocked_workspace.resolve()), result.stderr)

    def test_auto_selection_recovers_from_sandbox_write_probe_denial(self) -> None:
        self.env.pop("SMARTVIDEO_HOME")
        tools = self.root / "tools"
        tools.mkdir()
        mktemp = tools / "mktemp"
        mktemp.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            f"if sys.argv[-1].startswith({str(self.home)!r}): sys.exit(1)\n"
            f"os.execv({shutil.which('mktemp')!r}, ['mktemp', *sys.argv[1:]])\n"
        )
        mktemp.chmod(0o755)
        self.env["PATH"] = str(tools) + os.pathsep + self.env["PATH"]
        result = self.run_command("preflight")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["home"]).resolve(), (self.root / ".smartvideo").resolve())

    def test_auto_fallback_never_writes_inside_plugin_installation(self) -> None:
        self.deny_default_home()
        plugin = self.root / "plugin"
        shutil.copytree(PLUGIN_ROOT, plugin)
        self.runner = plugin / "scripts" / "smart-video.sh"
        self.cwd = plugin / "scripts"
        result = self.run_command("settings")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin installation cannot be used", result.stderr)
        self.assertFalse((self.cwd / ".smartvideo").exists())

    def test_real_runtime_workspace_uses_selected_root(self) -> None:
        configured = os.environ.get("SMARTVIDEO_STORAGE_TEST_RUNTIME")
        if not configured:
            self.skipTest("set SMARTVIDEO_STORAGE_TEST_RUNTIME to an installed npm runtime")
        runtime = Path(configured)
        plugin = self.root / "plugin"
        shutil.copytree(PLUGIN_ROOT, plugin)
        bom_path = plugin / "runtime-bom.json"
        bom = json.loads(bom_path.read_text())
        aggregate = json.loads((runtime / "node_modules/@joggai/smartvideo/package.json").read_text())
        bom["aggregate"]["version"] = aggregate["version"]
        for name in bom["packages"]:
            bom["packages"][name] = json.loads((runtime / "node_modules" / name / "package.json").read_text())["version"]
        bom_path.write_text(json.dumps(bom))
        self.runner = plugin / "scripts" / "smart-video.sh"
        self.env["SMARTVIDEO_INSTALL_ROOT"] = str(runtime)
        for automatic in (False, True):
            with self.subTest(automatic=automatic):
                if automatic:
                    self.deny_default_home()
                result = self.run_command("workspace")
                self.assertEqual(result.returncode, 0, result.stderr)
                selected = self.root / ".smartvideo" if automatic else self.storage
                workspace = Path(json.loads(result.stdout)["workspace_dir"]).resolve()
                self.assertTrue(workspace.is_relative_to((selected / "data").resolve()))
                for name in ("assets", "html", "plans"):
                    self.assertTrue((workspace / name).is_dir())
                self.assertFalse((self.home / ".codex").exists())


if __name__ == "__main__":
    unittest.main()
