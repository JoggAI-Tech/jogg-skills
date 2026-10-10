import { spawnSync } from "node:child_process";
import { accessSync, constants, existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pluginRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const args = process.argv.slice(2);
const configIndex = args.indexOf("--config");
const commands = [...args];
if (configIndex >= 0) commands.splice(configIndex, 2);
const action = commands[0] || "doctor";
const readOnly = ["doctor", "install-deps", "help", "--help", "-h", "paths", "version", "--version"].includes(action)
  || (action === "env" && commands[1] !== "configure")
  || (action === "resources" && [undefined, "list", "status"].includes(commands[1]));
const emit = (result, code = 2) => { process.stdout.write(`${JSON.stringify(result, null, 2)}\n`); process.exitCode = code; };
function readJson(location) { return JSON.parse(readFileSync(location, "utf8")); }
function verifyHome(root) {
 try {
  let ancestor = root;
  while (!existsSync(ancestor)) ancestor = path.dirname(ancestor);
  accessSync(ancestor, constants.R_OK | constants.W_OK | constants.X_OK);
  if (!readOnly) {
    mkdirSync(root, { recursive: true });
    const probe = mkdtempSync(path.join(root, ".smartvideo-write-check-"));
    rmSync(probe, { recursive: true });
  }
  return root;
 } catch (cause) {
   const error = new Error(`smartvideo_storage_unavailable: cannot read/write ${root}. Check filesystem permissions and Codex writable paths, or set SMARTVIDEO_HOME to an authorized workspace directory. ${cause.message}`, { cause });
   error.code = "smartvideo_storage_unavailable";
   throw error;
 }
}
function selectHome() {
  if (configIndex >= 0) {
    if (!args[configIndex + 1] || args[configIndex + 1].startsWith("--")) throw new Error("--config requires a file path");
    return verifyHome(path.dirname(path.resolve(args[configIndex + 1])));
  }
  if (process.env.SMARTVIDEO_CONFIG) return verifyHome(path.dirname(path.resolve(process.env.SMARTVIDEO_CONFIG)));
  if (process.env.SMARTVIDEO_HOME) return verifyHome(path.resolve(process.env.SMARTVIDEO_HOME));
  for (let directory = process.cwd(); ; directory = path.dirname(directory)) {
    const candidate = path.join(directory, ".smartvideo");
    if (!candidate.startsWith(pluginRoot + path.sep) && existsSync(candidate)) return verifyHome(candidate);
    if (path.dirname(directory) === directory) break;
  }
  try { return verifyHome(path.join(homedir(), ".codex", "smartvideo")); }
  catch {
    if (process.cwd() === pluginRoot || process.cwd().startsWith(pluginRoot + path.sep)) throw new Error("Start SmartVideo from a writable workspace or set SMARTVIDEO_HOME; the plugin installation cannot be used as automatic storage");
    const selected = verifyHome(path.join(process.cwd(), ".smartvideo"));
    process.stderr.write(`[smart-video] Using workspace data directory: ${selected}. Existing Home data has not been moved; use its original root to resume existing runs.\n`);
    return selected;
  }
}

try {
  const home = selectHome();
  const configPath = configIndex >= 0 ? path.resolve(args[configIndex + 1]) : process.env.SMARTVIDEO_CONFIG ? path.resolve(process.env.SMARTVIDEO_CONFIG) : path.join(home, "config.json");
  const config = existsSync(configPath) ? readJson(configPath) : {};
  const bom = readJson(path.join(pluginRoot, "runtime-bom.json"));
  const plugin = readJson(path.join(pluginRoot, ".codex-plugin/plugin.json"));
  const node = process.env.SMARTVIDEO_NODE_BINARY || config.tools?.node || process.execPath;
  const probe = spawnSync(node, ["--version"], { encoding: "utf8", windowsHide: true, timeout: 10000, killSignal: "SIGKILL" });
  const required = bom.minimum_node.split(".").map(Number);
  const detected = (probe.stdout || "").trim().replace(/^v/, "").split(".").map(Number);
  const compatible = probe.status === 0 && detected.length >= 3 && (detected[0] > required[0] || (detected[0] === required[0] && (detected[1] > required[1] || (detected[1] === required[1] && detected[2] >= required[2]))));
  if (!compatible) {
    emit({ schema: "smartvideo_environment_v1", status: "blocked", capability: "product-install", dependencies: [{ id: "node", status: probe.error ? "launch_failed" : "incompatible", executable: node, required_version: bom.minimum_node, install_guidance: { official_url: "https://nodejs.org/en/download", user_choices: ["agent", "manual", "existing_path", "skip"] } }] });
  } else {
    const releases = path.join(home, "node-runtime/releases");
    const installRoot = path.resolve(process.env.SMARTVIDEO_INSTALL_ROOT || path.join(releases, bom.aggregate.version));
    const entry = (root) => path.join(root, "node_modules", ...bom.aggregate.name.split("/"), "bin/smartvideo.mjs");
    const expected = { [bom.aggregate.name]: bom.aggregate.version, ...bom.packages };
    const ready = (root) => {
      try { return existsSync(entry(root)) && Object.entries(expected).every(([name, version]) => { const metadata = readJson(path.join(root, "node_modules", ...name.split("/"), "package.json")); return metadata.name === name && metadata.version === version; }); }
      catch { return false; }
    };
    if (["bootstrap", "upgrade"].includes(action) && !ready(installRoot)) {
      const npm = config.tools?.npm_cli || [path.join(path.dirname(node), "node_modules/npm/bin/npm-cli.js"), path.join(path.dirname(node), "../lib/node_modules/npm/bin/npm-cli.js")].find(existsSync);
      if (!npm || !path.isAbsolute(npm) || !existsSync(npm)) throw new Error("npm-cli.js is missing. Prepare Node.js from https://nodejs.org/en/download and register tools.npm_cli.");
      mkdirSync(releases, { recursive: true });
      const staging = mkdtempSync(path.join(releases, ".install-"));
      process.stderr.write(`[smart-video] Installing product packages ${bom.aggregate.name}@${bom.aggregate.version}\n`);
      const installed = spawnSync(node, [npm, "install", "--prefix", staging, "--ignore-scripts", "--no-audit", "--no-fund", "--no-package-lock", process.env.SMARTVIDEO_PACKAGE_SPEC || `${bom.aggregate.name}@${bom.aggregate.version}`], {
        env: { ...process.env, npm_config_cache: process.env.npm_config_cache || path.join(home, "cache/npm") }, stdio: ["ignore", 2, 2], windowsHide: true,
      });
      if (installed.status !== 0 || !ready(staging)) throw new Error(`Product installation failed or BOM mismatched; inspect ${staging}`);
      mkdirSync(path.dirname(installRoot), { recursive: true });
      if (existsSync(installRoot)) renameSync(installRoot, `${installRoot}.replaced.${Date.now()}`);
      renameSync(staging, installRoot);
    }
    if (!ready(installRoot)) {
      emit({ schema: "smartvideo_environment_v1", status: "blocked", capability: "product-install", error_code: "product_runtime_missing", required: bom.aggregate, install_guidance: { command: "bootstrap", user_choices: ["agent", "manual", "skip"] } }, action === "doctor" && !args.includes("--strict") ? 0 : 2);
    } else {
      if (["bootstrap", "upgrade"].includes(action)) {
        const active = path.join(home, "active-runtime.json");
        const temporary = `${active}.${process.pid}.tmp`;
        mkdirSync(home, { recursive: true });
        writeFileSync(temporary, `${JSON.stringify({ schema: "smartvideo_active_runtime_v1", package: bom.aggregate.name, version: bom.aggregate.version, install_root: installRoot, plugin_root: pluginRoot, activated_at: new Date().toISOString() })}\n`, { mode: 0o600 });
        renameSync(temporary, active);
      }
      const manifest = path.join(installRoot, "node_modules/@joggai/smartvideo-runtime/environment-manifest.json");
      if (!existsSync(manifest)) {
        emit({ schema: "smartvideo_environment_v1", status: "blocked", error_code: "runtime_update_required", detail: "This runtime predates on-demand preparation. Update the plugin BOM to a release with smartvideo_environment_v1." });
      } else {
        const forwarded = action === "upgrade" ? ["doctor", "--for", "service"] : commands.length ? commands : ["doctor"];
        const result = spawnSync(node, [entry(installRoot), "--config", configPath, ...forwarded], {
          env: { ...process.env, SMARTVIDEO_HOME: home, SMARTVIDEO_PLUGIN_ROOT: pluginRoot, SMARTVIDEO_PLUGIN_VERSION: plugin.version, SMARTVIDEO_SKILL_ROOT: path.join(pluginRoot, "skills/smart-video"), SMARTVIDEO_RELEASE_MANIFEST: path.join(pluginRoot, "release-manifest.json"), SMARTVIDEO_OAUTH_CLIENT_ID: "smart-video" },
          stdio: "inherit", windowsHide: true,
        });
        if (result.error) throw result.error;
        process.exitCode = result.status ?? 1;
      }
    }
  }
} catch (error) {
  emit({ schema: "smartvideo_environment_v1", status: "blocked", error_code: error.code === "smartvideo_storage_unavailable" ? error.code : "preparation_failed", detail: error.message }, 4);
}
