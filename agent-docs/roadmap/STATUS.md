# Status Dashboard (Canonical)

This file is the high-level execution dashboard for active work.
Detailed implementation scope and issue-level tracking live in:
`/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`

## Metadata
- Last Updated (UTC): 2026-03-03T10:40:00Z
- Active Branch: `main`
- Overall Status: Rename/migration hardening `DIST-05` is complete and verified. Authentication stabilization is closed: `AUTH-01` and `AUTH-02` are done with OpenCode runtime evidence (OP-74/OP-76 PASS, persisted credentials for both tenants). Release gate recovery is complete: `release-pypi.yml` failure on tag run `22617048674` was fixed via Pyright/type signature corrections and revalidated with successful publish run `22618871138` on `main` (`28509fc`).
- Implementation Readiness: `YES`

## Baseline Verification Snapshot

| Command | Result | Notes |
|---|---|---|
| `uv run ruff check .` | Pass | No lint violations |
| `uv run ruff format --check .` | Pass | `153` files unchanged |
| `uv run pyright --project pyrightconfig.json` | Pass | Blocking source-scoped type gate is green (0 errors) |
| `uv run pytest` | Pass | 648 passed, 3 skipped |
| `uv run python scripts/check_dry_run_defaults.py` | Pass | Dry-run default static guard is green |
| `uv run python scripts/check_tool_decorators.py` | Pass | Decorator-order static guard is green |
| `uv run python scripts/check_distribution_scope.py` | Pass | Canonical npm package references are guarded (`google-workspace-mcp-advanced`) |
| `uv run python -c "import main" && uv run python -c "import fastmcp_server"` | Pass | Startup/import smoke checks green |

## Wave Status

| Wave | Scope | Status | Exit Condition |
|---|---|---|---|
| Wave 0 | Setup and tracking artifacts | Done | Tracker artifacts and local task board are operational |
| Wave 1 | Security and runtime blockers | Done | `SEC-01`, `RUN-01`, `SEC-02`, `CONV-01` closed with tests |
| Wave 2 | Dry-run defaults and quality gates | Done | `SAFE-01`, `QUAL-01`, and `QUAL-02` are closed. |
| Wave 3 | Roadmap closure items | Done | `RM-01`..`RM-04` closed with evidence |
| Wave 4 | Autonomous MCP verification lanes | In Progress | Protocol/live/opencode lanes are implemented; OpenCode lifecycle smoke is now operational (`serve` spawn, `/global/health`, attached prompt, teardown). Remaining: optional cleanup automation script and broader live lane execution cadence |
| Wave 5 | Distribution infrastructure | Done | PyPI publish workflow and uvx runtime path are operational; npm/npx lane is de-scoped |
| Wave 6 | Distribution validation and rollout | Done | uvx stable/pinned validation is complete (`DT-01`..`DT-03`, `DT-08`) |

## Current Focus
1. Archive release evidence for run `22618871138` and keep distribution docs synchronized.
2. Optionally harden `complete_google_auth` user messaging for already-consumed callback state.
3. Start Wave 7 smart-chip roadmap (`RM-05`..`RM-07`) when product priorities allow.

## Open Blockers
1. None for auth track closure.

## Update Rules
1. Update this file at the end of each implementation session.
2. Keep command results and wave statuses current.
3. If this file conflicts with `PLAN.md`, reconcile immediately in the same session.
4. When status is unclear across docs, verify code truth first (`implemented signatures`, `tests`, `scripts`) before marking items `Done`.
