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

## CI Integration Notes
1. Lane A is suitable for standard CI by default.
2. Lane B and write-lane tests should be gated to protected environments.
3. OpenCode lane should skip gracefully when `opencode`/`node` are unavailable.
4. Keep `--live` SDK smoke opt-in because it executes a real prompt against the configured OpenCode model/provider.
