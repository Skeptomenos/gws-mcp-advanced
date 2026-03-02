# Execution Task Board

This file is the local task system for implementation.
Use this instead of external tickets.

Canonical plan: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/PLAN.md`
Status dashboard: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/docs/STATUS.md`
Dry-run tracker: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/docs/DRY_RUN_MATRIX.md`

## Metadata
- Last Updated (UTC): 2026-02-27
- Active Branch: `codex/run-01-fastmcp-import-smoke`
- Owner: Codex

## Status Legend
- `Not Started`
- `In Progress`
- `Blocked`
- `Done`

## Master Queue

| ID | Wave | Status | Next Action |
|---|---|---|---|
| SEC-01 | 1 | Done | Completed: default-deny unverified JWT identity, break-glass env override, and guardrail tests |
| RUN-01 | 1 | Done | Completed: import path fixed and CI startup smoke added |
| SEC-02 | 1 | Done | Completed: centralized secure atomic persistence + permission enforcement + tests |
| CONV-01 | 1 | Done | Completed: decorator order normalized, static checker added, CI gate + tests added |
| SAFE-01 | 2 | In Progress | Continue Wave 2A rollout after calendar + Drive file + Drive permission mutators (`gdocs/writing.py` next) |
| QUAL-01 | 2 | In Progress | Complete incremental type-check promotion plan; startup/static/format gates are in place |
| QUAL-02 | 2 | Not Started | Add high-risk runtime coverage and MCP protocol tests |
| RM-01 | 3 | Not Started | Implement code block visual parity |
| RM-02 | 3 | Not Started | Close table reliability gap with regressions/fallback |
| RM-03 | 3 | Not Started | Fix extra empty bullet after task lists |
| RM-04 | 3 | Not Started | Add deterministic image verification tests |
| DOC-01 | 0/3 | In Progress | Reconcile roadmap/testing docs to canonical status |
| DIST-00 | 5 | Not Started | Standardize scoped package naming across docs/workflows |
| DIST-01 | 5 | Not Started | Add version-coupled PyPI->npm release guard |
| DIST-02 | 5 | Not Started | Implement launcher preflight for missing `uvx` |
| DIST-03 | 6 | Not Started | Document deterministic pinned installs |
| DIST-04 | 5 | Not Started | Add trusted publishing + provenance checks |

## Wave 0 Tasks

- [x] Fix formatter drift in `gcalendar/calendar_tools.py`
- [x] Add `docs/STATUS.md`
- [x] Add `docs/DRY_RUN_MATRIX.md`
- [x] Add local task system in this file (`TASKS.md`)
- [ ] Reconcile stale roadmap/testing docs (`DOC-01`)

## Wave 1 Tasks (Security + Runtime)

### SEC-01
- [x] Map all identity sources in auth middleware/session store
- [x] Block unverified JWT identity claims by default
- [x] Add `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT=false` compatibility switch
- [x] Add negative tests for forged/unsigned identity tokens
- [x] Add positive tests for verified provider token path
- [x] Update `PLAN.md` + `docs/STATUS.md` evidence rows

### RUN-01
- [x] Fix broken imports/entrypoint behavior in `fastmcp_server.py`
- [x] Add startup smoke checks in CI for `import main` and `import fastmcp_server`
- [x] Add local smoke command to verification docs
- [x] Update `PLAN.md` evidence rows

### SEC-02
- [x] Add `auth/security_io.py` with atomic secure JSON writer
- [x] Apply secure writer in credential/session persistence code paths
- [x] Enforce strict file permissions for new writes
- [x] Add unit tests for atomicity and permissions behavior
- [x] Update `PLAN.md` evidence rows

### CONV-01
- [x] Normalize decorator order in identified outliers
- [x] Add `scripts/check_tool_decorators.py`
- [x] Wire checker into CI
- [x] Add tests for checker behavior

## Wave 2 Tasks (Safety + Quality)

### SAFE-01
- [ ] Implement Wave 2A dry-run defaults (high-risk mutators)
- [x] Implement Wave 2A dry-run defaults for `gcalendar/calendar_tools.py` (`create_event`, `modify_event`, `delete_event`)
- [x] Implement Wave 2A dry-run defaults for `gdrive/files.py` (`create_drive_file`, `update_drive_file`)
- [x] Implement Wave 2A dry-run defaults for `gdrive/permissions.py` (`share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership`)
- [ ] Implement Wave 2B dry-run defaults (remaining mutators)
- [ ] Add `scripts/check_dry_run_defaults.py`
- [ ] Add module-level dry-run tests per service
- [x] Update `docs/DRY_RUN_MATRIX.md` row statuses
- [x] Update `PLAN.md` evidence rows

### QUAL-01
- [x] Add blocking startup smoke checks in CI
- [x] Add blocking static safety checks in CI
- [x] Keep formatter gate in check mode only
- [ ] Define incremental type-check promotion plan

### QUAL-02
- [ ] Add protocol lane tests in `tests/mcp_protocol/`
- [ ] Add targeted auth/session regression coverage
- [ ] Add live MCP lane scaffolding in `tests/live_mcp/`
- [ ] Update verification protocol in docs

## Wave 3 Tasks (Roadmap Closure)

### RM-01
- [ ] Implement code block shading/border/language label behavior
- [ ] Add unit + integration coverage
- [ ] Validate against kitchen-sink scenarios

### RM-02
- [ ] Reproduce table reliability failures in deterministic tests
- [ ] Fix index math or apply fallback table-manager insertion path
- [ ] Add regression coverage and close open spec state

### RM-03
- [ ] Reproduce extra empty bullet after task lists
- [ ] Implement bullet reset correction
- [ ] Add regression tests for list transitions

### RM-04
- [ ] Add deterministic image insertion verification tests
- [ ] Validate structure assertions and non-regression behavior

### DOC-01
- [ ] Reconcile `ROADMAP.md` with current implementation reality
- [ ] Reconcile `TESTING_PLAN_MARKDOWN.md` open/closed states
- [ ] Mark stale reports as archived snapshots where appropriate
- [ ] Keep `docs/STATUS.md` synchronized with actual state

## Wave 4 Tasks (Autonomous MCP Verification)

- [ ] Add `tests/mcp_protocol/test_stdio_handshake.py`
- [ ] Add `tests/mcp_protocol/test_tool_registry_contract.py`
- [ ] Add `tests/live_mcp/conftest.py`
- [ ] Add `tests/live_mcp/helpers.py`
- [ ] Add `tests/live_mcp/test_live_smoke.py`
- [ ] Add `tests/live_mcp/test_markdown_features.py`
- [ ] Add `scripts/mcp_live_cleanup.py`
- [ ] Add `docs/MCP_AUTONOMOUS_TESTING.md`

## Wave 5-6 Tasks (Distribution)

### DIST-00
- [ ] Standardize package name to `@skeptomenos/gws-mcp-advanced` across all docs/config
- [ ] Add guard checks in release workflow

### DIST-01
- [ ] Add PyPI publish workflow
- [ ] Add npm publish workflow
- [ ] Block npm publish until matching PyPI version exists

### DIST-02
- [ ] Implement npm launcher preflight for `uvx`/`uv`
- [ ] Add clear failure remediation text
- [ ] Add launcher smoke tests

### DIST-03
- [ ] Add pinned install examples (`@x.y.z`) in docs
- [ ] Add rollback guidance for dist-tags

### DIST-04
- [ ] Configure trusted publishing (OIDC) for PyPI and npm
- [ ] Enable npm provenance output
- [ ] Verify release metadata checks in CI

## Verification Commands

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest -q`
- `uv run pytest -m mcp_protocol tests/mcp_protocol`
- `uv run pytest -m "live_mcp and live_write" tests/live_mcp`

## Session Log

- 2026-02-27: Created `TASKS.md` as local ticket-system replacement and populated all issue IDs with implementation steps.
- 2026-02-27: Closed `RUN-01` by fixing `fastmcp_server.py` docs import regression and adding CI startup smoke checks for `main` and `fastmcp_server`.
- 2026-02-27: Closed `SEC-01` by default-denying unverified JWT identity extraction in middleware, adding `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT` break-glass override, and adding auth/session guardrail tests.
- 2026-02-27: Closed `SEC-02` by adding shared secure atomic persistence helpers and wiring credential/session JSON writes to strict file and directory modes with dedicated tests.
- 2026-02-27: Closed `CONV-01` by enforcing standard decorator order, adding `scripts/check_tool_decorators.py`, adding checker tests, and integrating the checker into CI.
- 2026-02-27: Advanced `QUAL-01` by making startup/import smoke and decorator static checks blocking CI gates; incremental type-check promotion remains.
- 2026-02-27: Started `SAFE-01` Wave 2A by adding `dry_run=True` defaults and dry-run previews for calendar mutators, plus calendar dry-run contract tests.
- 2026-02-27: Continued `SAFE-01` Wave 2A by adding `dry_run=True` defaults and dry-run previews for `gdrive/files.py` mutators, plus runtime tests for dry-run skip and `dry_run=False` mutation paths.
- 2026-02-27: Continued `SAFE-01` Wave 2A by adding `dry_run=True` defaults and dry-run previews for `gdrive/permissions.py` mutators, plus runtime tests for default dry-run skip and explicit mutation paths.
