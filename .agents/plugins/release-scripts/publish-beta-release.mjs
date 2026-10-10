import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const taskRoot = fileURLToPath(new URL("..", import.meta.url));
const root = path.join(taskRoot, "artifacts/smart-video-beta-20261010.1");
const planFile = path.join(root, "release-plan.json");
const plan = JSON.parse(readFileSync(planFile));
assert.equal(JSON.parse(readFileSync(path.join(root, "verification.json"))).status, "passed");
assert.equal(plan.dist_tag, "beta");
const registry = "https://registry.npmjs.org/";
const npmJson = (args) => JSON.parse(execFileSync("npm", [...args, "--registry", registry, "--json"], { encoding: "utf8", maxBuffer: 16 * 1024 * 1024 }));
const actor = execFileSync("npm", ["whoami", "--registry", registry], { encoding: "utf8" }).trim();
assert.ok(["owner", "admin", "developer"].includes(npmJson(["org", "ls", "joggai"])[actor]), "Publishing account lacks organization rights.");
const resultFile = path.join(root, "npm-publication.json");
const state = existsSync(resultFile) ? JSON.parse(readFileSync(resultFile)) : { status: "publishing", actor, latest_before: Object.fromEntries(plan.packages.map((pkg) => [pkg.name, npmJson(["view", pkg.name, "dist-tags"]).latest])), published: [] };
const save = () => writeFileSync(resultFile, `${JSON.stringify(state, null, 2)}\n`);
state.submitted ||= [];
save();
for (const pkg of plan.packages) {
  assert.match(pkg.version, /-beta\./);
  const archive = path.join(root, "npm-packages", pkg.filename);
  assert.equal(createHash("sha256").update(readFileSync(archive)).digest("hex"), pkg.sha256);
  const existing = spawnSync("npm", ["view", `${pkg.name}@${pkg.version}`, "dist.integrity", "--registry", registry, "--json"], { encoding: "utf8" });
  if (existing.status === 0) assert.equal(JSON.parse(existing.stdout), pkg.integrity, "Existing immutable version has different contents.");
  else if (!state.submitted.includes(pkg.name)) {
    assert.ok(existing.stderr.includes("E404"), `Cannot inspect ${pkg.name}@${pkg.version}; do not publish blindly.`);
    console.log(`Publishing ${pkg.name}@${pkg.version} with tag beta`);
    const uploaded = spawnSync("npm", ["publish", archive, "--tag", "beta", "--access", "public", "--ignore-scripts", "--registry", registry, "--loglevel", "warn"], { stdio: "inherit" });
    if (uploaded.status !== 0) { state.status = "incomplete"; state.failed_package = pkg.name; save(); throw new Error(`npm publish failed for ${pkg.name}; successful uploads remain recorded.`); }
    state.submitted.push(pkg.name);
    save();
  }
}
// Registry processing can lag uploads; verify every dependency before opening the plugin channel.
for (const pkg of plan.packages) {
  let verified = false;
  for (let attempt = 0; attempt < 48; attempt++) {
    const available = spawnSync("npm", ["view", `${pkg.name}@${pkg.version}`, "dist.integrity", "--registry", registry, "--json", "--prefer-online"], { encoding: "utf8" });
    if (available.status === 0) { assert.equal(JSON.parse(available.stdout), pkg.integrity); verified = true; break; }
    assert.ok(available.stderr.includes("E404"), `Registry check failed for ${pkg.name}.`);
    if (attempt % 6 === 0) console.log(`Waiting for npm processing: ${pkg.name}@${pkg.version}`);
    await delay(5000);
  }
  assert.ok(verified, `npm is still processing ${pkg.name}; resume this script later without republishing.`);
  if (!state.published.some((item) => item.name === pkg.name)) state.published.push({ name: pkg.name, version: pkg.version, integrity: pkg.integrity });
  save();
}
state.latest_after = Object.fromEntries(plan.packages.map((pkg) => [pkg.name, npmJson(["view", pkg.name, "dist-tags"]).latest]));
assert.deepEqual(state.latest_after, state.latest_before, "Stable latest tags changed during publication.");
state.status = "published";
save();
plan.status = "npm-published";
writeFileSync(planFile, `${JSON.stringify(plan, null, 2)}\n`);
console.log("All beta npm packages published; stable latest tags unchanged.");
