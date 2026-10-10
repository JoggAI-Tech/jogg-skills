import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createReadStream, openAsBlob, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const taskRoot = fileURLToPath(new URL("..", import.meta.url));
const root = path.join(taskRoot, "artifacts/avatar-office-presenter-1.0.1");
const reportFile = path.join(root, "release.json");
const report = JSON.parse(readFileSync(reportFile));
assert.equal(report.payload_contents_unchanged, true);
const repository = path.join(taskRoot, "jogg-skills");
const credentialText = execFileSync("git", ["credential", "fill"], { cwd: repository, input: "protocol=https\nhost=github.com\npath=JoggAI-Tech/jogg-skills.git\n\n", encoding: "utf8" });
const credentials = Object.fromEntries(credentialText.trim().split("\n").map((line) => { const position = line.indexOf("="); return [line.slice(0, position), line.slice(position + 1)]; }));
assert.ok(credentials.password, "GitHub publishing credentials unavailable");
const api = "https://api.github.com/repos/JoggAI-Tech/jogg-skills";
async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { Authorization: `Bearer ${credentials.password}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", ...options.headers } });
  if (!response.ok) throw new Error(`GitHub release API returned HTTP ${response.status}`);
  return response.json();
}
const info = await request(api);
assert.equal(info.permissions.push, true);
const target = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repository, encoding: "utf8" }).trim();
const releases = await request(`${api}/releases?per_page=100`);
let release = releases.find((item) => item.tag_name === report.tag);
if (!release) release = await request(`${api}/releases`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tag_name: report.tag, target_commitish: target, name: "Office Presenter 1.0.1", draft: true, prerelease: true, body: "Remove macOS AppleDouble and Finder metadata from the Presenter resource archive for cross-platform installation. All 1.0.0 resource file contents are preserved.\n\nSHA-256: " + report.sha256 }) });
let asset = release.assets.find((item) => item.name === report.filename);
if (!asset) {
  assert.equal(release.draft, true, "Do not mutate an existing public release");
  asset = await request(release.upload_url.split("{")[0] + `?name=${encodeURIComponent(report.filename)}`, { method: "POST", headers: { "Content-Type": "application/gzip" }, body: await openAsBlob(path.join(root, report.filename)) });
}
assert.equal(asset.size, report.bytes);
if (asset.digest) assert.equal(asset.digest, `sha256:${report.sha256}`);
if (release.draft) release = await request(`${api}/releases/${release.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ draft: false, prerelease: true, make_latest: "false" }) });
assert.equal(release.prerelease, true);
assert.equal(release.draft, false);
const downloaded = path.join(root, "published-download.tar.gz");
execFileSync("curl", ["--fail", "--location", "--silent", "--show-error", "--retry", "3", "--output", downloaded, report.archive_url], { stdio: "inherit" });
const hash = createHash("sha256");
for await (const chunk of createReadStream(downloaded)) hash.update(chunk);
assert.equal(hash.digest("hex"), report.sha256);
Object.assign(report, { status: "published", release_url: release.html_url, public_download_verified: true });
writeFileSync(reportFile, `${JSON.stringify(report, null, 2)}\n`);
console.log(`Resource prerelease published and download verified: ${release.html_url}`);
