# Live Cadence Workflow Guide

This guide explains the recurring live-validation workflow for this MCP.

Workflow file:
`.github/workflows/live-mcp-cadence.yml`

## What This Workflow Does

On each cadence run, it performs:

1. Preflight gating:
   1. checks that required secrets exist,
   2. skips cleanly if they are missing.
2. Credential-store bootstrap:
   1. writes credentials into a temporary `WORKSPACE_MCP_CONFIG_DIR` on the runner.
3. Test lanes:
   1. Lane A: protocol tests (`mcp_protocol`),
   2. Lane B: live tests (`live_mcp`),
   3. optional live write lane (`live_write`).
4. Artifact cleanup:
   1. always runs cleanup preview,
   2. runs destructive cleanup only when explicitly enabled.

## Trigger Modes

The workflow supports:

1. Nightly schedule (`03:15 UTC`).
2. Manual run (`workflow_dispatch`) with toggles:
   1. `run_write_lane`,
   2. `execute_cleanup`,
   3. `cleanup_older_than_hours`.

## Required Repository Secrets

1. `MCP_TEST_USER_EMAIL`
   1. Google account used for live MCP lanes.
2. `MCP_CREDENTIALS_JSON`
   1. OAuth credential JSON for that account.

Optional:

1. `MCP_AUTH_CLIENTS_JSON`
   1. Include when multi-client auth mapping is required.

## Optional Repository Variables

1. `MCP_TEST_PREFIX`
   1. Artifact prefix (default fallback: `codex-it-`).
2. `MCP_LIVE_WRITE_CADENCE`
   1. Set to `1` to run write lane by default on cadence runs.
3. `MCP_LIVE_CLEANUP_EXECUTE`
   1. Set to `1` to run destructive cleanup by default after cadence runs.

## How Cleanup Works

Cleanup command uses:
`scripts/mcp_live_cleanup.py`

Behavior:

1. Default mode is dry-run (safe preview).
2. Deletion only happens with `--execute`.
3. A resource is eligible only when:
   1. name/title starts with the configured prefix,
   2. timestamp is older than the retention window.
4. Current service support:
   1. Drive files,
   2. Calendar events,
   3. Tasks task lists.

## Manual Invocation Examples

Dry-run preview:

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

## Recommended Operating Policy

1. Keep write lane disabled by default.
2. Keep execute cleanup disabled by default.
3. Use manual dispatch for destructive operations unless team policy allows automated cleanup.
4. Always keep prefix scoping enabled so cleanup never touches non-test artifacts.
