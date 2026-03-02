#!/usr/bin/env node

const { spawnSync, spawn } = require("node:child_process");
const path = require("node:path");

const pkg = require(path.join(__dirname, "..", "package.json"));
const cliArgs = process.argv.slice(2);
const defaultSpec = `google-workspace-mcp-advanced==${pkg.version}`;
const targetSpec = process.env.GWS_MCP_PYPI_SPEC || defaultSpec;

function commandAvailable(command, args) {
  const result = spawnSync(command, args, { encoding: "utf-8" });
  if (result.error) {
    return false;
  }
  return result.status === 0;
}

function startViaUvx(spec, args) {
  return {
    command: "uvx",
    args: ["--from", spec, "google-workspace-mcp-advanced", ...args]
  };
}

function startViaUvToolRun(spec, args) {
  return {
    command: "uv",
    args: ["tool", "run", "--from", spec, "google-workspace-mcp-advanced", ...args]
  };
}

let launch = null;
if (commandAvailable("uvx", ["--version"])) {
  launch = startViaUvx(targetSpec, cliArgs);
} else if (commandAvailable("uv", ["--version"])) {
  launch = startViaUvToolRun(targetSpec, cliArgs);
}

if (!launch) {
  console.error(
    "[google-workspace-mcp-advanced] Missing required runtime: install `uv` to use this launcher.\n" +
      "Install guide: https://docs.astral.sh/uv/getting-started/installation/"
  );
  process.exit(1);
}

const child = spawn(launch.command, launch.args, {
  stdio: "inherit",
  env: process.env
});

child.on("error", (error) => {
  console.error(`[google-workspace-mcp-advanced] Failed to start process: ${error.message}`);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});
