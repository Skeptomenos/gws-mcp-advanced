# Status Dashboard (Canonical)

This file is the high-level execution dashboard for active work.
Detailed implementation scope and issue-level tracking live in:
`/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`

## Metadata
- Last Updated (UTC): 2026-03-02T11:54:53Z
- Active Branch: `codex/run-01-fastmcp-import-smoke`
- Overall Status: Wave 3 is complete (`RM-01`..`RM-04` closed) and pre-merge kitchen-sink gate `OP-70` is PASS. OpenCode matrix is `81 PASS`, `0 FAIL`, `1 BLOCKED` (`OP-06` deferred by product decision). Wave 5 distribution work remains in progress.
- Implementation Readiness: `YES`

## Baseline Verification Snapshot

| Command | Result | Notes |
|---|---|---|
| `uv run ruff check .` | Pass | No lint violations |
| `uv run ruff format --check .` | Pass | Formatter drift corrected |
| `uv run pyright --project pyrightconfig.json` | Pass | Blocking source-scoped type gate is green (0 errors) |
| `uv run pytest` | Pass | 615 passed, 3 skipped |
| `uv run python scripts/check_dry_run_defaults.py` | Pass | Dry-run default static guard is green |
| `uv run python scripts/check_tool_decorators.py` | Pass | Decorator-order static guard is green |
| `uv run python scripts/check_distribution_scope.py` | Pass | Canonical npm package references are guarded (`google-workspace-mcp-advanced`) |
| `uv run python scripts/check_release_version_match.py` | Pass | npm and Python versions are coupled (`1.0.0`) |
| `uv run python -c "import main" && uv run python -c "import fastmcp_server"` | Pass | Startup/import smoke checks green |

## Wave Status

| Wave | Scope | Status | Exit Condition |
|---|---|---|---|
| Wave 0 | Setup and tracking artifacts | Done | Tracker artifacts and local task board are operational |
| Wave 1 | Security and runtime blockers | Done | `SEC-01`, `RUN-01`, `SEC-02`, `CONV-01` closed with tests |
| Wave 2 | Dry-run defaults and quality gates | Done | `SAFE-01`, `QUAL-01`, and `QUAL-02` are closed. |
| Wave 3 | Roadmap closure items | Done | `RM-01`..`RM-04` closed with evidence |
| Wave 4 | Autonomous MCP verification lanes | In Progress | Protocol/live/opencode lanes are implemented; OpenCode lifecycle smoke is now operational (`serve` spawn, `/global/health`, attached prompt, teardown). Remaining: optional cleanup automation script and broader live lane execution cadence |
| Wave 5 | npm/npx distribution infrastructure | In Progress | Canonical npm launcher, release workflows, package/version guards, and provenance publishing are implemented; first live publish validation remains |
| Wave 6 | Distribution validation and rollout | In Progress | Pinned install/rollback docs are complete; live channel validation (`latest`, `next`, pinned) remains |

## Current Focus
1. Add/commit release workflows to `main` so `workflow_dispatch` is available for `release-pypi.yml` and `release-npm.yml` (post-merge check still shows only `CI` workflow visible).
2. Run first end-to-end release validation (PyPI workflow then npm workflow) and confirm PyPI->npm gate behavior.
3. Verify trusted publisher/provenance and execute channel validation tests for `latest`, `next`, and pinned installs (`@x.y.z`) using `agent-docs/testing/DISTRIBUTION_TEST_PHASE.md`.

## Open Blockers
1. Distribution release validation remains blocked on workflows being present on default branch (`main`) (`DT-01`..`DT-07`).
2. External trusted-publisher setup in PyPI/npm project settings still requires first live validation evidence.
3. `OP-06` remains product-deferred and non-blocking.

## Update Rules
1. Update this file at the end of each implementation session.
2. Keep command results and wave statuses current.
3. If this file conflicts with `PLAN.md`, reconcile immediately in the same session.
4. When status is unclear across docs, verify code truth first (`implemented signatures`, `tests`, `scripts`) before marking items `Done`.
