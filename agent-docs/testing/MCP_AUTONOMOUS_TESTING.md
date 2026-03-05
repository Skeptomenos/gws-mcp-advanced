# MCP Autonomous Testing

This document defines repeatable command lanes for protocol, live, and OpenCode MCP validation.

## Prerequisites
1. Install dev dependencies: `uv pip install -e ".[dev]"`
2. Ensure local auth config exists for the target account.
3. Restart OpenCode after code changes before manual/OpenCode validation.

## Lane A: Protocol (Local, No Live Mutations)
Runs stdio handshake + tool registry contract checks.

Command:
```bash
uv run pytest -m mcp_protocol tests/mcp_protocol -q
```

## Lane B: Live MCP (Environment Guarded)
Runs only when live env vars are explicitly enabled.

Required env:
1. `MCP_LIVE_TESTS=1`
2. `MCP_TEST_USER_EMAIL=<email>`

Optional env:
1. `MCP_TEST_ALLOW_WRITE=1` (required for write-lane tests)
2. `MCP_TEST_PREFIX=codex-it-`

Command:
```bash
uv run pytest -m live_mcp tests/live_mcp -q
```

Write-only subset:
```bash
uv run pytest -m "live_mcp and live_write" tests/live_mcp -q
```

## Lane C: OpenCode Smoke
Server spawn + health smoke:
```bash
./scripts/opencode_serve_smoke.sh
```

SDK/session wrapper (dry-run preflight):
```bash
node scripts/opencode_sdk_smoke.mjs --dry-run
```

SDK/session wrapper (full lifecycle: spawn -> /global/health -> attach prompt -> teardown):
```bash
OPENCODE_SMOKE_LIVE=1 node scripts/opencode_sdk_smoke.mjs --live
```

Pytest wrappers:
```bash
uv run pytest tests/opencode -q
```

Live pytest wrapper (opt-in only):
```bash
OPENCODE_SMOKE_LIVE=1 uv run pytest tests/opencode/test_opencode_sdk_session_flow.py -q
```

## Lane D: Live Artifact Cleanup
Dry-run preview (safe default):
```bash
uv run python scripts/mcp_live_cleanup.py \
  --user-email "$MCP_TEST_USER_EMAIL" \
  --artifact-prefix "${MCP_TEST_PREFIX:-codex-it-}" \
  --older-than-hours 24 \
  --services all
```

Execute cleanup:
```bash
uv run python scripts/mcp_live_cleanup.py \
  --user-email "$MCP_TEST_USER_EMAIL" \
  --artifact-prefix "${MCP_TEST_PREFIX:-codex-it-}" \
  --older-than-hours 24 \
  --services all \
  --execute
```

Notes:
1. Cleanup only targets resources whose name/title starts with the configured prefix.
2. Cleanup also enforces retention cutoff (`--older-than-hours`) before deletion.
3. Services supported today: `drive`, `calendar`, `tasks`.

## Cadence
Scheduled/manual cadence workflow:
1. `.github/workflows/live-mcp-cadence.yml`
2. Trigger modes:
   1. nightly schedule (`03:15 UTC`)
   2. manual `workflow_dispatch` (optional write lane + cleanup execute toggle)
3. Required repository secrets:
   1. `MCP_TEST_USER_EMAIL`
   2. `MCP_CREDENTIALS_JSON` (credential JSON for the test account)
4. Optional repository secret:
   1. `MCP_AUTH_CLIENTS_JSON` (when client-mapping config is required)
5. Optional repository variables:
   1. `MCP_TEST_PREFIX` (artifact prefix override)
   2. `MCP_LIVE_WRITE_CADENCE=1` (enable write lane by default)
   3. `MCP_LIVE_CLEANUP_EXECUTE=1` (enable execute-mode cleanup by default)

## CI Integration Notes
1. Lane A is suitable for standard CI by default.
2. Lane B and write-lane tests should be gated to protected environments.
3. Lane D should run after live lanes (preview always, execute by explicit policy).
4. OpenCode lane should skip gracefully when `opencode`/`node` are unavailable.
5. Keep `--live` SDK smoke opt-in because it executes a real prompt against the configured OpenCode model/provider.
