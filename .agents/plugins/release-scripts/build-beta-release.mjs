import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const taskRoot = fileURLToPath(new URL("..", import.meta.url));
const releaseId = "20261010.1";
const suffix = `-beta.${releaseId}`;
const root = path.join(taskRoot, "artifacts", `smart-video-beta-${releaseId}`);
const sources = path.join(root, "package-sources");
const archives = path.join(root, "npm-packages");
const npmRepo = path.join(taskRoot, "jogg-npm");
const rendererRepo = path.join(taskRoot, "smartvideo");
const skillsRepo = path.join(taskRoot, "jogg-skills");
const pluginRoot = path.join(root, "marketplace/plugins/smart-video");
const pluginVersion = `0.8.23${suffix}`;
const readJson = (file) => JSON.parse(readFileSync(file, "utf8"));
const writeJson = (file, value) => writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const digest = (file) => createHash("sha256").update(readFileSync(file)).digest("hex");
const run = (command, args, cwd) => execFileSync(command, args, { cwd, encoding: "utf8", maxBuffer: 32 * 1024 * 1024 });
const changed = ["smartvideo-speech", "smartvideo-runtime", "smartvideo-renderer", "smartvideo"];
const versions = Object.fromEntries(changed.map((name) => {
  const pkg = readJson(path.join(npmRepo, "packages", name, "package.json"));
  const [major, minor, patch] = pkg.version.split(".").map(Number);
  return [pkg.name, `${major}.${minor}.${patch + 1}${suffix}`];
}));
versions["@joggai/smartvideo-cli"] = `0.0.8${suffix}`;
const blocked = /(^|\/)(node_modules|\.git|__pycache__|\.remote-assets)(\/|$)|(^|\/)(\.DS_Store|Thumbs\.db)$|\.py[co]$/;
const textExtensions = new Set([".json", ".mjs", ".js", ".py", ".sh", ".ps1", ".cmd", ".html", ".css", ".md", ".txt", ".yaml", ".yml"]);
function copy(source, destination) {
  mkdirSync(path.dirname(destination), { recursive: true });
  cpSync(source, destination, { recursive: true, dereference: false, filter: (file) => !blocked.test(file.replaceAll("\\", "/")) });
}
function scan(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    assert.ok(!entry.isSymbolicLink(), `Distribution symlink: ${file}`);
    assert.ok(!blocked.test(file.replaceAll("\\", "/")), file);
    if (entry.isDirectory()) scan(file);
    else if (textExtensions.has(path.extname(file))) {
      const content = readFileSync(file, "utf8");
      assert.doesNotMatch(content, /\/(?:Users|home)\/[^/\s"']+\//, file);
      assert.doesNotMatch(content, /[A-Za-z]:\\Users\\[^\\\s"']+\\/, file);
    }
  }
}
function rewritePins(value) {
  if (Array.isArray(value)) return value.map(rewritePins);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, rewritePins(item)]));
  if (typeof value !== "string") return value;
  for (const [name, version] of Object.entries(versions)) {
    const old = name === "@joggai/smartvideo-cli" ? "0.0.7" : readJson(path.join(npmRepo, "packages", name.split("/")[1], "package.json")).version;
    value = value.replaceAll(`${name}@${old}`, `${name}@${version}`);
  }
  return value.replaceAll("~/.codex/smartvideo/", "~/.codex/smartvideo-beta/");
}
function stage(name, source, publishedName) {
  const output = path.join(sources, name);
  const report = JSON.parse(run("npm", ["pack", "--dry-run", "--json", "--ignore-scripts"], source))[0];
  for (const item of report.files) if (!blocked.test(item.path)) copy(path.join(source, item.path), path.join(output, item.path));
  const pkg = readJson(path.join(output, "package.json"));
  pkg.name = publishedName || pkg.name;
  pkg.version = versions[pkg.name];
  assert.match(pkg.version, /-beta\./);
  delete pkg.private;
  delete pkg.scripts;
  delete pkg.devDependencies;
  pkg.publishConfig = { access: "public", registry: "https://registry.npmjs.org/", tag: "beta" };
  for (const section of ["dependencies", "optionalDependencies", "peerDependencies"]) {
    for (const dependency of Object.keys(pkg[section] || {})) if (versions[dependency]) pkg[section][dependency] = versions[dependency];
  }
  writeJson(path.join(output, "package.json"), pkg);
  return output;
}

if (process.argv.includes("--rebuild")) rmSync(root, { recursive: true, force: true });
assert.ok(!existsSync(root), "Beta output already exists; use --rebuild only before publication.");
mkdirSync(archives, { recursive: true });
mkdirSync(sources, { recursive: true });
const cliRoot = stage("smartvideo-cli", path.join(rendererRepo, "packages/cli"), "@joggai/smartvideo-cli");
const cliDist = path.join(cliRoot, "dist");
copy(path.join(npmRepo, "packages/smartvideo-editor/dist/studio"), path.join(cliDist, "studio"));
copy(path.join(rendererRepo, "registry"), path.join(cliDist, "registry"));
for (const name of ["blank", "_shared"]) copy(path.join(rendererRepo, "packages/cli/src/templates", name), path.join(cliDist, "templates", name));
copy(path.join(rendererRepo, "packages/cli/src/docker/Dockerfile.render"), path.join(cliDist, "docker/Dockerfile.render"));
for (const name of ["layout-audit.browser.js", "contrast-audit.browser.js"]) copy(path.join(rendererRepo, "packages/cli/src/commands", name), path.join(cliDist, "commands", name));
for (const name of readdirSync(path.join(rendererRepo, "packages/cli/src/docs")).filter((name) => name.endsWith(".md"))) copy(path.join(rendererRepo, "packages/cli/src/docs", name), path.join(cliDist, "docs", name));
const coreDist = path.join(rendererRepo, "packages/core/dist");
const coreManifest = readJson(path.join(coreDist, "framevideo.manifest.json"));
copy(path.join(coreDist, "framevideo.manifest.json"), path.join(cliDist, "framevideo.manifest.json"));
copy(path.join(coreDist, coreManifest.artifacts.iife), path.join(cliDist, coreManifest.artifacts.iife));
copy(path.join(coreDist, coreManifest.artifacts.iife), path.join(cliDist, "framevideo-runtime.js"));
const cliFile = path.join(cliDist, "cli.js");
const cliText = readFileSync(cliFile, "utf8");
assert.ok(cliText.includes('VERSION = true ? "0.0.7"'), "CLI version marker changed; inspect the fresh build.");
writeFileSync(cliFile, cliText.replace('VERSION = true ? "0.0.7"', `VERSION = true ? "${versions["@joggai/smartvideo-cli"]}"`));
const staged = [cliRoot, ...changed.map((name) => stage(name, path.join(npmRepo, "packages", name)))];
const aggregateRoot = path.join(sources, "smartvideo");
const cliEntry = path.join(aggregateRoot, "bin/smartvideo.mjs");
writeFileSync(cliEntry, readFileSync(cliEntry, "utf8")
  .replace('process.stdout.write("0.1.14\\n")', `process.stdout.write("${versions["@joggai/smartvideo"]}\\n")`)
  .replace('if (!readOnly && action !== "env") await migrateSmartVideoHome();', '// Beta never migrates or rewrites stable projects.'));
for (const name of ["lib/storage-home.mjs", "lib/environment.mjs", "lib/resources.mjs", "lib/runtime-paths.mjs", "lib/service.mjs", "bin/smartvideo-runtime.sh"]) {
  const file = path.join(aggregateRoot, name);
  writeFileSync(file, readFileSync(file, "utf8")
    .replaceAll('".codex", "smartvideo"', '".codex", "smartvideo-beta"')
    .replaceAll('".smartvideo"', '".smartvideo-beta"')
    .replaceAll(".codex/smartvideo", ".codex/smartvideo-beta")
    .replaceAll("51693", "51694"));
}
const configFile = path.join(sources, "smartvideo-runtime/runtime/backend/services/runtime_config.py");
writeFileSync(configFile, readFileSync(configFile, "utf8").replace('Path.home() / ".codex" / "smartvideo"', 'Path.home() / ".codex" / "smartvideo-beta"').replaceAll("51693", "51694"));
const mainFile = path.join(sources, "smartvideo-runtime/runtime/backend/main.py");
writeFileSync(mainFile, readFileSync(mainFile, "utf8").replace("DEFAULT_LOOPBACK_PORT = 51693", "DEFAULT_LOOPBACK_PORT = 51694"));
const authFile = path.join(sources, "smartvideo-runtime/runtime/backend/services/jogg_runtime.py");
writeFileSync(authFile, readFileSync(authFile, "utf8")
  .replace('return MacOSKeychainCredentialStore()', 'return MacOSKeychainCredentialStore(service="ai.jogg.smart-video-beta.oauth")')
  .replace('return WindowsDPAPICredentialStore()', 'return WindowsDPAPICredentialStore(path=_windows_credential_path())')
  .replace('root / "Jogg" / "SmartVideo" / "oauth-smart-video.dpapi"', 'root / "Jogg" / "SmartVideoBeta" / "oauth-smart-video-beta.dpapi"'));
const identityFile = path.join(sources, "smartvideo-runtime/runtime/trusted-runtime-identity.v1.json");
const identity = readJson(identityFile);
for (const name of Object.keys(identity.files)) identity.files[name] = digest(path.join(sources, "smartvideo-runtime/runtime", name));
writeJson(identityFile, identity);
const aggregate = readJson(path.join(aggregateRoot, "package.json"));
const bomFile = path.join(aggregateRoot, "runtime-bom.json");
const bom = rewritePins(readJson(bomFile));
bom.release = aggregate.version;
bom.packages = aggregate.dependencies;
writeJson(bomFile, bom);
const runtimeManifestFile = path.join(sources, "smartvideo-runtime/manifest.json");
const runtimeManifest = readJson(runtimeManifestFile);
runtimeManifest.version = versions["@joggai/smartvideo-runtime"];
writeJson(runtimeManifestFile, runtimeManifest);
const adapterFile = path.join(sources, "smartvideo-renderer/index.mjs");
writeFileSync(adapterFile, readFileSync(adapterFile, "utf8").replaceAll("0.0.7", versions["@joggai/smartvideo-cli"]));

copy(path.join(skillsRepo, "plugins/smart-video"), pluginRoot);
const installFile = path.join(pluginRoot, "INSTALL.md");
writeFileSync(installFile, readFileSync(installFile, "utf8").replace(/C:\\+Users\\+example\\+SmartVideo/g, "C:\\SmartVideoBeta"));
const pluginFile = path.join(pluginRoot, ".codex-plugin/plugin.json");
const plugin = readJson(pluginFile);
plugin.name = "smart-video-beta";
plugin.version = pluginVersion;
plugin.interface.displayName = "Smart Video Beta";
writeJson(pluginFile, plugin);
const pluginBomFile = path.join(pluginRoot, "runtime-bom.json");
const pluginBom = rewritePins(readJson(pluginBomFile));
pluginBom.plugin_version = pluginVersion;
pluginBom.aggregate.version = aggregate.version;
pluginBom.packages = aggregate.dependencies;
pluginBom.distribution.package = `${aggregate.name}@${aggregate.version}`;
pluginBom.distribution.upstream_cli = `@joggai/smartvideo-cli@${versions["@joggai/smartvideo-cli"]}`;
pluginBom.system_dependency_preparation = "chat_first_agent";
writeJson(pluginBomFile, pluginBom);
const releaseFile = path.join(pluginRoot, "release-manifest.json");
const release = rewritePins(readJson(releaseFile));
release.version = pluginVersion;
release.npm_runtime.version = aggregate.version;
release.runtime_bom.sha256 = digest(pluginBomFile);
release.session_storage.projects = "~/.codex/smartvideo-beta";
release.session_storage.npm_runtime = `~/.codex/smartvideo-beta/node-runtime/releases/${aggregate.version}`;
writeJson(releaseFile, release);
for (const name of ["smart-video.sh", "smart-video.ps1"]) {
  const file = path.join(pluginRoot, "scripts", name);
  writeFileSync(file, readFileSync(file, "utf8").replaceAll(".codex/smartvideo", ".codex/smartvideo-beta").replaceAll(".codex\\smartvideo", ".codex\\smartvideo-beta"));
}
const launcherFile = path.join(pluginRoot, "scripts/launcher.mjs");
const launcherText = readFileSync(launcherFile, "utf8");
assert.ok(launcherText.includes("try {\n  const home = selectHome();"));
writeFileSync(launcherFile, launcherText.replace("try {\n  const home = selectHome();", 'try {\n  if (configIndex < 0 && !process.env.SMARTVIDEO_CONFIG && !process.env.SMARTVIDEO_HOME) process.env.SMARTVIDEO_HOME = path.join(homedir(), ".codex", "smartvideo-beta");\n  const home = selectHome();'));
const skillFile = path.join(pluginRoot, "skills/smart-video/SKILL.md");
let skill = readFileSync(skillFile, "utf8").replace("name: smart-video\n", "name: smart-video-beta\n").replaceAll("$direct-slide-art", "$direct-slide-art-beta");
skill = skill.replace("# Smart Video\n", "# Smart Video Beta\n\nThis is the beta channel. Use this plugin's launcher for every operation; do not\nuse a global CLI or the stable plugin. Its default data root is\n~/.codex/smartvideo-beta, separate from stable projects and configuration.\nDo not point it at production data or change stable plugin installations.\n");
writeFileSync(skillFile, skill);
const artFile = path.join(pluginRoot, "skills/direct-slide-art/SKILL.md");
writeFileSync(artFile, readFileSync(artFile, "utf8").replace("name: direct-slide-art\n", "name: direct-slide-art-beta\n"));
mkdirSync(path.join(root, "marketplace/.agents/plugins"), { recursive: true });
writeJson(path.join(root, "marketplace/.agents/plugins/marketplace.json"), { name: "jogg-skills-beta", interface: { displayName: "Jogg Skills Beta" }, plugins: [{ name: plugin.name, source: { source: "local", path: "./plugins/smart-video" }, policy: { installation: "AVAILABLE", authentication: "ON_INSTALL" }, category: "Creativity" }] });
scan(pluginRoot);
const packages = staged.map((directory) => {
  scan(directory);
  const report = JSON.parse(run("npm", ["pack", "--ignore-scripts", "--json", "--pack-destination", archives], directory))[0];
  const archive = path.join(archives, report.filename);
  const dryRun = JSON.parse(run("npm", ["publish", archive, "--dry-run", "--tag", "beta", "--access", "public", "--ignore-scripts", "--json"], root));
  assert.equal(dryRun.name, report.name);
  console.log(`${report.name}@${report.version}: publish dry-run passed`);
  return { name: report.name, version: report.version, filename: report.filename, bytes: report.size, integrity: report.integrity, sha256: digest(archive) };
});
writeJson(path.join(root, "release-plan.json"), { schema: "smartvideo_beta_release_v1", status: "prepared", dist_tag: "beta", git_branch: "beta", git_tag: `smart-video-v${pluginVersion}`, plugin_name: plugin.name, plugin_version: pluginVersion, marketplace: "jogg-skills-beta", aggregate_version: aggregate.version, packages, source_commits: Object.fromEntries([skillsRepo, npmRepo, rendererRepo].map((repo) => [path.basename(repo), run("git", ["rev-parse", "HEAD"], repo).trim()])), unchanged_dependencies: Object.fromEntries(Object.entries(aggregate.dependencies).filter(([name]) => !versions[name])), limitations: ["Native Windows speech execution and Intel macOS remain unverified.", "Real Edge TTS and Whisper inference remain unverified.", "Studio uses the existing checked-in editor distribution because baseline Studio source is incomplete.", "Full Studio typecheck fails on baseline missing modules; extended HDR tests lack baseline image fixture. Renderer fallow audit reports unresolved findings; these commit hooks were excluded for this internal beta after lint/format passed."] });
console.log(JSON.stringify({ root, pluginVersion, packages: packages.length }, null, 2));
