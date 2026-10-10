import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getResourceStatus } from "../jogg-npm/packages/smartvideo/lib/resources.mjs";

const taskRoot = fileURLToPath(new URL("..", import.meta.url));
const root = path.join(taskRoot, "artifacts/avatar-office-presenter-1.0.1");
const report = JSON.parse(readFileSync(path.join(root, "release.json")));
assert.equal(report.status, "published");
assert.equal(report.public_download_verified, true);
const home = path.join(root, "verification-home");
const parent = path.join(home, "resources/avatar-packs/releases/office-presenter");
const destination = path.join(parent, report.version);
if (!existsSync(destination)) {
  mkdirSync(parent, { recursive: true });
  execFileSync("tar", ["-xzf", path.join(root, "published-download.tar.gz"), "-C", parent, "--exclude=__MACOSX", "--exclude=.DS_Store", "--exclude=._*", report.archive_root], { env: { ...process.env, COPYFILE_DISABLE: "1" } });
  renameSync(path.join(parent, report.archive_root), destination);
}
const environment = { ...process.env, SMARTVIDEO_HOME: home, SMARTVIDEO_RESOURCE_ROOT: path.join(home, "resources/avatar-packs"), SMARTVIDEO_RESOURCE_CATALOG_PATH: path.join(taskRoot, "jogg-npm/packages/smartvideo/resources/avatar-packs.json") };
const status = getResourceStatus("office-presenter", environment);
assert.equal(status.version, "1.0.1");
assert.equal(status.installed, true);
assert.equal(status.error, undefined);
writeFileSync(path.join(root, "verification.json"), `${JSON.stringify({ status: "passed", public_archive_extraction: true, presenter_catalog_and_encrypted_integrity: true, version: status.version, inference_executed: false }, null, 2)}\n`);
console.log("Published resource extraction and Presenter integrity validation passed.");
