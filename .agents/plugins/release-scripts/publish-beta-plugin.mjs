import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const taskRoot = fileURLToPath(new URL("..", import.meta.url));
const releaseId = process.env.SMARTVIDEO_BETA_RELEASE_ID || "20261010.3";
assert.match(releaseId, /^\d{8}\.\d+$/);
const root = path.join(taskRoot, "artifacts", `smart-video-beta-${releaseId}`);
const repository = path.join(taskRoot, "jogg-skills");
const market = path.join(root, "marketplace");
const planFile = path.join(root, "release-plan.json");
const plan = JSON.parse(readFileSync(planFile));
assert.equal(JSON.parse(readFileSync(path.join(root, "npm-publication.json"))).status, "published");
assert.equal(JSON.parse(readFileSync(path.join(root, "verification.json"))).status, "passed");
const git = (args, options = {}) => {
  const output = execFileSync("git", args, { cwd: repository, encoding: "utf8", ...options });
  return typeof output === "string" ? output.trim() : "";
};
const mainBefore = git(["ls-remote", "--heads", "origin", "main"]).split(/\s+/)[0];
assert.equal(mainBefore, "dddf9df5d46ffd2420977ed9bfd19e0d2b39e500", "Main changed since task preparation; recheck release boundaries.");
const manifest = { ...plan, status: "published", installation: [`codex plugin marketplace add JoggAI-Tech/jogg-skills --ref ${plan.git_branch}`, `codex plugin add ${plan.plugin_name}@${plan.marketplace}`], data_root: "~/.codex/smartvideo-beta", default_port: 51694, credentials: "separate macOS Keychain service and Windows DPAPI file" };
const recipes = path.join(market, ".agents/plugins/release-scripts");
mkdirSync(recipes, { recursive: true });
for (const name of ["build-beta-release.mjs", "verify-beta-release.mjs", "publish-beta-release.mjs", "publish-beta-plugin.mjs", "verify-published-beta.mjs", "prepare-avatar-resource-release.py", "publish-avatar-resource-release.mjs", "verify-avatar-resource-release.mjs"]) cpSync(path.join(taskRoot, "packaging", name), path.join(recipes, name));
const resourceReportFile = path.join(taskRoot, "artifacts/avatar-office-presenter-1.0.1/release.json");
const resourceReport = JSON.parse(readFileSync(resourceReportFile));
assert.equal(resourceReport.status, "published");
assert.equal(resourceReport.public_download_verified, true);
assert.equal(JSON.parse(readFileSync(path.join(taskRoot, "artifacts/avatar-office-presenter-1.0.1/verification.json"))).status, "passed");
cpSync(resourceReportFile, path.join(market, ".agents/plugins/avatar-resource-release.json"));
writeFileSync(path.join(market, ".agents/plugins/beta-release.json"), `${JSON.stringify(manifest, null, 2)}\n`);
writeFileSync(path.join(market, "BETA.md"), `# Smart Video Beta\n\nPlugin: ${plan.plugin_name}@${plan.plugin_version}. This channel is for internal\ntesting; prerelease labels do not make public packages private.\n\nInstall the moving beta branch:\n\n\x60\x60\x60sh\ncodex plugin marketplace add JoggAI-Tech/jogg-skills --ref beta\ncodex plugin add smart-video-beta@jogg-skills-beta\n\x60\x60\x60\n\nFor a reproducible installation, replace beta with ${plan.git_tag}.\nUse this plugin's launcher; system and Python dependencies are prepared by the\nAgent in chat only when a requested capability needs them.\n\nDefault data: ~/.codex/smartvideo-beta. Default service port: 51694.\nOAuth uses a separate Keychain service or Windows DPAPI file and does not migrate\nstable credentials. Do not explicitly point beta at stable projects or config.\nStable main and npm latest are unchanged.\n\nKnown test limits:\n\n${plan.limitations.map((item) => `- ${item}`).join("\n")}\n\nExact packages and source commits: .agents/plugins/beta-release.json.\n`);
const resultFile = path.join(root, "github-publication.json");
let commit;
if (existsSync(resultFile)) commit = JSON.parse(readFileSync(resultFile)).commit;
else {
  const parent = git(["rev-parse", "HEAD"]);
  assert.equal(parent, plan.source_commits["jogg-skills"]);
  const index = path.join(mkdtempSync(path.join(root, ".release-index-")), "index");
  const environment = { ...process.env, GIT_INDEX_FILE: index };
  git(["read-tree", parent], { env: environment });
  function add(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) add(file);
      else {
        assert.ok(entry.isFile());
        const relative = path.relative(market, file).replaceAll("\\", "/");
        const hash = git(["hash-object", "-w", file]);
        git(["update-index", "--add", "--cacheinfo", statSync(file).mode & 0o111 ? "100755" : "100644", hash, relative], { env: environment });
      }
    }
  }
  add(market);
  const tree = git(["write-tree"], { env: environment });
  const previousBeta = git(["ls-remote", "--heads", "origin", plan.git_branch]).split(/\s+/)[0];
  const parents = ["-p", parent];
  if (previousBeta && previousBeta !== parent) {
    git(["fetch", "origin", `refs/heads/${plan.git_branch}`]);
    parents.push("-p", previousBeta);
  }
  commit = git(["commit-tree", tree, ...parents, "-m", `release: publish isolated Smart Video ${plan.plugin_version}`]);
  writeFileSync(resultFile, `${JSON.stringify({ status: "prepared", commit, branch: plan.git_branch, tag: plan.git_tag, main_before: mainBefore }, null, 2)}\n`);
}
git(["push", "origin", `${commit}:refs/heads/${plan.git_branch}`], { stdio: ["ignore", "inherit", "inherit"] });
if (git(["tag", "--list", plan.git_tag])) assert.equal(git(["rev-parse", `refs/tags/${plan.git_tag}`]), commit);
else git(["tag", plan.git_tag, commit]);
git(["push", "origin", `refs/tags/${plan.git_tag}`], { stdio: ["ignore", "inherit", "inherit"] });
const remote = git(["ls-remote", "origin", `refs/heads/${plan.git_branch}`, `refs/tags/${plan.git_tag}`, "refs/heads/main"]);
assert.ok(remote.includes(`${commit}\trefs/heads/${plan.git_branch}`));
assert.ok(remote.includes(`${commit}\trefs/tags/${plan.git_tag}`));
assert.ok(remote.includes(`${mainBefore}\trefs/heads/main`));
writeFileSync(resultFile, `${JSON.stringify({ status: "published", commit, branch: plan.git_branch, tag: plan.git_tag, main_before: mainBefore, main_after: mainBefore }, null, 2)}\n`);
plan.status = "published";
writeFileSync(planFile, `${JSON.stringify(plan, null, 2)}\n`);
console.log("Beta branch and immutable tag published; main unchanged.");
