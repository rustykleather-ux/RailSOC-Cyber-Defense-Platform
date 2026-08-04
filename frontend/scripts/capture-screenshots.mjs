import { spawn } from "node:child_process";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const repoDir = path.resolve(frontendDir, "..");
const backendDir = path.join(repoDir, "backend");
const outputDir = path.join(repoDir, "docs", "screenshots");
const frontendUrl = "http://127.0.0.1:4173";
const backendUrl = "http://127.0.0.1:8010";
const onlyScreenshot = process.env.TRACKSENTINEL_SCREENSHOT;
const python = process.env.TRACKSENTINEL_PYTHON || path.join(
  backendDir,
  "venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);

const tempDir = await mkdtemp(path.join(os.tmpdir(), "tracksentinel-screenshots-"));
const databasePath = path.join(tempDir, "tracksentinel.db").replaceAll("\\", "/");
const databaseUrl = `sqlite:///${databasePath}`;
const processes = [];
const results = [];

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit", ...options });
    child.once("error", reject);
    child.once("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} exited with status ${code}`));
    });
  });
}

function start(command, args, options = {}) {
  const child = spawn(command, args, { stdio: "ignore", ...options });
  processes.push(child);
  return child;
}

async function waitFor(url, timeoutMs = 45_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The server may still be starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function capture(page, filename, route, prepare) {
  if (onlyScreenshot && onlyScreenshot !== filename) return;
  try {
    await page.goto(`${frontendUrl}${route}`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    await page.locator(".railsoc-main").waitFor({ state: "visible" });
    if (prepare) await prepare(page);
    await page.screenshot({
      path: path.join(outputDir, filename),
      fullPage: false,
      animations: "disabled",
    });
    results.push({ filename, status: "captured" });
    console.log(`Captured ${filename}`);
  } catch (error) {
    results.push({ filename, status: "failed", error: error.message });
    console.error(`Failed ${filename}: ${error.message}`);
  }
}

try {
  await mkdir(outputDir, { recursive: true });
  const backendEnv = {
    ...process.env,
    TRACKSENTINEL_DATABASE_URL: databaseUrl,
    TRACKSENTINEL_CORS_ORIGINS: frontendUrl,
    TRACKSENTINEL_DISPATCH_DELAY_SECONDS: "0",
  };

  console.log("Seeding an isolated screenshot database...");
  await run(python, ["seed.py"], { cwd: backendDir, env: backendEnv });
  start(python, ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8010"], {
    cwd: backendDir,
    env: backendEnv,
  });
  start(process.execPath, [path.join(frontendDir, "node_modules", "vite", "bin", "vite.js"), "--host", "127.0.0.1", "--port", "4173"], {
    cwd: frontendDir,
    env: { ...process.env, VITE_API_BASE_URL: backendUrl },
  });

  await Promise.all([
    waitFor(`${backendUrl}/docs`),
    waitFor(frontendUrl),
  ]);

  await fetch(`${backendUrl}/simulate-attack/firmware`, { method: "POST" });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    colorScheme: "dark",
  });
  const page = await context.newPage();
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  await capture(page, "dashboard.png", "/");
  await capture(page, "digital-twin.png", "/", async (current) => {
    await current.locator(".dt-map-scroll").scrollIntoViewIfNeeded();
  });
  await capture(page, "executive-dashboard.png", "/executive");
  await capture(page, "dispatcher-console.png", "/dispatcher");
  await capture(page, "operational-impact.png", "/dispatcher", async (current) => {
    await current.locator(".dt-impact-panel").scrollIntoViewIfNeeded();
  });
  await capture(page, "network-visibility.png", "/network");
  await capture(page, "purple-team-library.png", "/scenarios");
  await capture(page, "incident-center.png", "/incidents");
  await capture(page, "incident-analysis.png", "/incidents", async (current) => {
    await current.locator(".incident-card").first().click();
    const analysisHeading = current.getByRole("heading", { name: /AI Incident Analysis/ });
    await analysisHeading.waitFor({ timeout: 15_000 });
    await analysisHeading.scrollIntoViewIfNeeded();
  });
  await capture(page, "exercise-library.png", "/exercises");
  await capture(page, "exercise-running.png", "/exercises", async (current) => {
    await current.getByRole("button", { name: /Create run/ }).click();
    await current.getByRole("button", { name: /^Start$/ }).click();
    await current.getByRole("button", { name: /^objectives$/i }).click();
    await current.locator(".exercise-objective-diagnostics").waitFor();
  });
  await capture(page, "exercise-walkthrough.png", "/exercises", async (current) => {
    await current.getByRole("button", { name: /Create run/ }).click();
    await current.getByRole("button", { name: /^Start$/ }).click();
    await current.getByRole("button", { name: "Answer Sheet" }).click();
    current.once("dialog", (dialog) => dialog.accept());
    const revealResponse = current.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().includes("/walkthrough/reveal"),
    );
    await current.getByRole("button", { name: /Reveal answer sheet/ }).evaluate((button) => button.click());
    await revealResponse;
    await current.locator(".walkthrough-panel").waitFor();
  });
  await capture(page, "device-inventory.png", "/assets");
  await capture(page, "custom-ot-devices.png", "/assets", async (current) => {
    await current.getByRole("button", { name: "Create Device" }).click();
    await current.getByRole("heading", { name: "Create custom OT device" }).waitFor();
  });
  await capture(page, "live-telemetry.png", "/telemetry");

  await browser.close();
} finally {
  await Promise.all(processes.reverse().map((child) => new Promise((resolve) => {
    if (child.exitCode !== null) return resolve();
    child.once("exit", resolve);
    child.kill();
  })));
  await rm(tempDir, { recursive: true, force: true, maxRetries: 6, retryDelay: 500 });
}

const failed = results.filter((result) => result.status === "failed");
console.log(`Screenshot capture complete: ${results.length - failed.length}/${results.length} succeeded.`);
if (failed.length) {
  for (const result of failed) console.error(`- ${result.filename}: ${result.error}`);
  process.exitCode = 1;
}
