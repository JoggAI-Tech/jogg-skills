import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createServer } from "node:net";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const taskRoot = fileURLToPath(new URL("..", import.meta.url));
const releaseId = process.env.SMARTVIDEO_BETA_RELEASE_ID || "20261010.2";
assert.match(releaseId, /^\d{8}\.\d+$/);
const root = path.join(taskRoot, "artifacts", `smart-video-beta-${releaseId}`);
const plan = JSON.parse(readFileSync(path.join(root, "release-plan.json")));
const smoke = path.join(root, "smoke");
const home = path.join(smoke, "user-home");
const workspace = path.join(smoke, "workspace");
mkdirSync(path.join(workspace, ".smartvideo"), { recursive: true });
mkdirSync(home, { recursive: true });
writeFileSync(path.join(workspace, ".smartvideo/config.json"), '{"stable_sentinel":true}\n');
const dependencies = {};
for (const pkg of plan.packages) {
  const archive = path.join(root, "npm-packages", pkg.filename);
  assert.equal(createHash("sha256").update(readFileSync(archive)).digest("hex"), pkg.sha256);
  dependencies[pkg.name] = `file:${archive}`;
}
writeFileSync(path.join(smoke, "package.json"), JSON.stringify({ name: "smartvideo-beta-smoke", private: true, version: "1.0.0", dependencies }));
execFileSync("npm", ["install", "--prefix", smoke, "--ignore-scripts", "--no-audit", "--no-fund", "--no-package-lock"], { stdio: "inherit" });
const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith("SMARTVIDEO_") && !key.startsWith("FRAMEVIDEO_")));
Object.assign(environment, { HOME: home, USERPROFILE: home });
const aggregateRoot = path.join(smoke, "node_modules/@joggai/smartvideo");
const cli = path.join(aggregateRoot, "bin/smartvideo.mjs");
const run = (args) => execFileSync(process.execPath, [cli, ...args], { cwd: workspace, env: environment, encoding: "utf8" });
assert.equal(run(["--version"]).trim(), plan.aggregate_version);
const report = JSON.parse(run(["doctor", "--for", "local-asr", "--json"]));
assert.equal(report.config_path, path.join(home, ".codex/smartvideo-beta/config.json"));
assert.ok(report.dependencies.some((item) => item.id === "whisper-model"));
assert.ok(!report.dependencies.some((item) => /bridge|vosk|edge/.test(item.id)));
const tts = JSON.parse(run(["doctor", "--for", "local-tts", "--json"]));
assert.ok(!tts.dependencies.some((item) => /whisper|bridge|vosk/.test(item.id)));
const avatar = JSON.parse(run(["doctor", "--for", "local-avatar", "--json"]));
const avatarGuidance = avatar.dependencies.find((item) => item.id === "avatar-resources").install_guidance;
assert.equal(avatarGuidance.preferred_action, "agent");
assert.equal(avatarGuidance.user_choices, undefined);
assert.deepEqual(avatarGuidance.command, ["resources", "install", "office-presenter", "--json"]);
const created = JSON.parse(run(["workspace"]));
assert.ok(created.workspace_dir.startsWith(path.join(home, ".codex/smartvideo-beta/data/sessions")));
assert.equal(readFileSync(path.join(workspace, ".smartvideo/config.json"), "utf8"), '{"stable_sentinel":true}\n');
assert.ok(!existsSync(path.join(home, ".codex/smartvideo")));
const rendererRoot = path.join(smoke, "node_modules/@joggai/smartvideo-renderer");
const { resolveRendererCli } = await import(pathToFileURL(path.join(rendererRoot, "index.mjs")));
const rendererCli = resolveRendererCli();
const rendererVersion = execFileSync(process.execPath, [rendererCli, "--version"], { env: environment, cwd: workspace, encoding: "utf8" });
assert.ok(rendererVersion.includes(plan.packages.find((item) => item.name === "@joggai/smartvideo-cli").version));
const runtime = path.join(smoke, "node_modules/@joggai/smartvideo-runtime/runtime");
const venv = path.join(smoke, "venv");
const python = path.join(venv, process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python)) execFileSync("python3", ["-m", "venv", venv], { stdio: "inherit" });
execFileSync(python, ["-m", "pip", "install", "-r", path.join(runtime, "backend/requirements.txt")], { stdio: "inherit" });
assert.equal(JSON.parse(run(["env", "configure", "--tool", "service_python", "--path", python])).saved, true);
const portProbe = createServer();
await new Promise((resolve, reject) => { portProbe.once("error", reject); portProbe.listen(0, "127.0.0.1", resolve); });
const port = portProbe.address().port;
await new Promise((resolve) => portProbe.close(resolve));
const configPath = report.config_path;
const config = JSON.parse(readFileSync(configPath));
config.loopback = { base_url: `http://127.0.0.1:${port}` };
config.testing = { in_memory_credential_store: true };
writeFileSync(configPath, JSON.stringify(config));
const { startService } = await import(pathToFileURL(path.join(aggregateRoot, "lib/service.mjs")));
try {
  const service = await startService(configPath, { environment });
  assert.ok(!service.report);
  assert.equal(service.health.status, "ok");
  const response = await fetch(`${service.baseUrl}/api/v1/settings/environment?capability=service`);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).ready, true);
} finally {
  const stateFile = path.join(path.dirname(configPath), "service.json");
  if (existsSync(stateFile)) {
    const service = JSON.parse(readFileSync(stateFile));
    assert.equal(service.config_path, configPath);
    assert.equal(service.base_url, config.loopback.base_url);
    process.kill(service.pid, "SIGTERM");
  }
}
const identity = JSON.parse(readFileSync(path.join(runtime, "trusted-runtime-identity.v1.json")));
for (const [name, expected] of Object.entries(identity.files)) assert.equal(createHash("sha256").update(readFileSync(path.join(runtime, name))).digest("hex"), expected, name);
const pythonCheck = `
from pathlib import Path
from unittest.mock import Mock, patch
from backend.services import jogg_runtime, runtime_config
assert runtime_config.DEFAULT_LOOPBACK_BASE_URL == "http://127.0.0.1:51694"
with patch.object(jogg_runtime.sys, "platform", "darwin"), patch.object(jogg_runtime, "MacOSKeychainCredentialStore") as store:
    jogg_runtime._default_credential_store()
    store.assert_called_once_with(service="ai.jogg.smart-video-beta.oauth")
with patch.object(jogg_runtime.sys, "platform", "win32"), patch.object(jogg_runtime, "WindowsDPAPICredentialStore") as store:
    jogg_runtime._default_credential_store()
    assert "SmartVideoBeta" in str(store.call_args.kwargs["path"])
print("beta credentials and loopback isolation passed")
`;
execFileSync(python, ["-c", pythonCheck], { env: { ...environment, PYTHONPATH: runtime, PYTHONDONTWRITEBYTECODE: "1" }, stdio: "inherit" });
for (const [name, version] of Object.entries(plan.unchanged_dependencies)) assert.equal(JSON.parse(readFileSync(path.join(smoke, "node_modules", ...name.split("/"), "package.json"))).version, version);
writeFileSync(path.join(root, "verification.json"), `${JSON.stringify({ status: "passed", local_tarball_install: true, beta_storage_isolated: true, stable_workspace_unchanged: true, credential_namespace_isolated: true, default_port: 51694, exact_dependencies: true, service_health_and_environment_api: true, renderer_version: rendererVersion.trim(), runtime_identity_hashes: true, tts_asr_checks_independent: true }, null, 2)}\n`);
console.log("Beta clean-install verification passed.");
