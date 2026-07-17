#!/usr/bin/env node

import { once } from "node:events";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";

function argumentsByName(values) {
  const result = new Map();
  for (let index = 0; index < values.length; index += 2) {
    const name = values[index];
    const value = values[index + 1];
    if (!name?.startsWith("--") || value === undefined) throw new Error(`invalid argument: ${name || ""}`);
    result.set(name.slice(2), value);
  }
  return result;
}

function required(args, name) {
  const value = args.get(name);
  if (!value) throw new Error(`missing --${name}`);
  return value;
}

export function frameTimes(duration, frameRate, startMs = 0) {
  const durationMs = Math.max(0, duration * 1000);
  const stepMs = 1000 / frameRate;
  const times = Array.from({ length: Math.floor(durationMs / stepMs) + 1 }, (_, index) => index * stepMs);
  if (!times.length || durationMs - times.at(-1) > 0.0001) times.push(durationMs);
  return times.map((value) => Number((startMs + Math.min(durationMs, value)).toFixed(6)));
}

async function openCdp(url, timeoutMs) {
  const socket = new WebSocket(url);
  let openTimer;
  try {
    await Promise.race([
      once(socket, "open"),
      once(socket, "error").then(([error]) => Promise.reject(error)),
      new Promise((_, reject) => {
        openTimer = setTimeout(() => reject(new Error("timed out opening Chrome DevTools")), timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(openTimer);
  }
  let requestId = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(String(event.data));
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    clearTimeout(request.timer);
    if (message.error) request.reject(new Error(`${request.method} failed: ${message.error.message || "unknown error"}`));
    else request.resolve(message.result || {});
  });
  socket.addEventListener("close", () => {
    for (const request of pending.values()) request.reject(new Error("Chrome DevTools connection closed"));
    pending.clear();
  });
  return {
    socket,
    call(method, params = {}, sessionId = "") {
      return new Promise((resolve, reject) => {
        const id = ++requestId;
        const timer = setTimeout(() => {
          pending.delete(id);
          reject(new Error(`${method} timed out`));
        }, timeoutMs);
        pending.set(id, { method, resolve, reject, timer });
        socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
      });
    },
  };
}

function freezeExpression(timeMs) {
  return `(async()=>{const t=${Number(timeMs).toFixed(6)};const documents=[document];for(const frame of document.querySelectorAll('iframe[srcdoc]')){try{if(frame.contentDocument)documents.push(frame.contentDocument)}catch(_){}}for(const currentDocument of documents){if(currentDocument.fonts&&currentDocument.fonts.ready)await currentDocument.fonts.ready;for(const animation of currentDocument.getAnimations({subtree:true})){try{animation.pause();animation.currentTime=t}catch(_){}}if(currentDocument.documentElement)currentDocument.documentElement.getBoundingClientRect()}return true})()`;
}

async function writeFrame(cdp, sessionId, timeMs) {
  const evaluated = await cdp.call("Runtime.evaluate", {
    expression: freezeExpression(timeMs),
    awaitPromise: true,
    returnByValue: true,
    userGesture: false,
  }, sessionId);
  if (evaluated.exceptionDetails) throw new Error("local HTML animation evaluation failed");
  const screenshot = await cdp.call("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    optimizeForSpeed: true,
  }, sessionId);
  if (!screenshot.data) throw new Error(`Chrome returned an empty frame at ${timeMs}ms`);
  if (!process.stdout.write(Buffer.from(screenshot.data, "base64"))) await once(process.stdout, "drain");
}

async function main() {
  const major = Number.parseInt(process.versions.node.split(".")[0], 10);
  if (major < 22 || typeof WebSocket !== "function") throw new Error("Node.js 22 or newer is required");
  const args = argumentsByName(process.argv.slice(2));
  const chromeBinary = required(args, "chrome");
  const profileDir = required(args, "profile");
  const pageUri = required(args, "page");
  const width = Number.parseInt(args.get("width") || "1920", 10);
  const height = Number.parseInt(args.get("height") || "1080", 10);
  const timeoutMs = Number.parseInt(args.get("timeout-ms") || "20000", 10);
  const keyframeMs = args.has("at-ms") ? Number(args.get("at-ms")) : null;
  const duration = Number(args.get("duration") || "0");
  const frameRate = Number(args.get("frame-rate") || "0");
  const startMs = Number(args.get("start-ms") || "0");
  if (keyframeMs === null && (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(frameRate) || frameRate <= 0)) {
    throw new Error("invalid capture duration or frame rate");
  }
  if (!Number.isFinite(startMs) || startMs < 0) throw new Error("invalid capture start time");
  const times = keyframeMs === null ? frameTimes(duration, frameRate, startMs) : [keyframeMs];
  if (!times.length || times.some((value) => !Number.isFinite(value) || value < 0)) throw new Error("invalid capture timing");

  fs.mkdirSync(profileDir, { recursive: true });
  fs.rmSync(path.join(profileDir, "DevToolsActivePort"), { force: true });
  const chrome = spawn(chromeBinary, [
    "--headless=new",
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=0",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=Translate,MediaRouter",
    "--disable-sync",
    "--hide-scrollbars",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-default-browser-check",
    "--no-first-run",
    "--force-color-profile=srgb",
    `--window-size=${width},${height}`,
    `--user-data-dir=${profileDir}`,
  ], { stdio: ["ignore", "ignore", "pipe"] });
  let stderr = "";
  chrome.stderr.setEncoding("utf8");
  chrome.stderr.on("data", (chunk) => { stderr = `${stderr}${chunk}`.slice(-65536); });
  let cdp;
  try {
    const browserUrl = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("timed out connecting to local Chrome DevTools")), timeoutMs);
      const inspect = () => {
        const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
        if (!match) return;
        clearTimeout(timer);
        resolve(match[1]);
      };
      chrome.stderr.on("data", inspect);
      chrome.once("exit", (code) => reject(new Error(`local Chrome exited with code ${code}`)));
      inspect();
    });
    const port = new URL(browserUrl).port;
    const created = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent("about:blank")}`, { method: "PUT" });
    if (!created.ok) throw new Error(`Chrome could not create a capture page: HTTP ${created.status}`);
    const target = await created.json();
    if (!target.webSocketDebuggerUrl) throw new Error("Chrome capture page has no DevTools endpoint");
    cdp = await openCdp(target.webSocketDebuggerUrl, timeoutMs);
    const sessionId = "";
    await cdp.call("Page.enable");
    await cdp.call("Runtime.enable");
    await cdp.call("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    await cdp.call("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });
    await cdp.call("Page.navigate", { url: pageUri });
    await new Promise((resolve) => setTimeout(resolve, 100));
    for (const timeMs of times) await writeFrame(cdp, sessionId, timeMs);
    await new Promise((resolve) => process.stdout.write("", resolve));
  } finally {
    try { cdp?.socket.close(); } catch (_) {}
    if (chrome.exitCode === null) chrome.kill("SIGTERM");
    await Promise.race([once(chrome, "exit"), new Promise((resolve) => setTimeout(resolve, 3000))]);
    if (chrome.exitCode === null) chrome.kill("SIGKILL");
    if (process.exitCode && stderr.trim()) process.stderr.write(stderr);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().then(
    () => process.exit(0),
    (error) => {
      process.stderr.write(`${error?.stack || error}\n`);
      process.exit(1);
    },
  );
}
