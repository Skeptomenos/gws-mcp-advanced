#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import net from "node:net";
import process from "node:process";
import { setTimeout as sleep } from "node:timers/promises";

const DRY_RUN_FLAG = "--dry-run";
const LIVE_FLAG = "--live";
const DIR_FLAG = "--dir";
const OK_TOKEN = "OPCODE_SMOKE_OK";
const DEBUG = process.env.OPENCODE_SMOKE_DEBUG === "1";

function debugLog(message) {
  if (DEBUG) {
    console.error(`[opencode-sdk-smoke][debug] ${message}`);
  }
}

function getArgValue(flag) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1) return undefined;
  if (idx + 1 >= process.argv.length) return undefined;
  return process.argv[idx + 1];
}

function parseIntEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

async function getFreePort(hostname) {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, hostname, resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    server.close();
    throw new Error("Unable to allocate a free port");
  }
  const { port } = address;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function waitForHealth(baseUrl, child, timeoutMs, getLogs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`opencode serve exited early with code ${child.exitCode}\n${getLogs()}`);
    }

    try {
      const response = await fetch(`${baseUrl}/global/health`);
      if (response.ok) {
        const payload = await response.json();
        if (payload && payload.healthy === true) return payload;
      }
    } catch {
      // server may not be ready yet
    }

    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${baseUrl}/global/health\n${getLogs()}`);
}

function killProcessesListeningOnPort(port, signal = "SIGTERM") {
  const listed = spawnSync("lsof", ["-ti", `tcp:${port}`], {
    encoding: "utf-8",
  });
  if (listed.status !== 0 || !listed.stdout) return;
  for (const line of listed.stdout.split(/\r?\n/u).map((item) => item.trim()).filter(Boolean)) {
    const pid = Number.parseInt(line, 10);
    if (Number.isFinite(pid)) {
      if (pid === process.pid) continue;
      try {
        process.kill(pid, signal);
      } catch {
        // process may have exited between lsof and kill
      }
    }
  }
}

async function stopServer(child, port) {
  debugLog(`stopServer enter pid=${child.pid} exitCode=${child.exitCode}`);
  if (child.exitCode === null) {
    debugLog("sending SIGTERM to child");
    child.kill("SIGTERM");
  }
  await sleep(600);
  if (child.exitCode === null) {
    debugLog(`killing listeners on port ${port} with SIGTERM`);
    killProcessesListeningOnPort(port, "SIGTERM");
  }
  await sleep(600);
  if (child.exitCode === null) {
    debugLog("sending SIGKILL to child");
    child.kill("SIGKILL");
    killProcessesListeningOnPort(port, "SIGKILL");
  }
  child.stdout?.destroy();
  child.stderr?.destroy();
  child.unref();
}

function parsePromptOutput(stdout) {
  const lines = stdout
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .filter(Boolean);
  const events = [];
  for (const line of lines) {
    try {
      events.push(JSON.parse(line));
    } catch {
      // ignore non-JSON output fragments
    }
  }
  return events;
}

const isDryRun = process.argv.includes(DRY_RUN_FLAG);
const isLive = process.argv.includes(LIVE_FLAG);
const runDir = getArgValue(DIR_FLAG) ?? process.cwd();
const hostname = process.env.OPENCODE_SMOKE_HOST ?? "127.0.0.1";
const healthTimeoutMs = parseIntEnv("OPENCODE_SMOKE_HEALTH_TIMEOUT_MS", 30000);
const runTimeoutMs = parseIntEnv("OPENCODE_SMOKE_RUN_TIMEOUT_MS", 90000);

if (isDryRun && isLive) {
  console.error("[opencode-sdk-smoke] Use either --dry-run or --live, not both.");
  process.exit(1);
}

const versionResult = spawnSync("opencode", ["--version"], {
  encoding: "utf-8",
});
if (versionResult.error || versionResult.status !== 0) {
  const msg = versionResult.error?.message ?? versionResult.stderr ?? "opencode --version failed";
  console.error(`[opencode-sdk-smoke] ${msg}`.trim());
  process.exit(1);
}
const versionText = (versionResult.stdout || versionResult.stderr || "").trim();

if (isDryRun || !isLive) {
  console.log(
    `[opencode-sdk-smoke] dry-run OK (${versionText}) - run with ${LIVE_FLAG} to execute full serve lifecycle`,
  );
  process.exit(0);
}

const port = await getFreePort(hostname);
const baseUrl = `http://${hostname}:${port}`;
const serverArgs = ["serve", "--hostname", hostname, "--port", String(port), "--print-logs"];
const server = spawn("opencode", serverArgs, {
  stdio: ["ignore", "pipe", "pipe"],
  env: process.env,
});

let serverLogs = "";
const appendLog = (chunk) => {
  serverLogs += String(chunk);
  if (serverLogs.length > 12000) {
    serverLogs = serverLogs.slice(-12000);
  }
};
server.stdout.on("data", appendLog);
server.stderr.on("data", appendLog);

const getLogs = () => `--- opencode serve logs ---\n${serverLogs}`;

try {
  await waitForHealth(baseUrl, server, healthTimeoutMs, getLogs);

  const prompt = `Reply with ${OK_TOKEN} and nothing else`;
  const runArgs = [
    "run",
    prompt,
    "--attach",
    baseUrl,
    "--format",
    "json",
    "--dir",
    runDir,
  ];
  const modelOverride = process.env.OPENCODE_SMOKE_MODEL;
  if (modelOverride) {
    runArgs.push("--model", modelOverride);
  }

  const runResult = spawnSync("opencode", runArgs, {
    encoding: "utf-8",
    timeout: runTimeoutMs,
    env: process.env,
  });
  if (runResult.error) {
    throw new Error(`Failed to execute attached prompt: ${runResult.error.message}`);
  }
  if (runResult.status !== 0) {
    throw new Error(
      `Attached prompt failed with exit ${runResult.status}\nSTDOUT:\n${runResult.stdout}\nSTDERR:\n${runResult.stderr}`,
    );
  }

  const events = parsePromptOutput(runResult.stdout || "");
  const textEvents = events.filter((event) => event.type === "text" && event.part?.text);
  const gotToken = textEvents.some((event) => String(event.part.text).includes(OK_TOKEN));
  if (!gotToken) {
    throw new Error(
      `Expected ${OK_TOKEN} in text events.\nEvents:\n${JSON.stringify(events, null, 2)}`,
    );
  }

  const sessionId =
    events.find((event) => typeof event.sessionID === "string")?.sessionID ?? "unknown-session";
  console.log(
    `[opencode-sdk-smoke] PASS (${versionText}) baseUrl=${baseUrl} session=${sessionId}`,
  );
} finally {
  await stopServer(server, port);
}
