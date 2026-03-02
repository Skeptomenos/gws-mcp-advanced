# ExecPlan: GWS MCP Hardening, Roadmap Closure, and Autonomous MCP Verification

## Living Document Controls
1. Status: `IN_IMPLEMENTATION`
2. Last Updated (UTC): `2026-02-27`
3. Canonical Path: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/PLAN.md`
4. Active Branch: `codex/run-01-fastmcp-import-smoke`
5. Local Task Board: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/TASKS.md`
6. Update Cadence:
   1. update this file after every completed issue ID (`SEC-*`, `SAFE-*`, `DIST-*`, etc.),
   2. update this file at the end of each implementation session,
   3. update this file before opening or merging any PR.
7. Source-of-Truth Rule: if another planning file conflicts with this document, this document wins until reconciliation.

## Implementation Readiness Verdict
1. Verdict: `YES`, preflight is complete and implementation is active.
2. Immediate preflight tasks (execute first):
   1. [x] Reformat `gcalendar/calendar_tools.py` so local quality protocol is green (`uv run ruff format --check .`).
   2. [x] Create `docs/STATUS.md` and `docs/DRY_RUN_MATRIX.md` (both are referenced by this plan).
   3. [x] Create `TASKS.md` entries for every ID in the Issue Register (local replacement for external tickets).
3. Branching rule for execution:
   1. keep this plan branch for planning/docs maintenance,
   2. execute code changes in dedicated branches per wave or per issue cluster.

## Wave Schedule (Target Dates)

| Wave | Scope | Target Window | Exit Condition |
|---|---|---|---|
| Wave 0 | Setup + tracking artifacts | 2026-02-27 to 2026-02-28 | Tracker artifacts and issue board created |
| Wave 1 | Security + runtime blockers | 2026-02-28 to 2026-03-01 | `SEC-01`, `RUN-01`, `SEC-02`, `CONV-01` closed with tests |
| Wave 2 | Dry-run + quality gates | 2026-03-01 to 2026-03-03 | `SAFE-01`, `QUAL-01`, `QUAL-02` closed |
| Wave 3 | Roadmap closure | 2026-03-03 to 2026-03-05 | `RM-01`..`RM-04` closed or explicitly re-scoped |
| Wave 4 | Autonomous MCP verification | 2026-03-02 to 2026-03-06 | Protocol + live lanes operational |
| Wave 5 | npm/npx infra | 2026-03-06 to 2026-03-07 | Scoped package + release workflows working |
| Wave 6 | Distribution validation | 2026-03-07 to 2026-03-08 | `latest`/`next`/pinned validation complete |

## Issue Execution Tracker (Living)

| ID | Status | Owner | Branch | PR | Test Evidence | Last Update |
|---|---|---|---|---|---|---|
| SEC-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Middleware now rejects unverified JWT identity by default; `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT=true` break-glass override; guardrail tests added | 2026-02-27 |
| RUN-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | `uv run python -c "import main"` + `uv run python -c "import fastmcp_server"`; CI startup smoke job added | 2026-02-27 |
| SEC-02 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Shared secure atomic JSON writer added; credential and session persistence wired to strict permissions; security I/O tests added | 2026-02-27 |
| SAFE-01 | In Progress | Codex | codex/run-01-fastmcp-import-smoke | - | `gcalendar`, `gdrive/files.py`, and `gdrive/permissions.py` mutators now default to `dry_run=True` with deterministic preview responses; runtime dry-run tests expanded | 2026-02-27 |
| QUAL-01 | In Progress | Codex | codex/run-01-fastmcp-import-smoke | - | Startup smoke checks and decorator-order static check now block CI; incremental type-check promotion remains | 2026-02-27 |
| QUAL-02 | Not Started | Codex | - | - | - | 2026-02-27 |
| CONV-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Decorator order normalized in `gmail/threads.py`; `scripts/check_tool_decorators.py` + unit tests added; checker wired into CI | 2026-02-27 |
| DOC-01 | In Progress | Codex | codex/run-01-fastmcp-import-smoke | - | `docs/STATUS.md`, `docs/DRY_RUN_MATRIX.md` added and synchronized with latest wave status | 2026-02-27 |
| OPC-01 | Not Started | Codex | - | - | - | 2026-02-27 |
| RM-01 | Not Started | Codex | - | - | - | 2026-02-27 |
| RM-02 | Not Started | Codex | - | - | - | 2026-02-27 |
| RM-03 | Not Started | Codex | - | - | - | 2026-02-27 |
| RM-04 | Not Started | Codex | - | - | - | 2026-02-27 |
| DIST-00 | Not Started | Codex | - | - | - | 2026-02-27 |
| DIST-01 | Not Started | Codex | - | - | - | 2026-02-27 |
| DIST-02 | Not Started | Codex | - | - | - | 2026-02-27 |
| DIST-03 | Not Started | Codex | - | - | - | 2026-02-27 |
| DIST-04 | Not Started | Codex | - | - | - | 2026-02-27 |

## Summary
This plan follows the Codex ExecPlan model and is scoped to **actionable current issues**, sequenced in **risk-first waves**, with a **full MCP harness + live smoke testing** strategy using `david@helmus.me` in **full-write mode**.

The plan is **decision-complete** for:
1. dry-run rollout across mutating tools (inventory + contract + migration waves),
2. runtime/security hardening,
3. canonical distribution path via npm/npx with explicit scope alignment.

The plan resolves:
1. Security and runtime blockers.
2. Safety and quality gate gaps.
3. Open roadmap/spec items.
4. The core gap: enabling autonomous, repeatable MCP verification (not just unit tests).

## Goals
1. Eliminate current critical security/runtime risks.
2. Enforce mutation safety and stronger CI guarantees.
3. Close open roadmap items (Markdown/docs feature stream).
4. Give the agent a deterministic way to test MCP protocol + live feature behavior end-to-end.
5. Normalize planning docs into one canonical status source.

## Non-Goals
1. Re-opening archived historical work that is already closed and non-impacting.
2. Major auth architecture rewrite beyond what is required to close current actionable risk.
3. Visual pixel-perfect UI automation as a merge blocker (optional diagnostic only).

## Baseline (Current Reality to Plan Against)
1. Lint: `ruff check` passes.
2. Formatter is enforced in CI with `--check`, and local verification is now green.
3. Tests: `pytest` passes (486 tests), coverage ~45%.
4. Runtime regression in `fastmcp_server.py` import path has been fixed in `RUN-01`.
5. `SEC-01` implemented: unverified JWT identity extraction is denied by default; break-glass override is explicit and logged.
6. `SEC-02` implemented: credential and session JSON persistence now use centralized secure atomic writes with restrictive permissions.
7. Planning/status docs are internally inconsistent and stale in places.
8. Distribution packaging is not yet implemented (`package.json` absent) and package naming needs to align with scoped target.

## Issue Register and Mitigation Strategy

| ID | Severity | Issue | Mitigation Strategy | Primary Files |
|---|---|---|---|---|
| SEC-01 | P0 | Auth trust boundary (unverified JWT identity path) | Allow identity only from verified token/provider paths; reject unsigned JWT identity claims by default; add break-glass env flag off by default | `auth/middleware/auth_info.py`, `auth/oauth21_session_store.py`, `auth/service_decorator.py`, `core/server.py` |
| RUN-01 | P1 | Cloud entrypoint import regression | Replace stale import and add import smoke tests in CI | `fastmcp_server.py`, `.github/workflows/ci.yml` |
| SEC-02 | P1 | Credential files written without strict permission guarantees | Centralize atomic secure JSON write with strict file/dir modes and apply to credential/session persistence | `auth/credential_types/store.py`, `auth/oauth21_session_store.py`, new `auth/security_io.py` |
| SAFE-01 | P1 | Mutating tools not dry-run-by-default | Roll out `dry_run: bool = True` via explicit mutator inventory, response contract, and phased compatibility plan | tool modules across `gcalendar`, `gdrive`, `gdocs`, `gsheets`, `gmail`, `gtasks`, `gforms`, `gslides`, `gchat`; new `docs/DRY_RUN_MATRIX.md` |
| QUAL-01 | P2 | CI quality gates still allow critical blind spots | Keep formatter gate, but add blocking startup smoke for both entrypoints, plus incremental blocking type gate and static compliance checks | `.github/workflows/ci.yml`, new `pyrightconfig.json`, new `scripts/check_*` |
| QUAL-02 | P2 | Low coverage in high-risk runtime paths | Add targeted tests for auth/session/runtime + live MCP scenarios | `tests/unit/auth/*`, `tests/integration/*`, new `tests/live_mcp/*`, new `tests/mcp_protocol/*` |
| CONV-01 | P3 | Decorator order inconsistency | Normalize decorator order in outliers and add static check | `gmail/threads.py`, new `scripts/check_tool_decorators.py` |
| DOC-01 | P3 | Planning/roadmap status drift | Introduce canonical status doc and mark stale/archived docs clearly | `ROADMAP.md`, `TESTING_PLAN_MARKDOWN.md`, `TEST_RESULTS.md`, `ISSUE_REPORT.md`, new `docs/STATUS.md` |
| OPC-01 | P2 | No automated OpenCode headless control plane for end-to-end MCP validation | Add `opencode serve` orchestration + SDK smoke lane with auth hardening and deterministic teardown | new `scripts/opencode_*`, new `tests/opencode/*`, CI workflow updates |
| RM-01 | P2 | Code block visual parity still open | Implement paragraph shading/border + language label handling for fenced code blocks | `gdocs/markdown_parser.py`, tests |
| RM-02 | P2 | Table reliability still tracked as open in roadmap/testing docs | Add regression e2e and close with proof; if failing, apply pre-defined fallback path via table manager flow | `gdocs/markdown_parser.py`, integration/live tests, docs |
| RM-03 | P3 | Extra empty bullet after task lists | Add explicit post-task-list bullet reset behavior and regression tests | `gdocs/markdown_parser.py`, tests |
| RM-04 | P3 | Images are implemented but insufficiently verified | Add deterministic tests for image insertion paths and structure assertions | `gdocs/markdown_parser.py`, integration/live tests |
| DIST-00 | P1 | npm package naming/scope mismatch across docs/plans | Standardize to `@skeptomenos/gws-mcp-advanced` for all npx examples and release automation | `PLAN.md`, wrapper `AGENTS.md`, `README.md`, npm package metadata |

## Open Roadmap Items Included
1. `specs/FIX_CODE_BLOCKS.md` (Open).
2. `TESTING_PLAN_MARKDOWN.md` open items: table reliability, extra bullet after tasks, image verification.
3. `ROADMAP.md` still reports Markdown feature “In Progress” and needs closure criteria update.
4. Status inconsistencies between testing/results/issue report documents.

## Execution Waves (Risk-First)

## Wave 0: Program Setup and Tracking (Day 0.5)
1. Use this `PLAN.md` as the single canonical execution document and keep it updated per the protocol below.
2. Track issues locally in `TASKS.md` with IDs preserved (`SEC-01`, `RUN-01`, etc.).
3. Add ownership labels: `security`, `runtime`, `safety`, `quality`, `roadmap`, `docs`.
4. Define merge policy: Wave 1 must be complete before Wave 2+ merges.

## Wave 1: Security + Runtime Blockers (Day 1-2)
1. Implement `SEC-01` identity hardening.
2. Implement `RUN-01` cloud entrypoint fix.
3. Implement `SEC-02` secure persistence I/O.
4. Implement `CONV-01` decorator order normalization.
5. Add/expand tests for each change before moving to Wave 2.

## Wave 2: Safety + Quality Gates (Day 3-5)
1. Implement `SAFE-01` dry-run rollout for all mutating tools using Wave 2A (high-risk mutators) then Wave 2B (remaining mutators).
2. Implement `QUAL-01` CI gate tightening (entrypoint smoke + blocking static checks + incremental type gate).
3. Implement `QUAL-02` coverage increases on critical modules.
4. Keep format check in verify mode (`--check`) in both local protocol and CI protocol.

## Wave 3: Roadmap Feature Closure (Day 5-7)
1. Implement `RM-01` code block rendering improvements.
2. Implement `RM-03` extra task-list bullet fix.
3. Execute `RM-02` table reliability closure workflow:
   1. Run deterministic regression suite.
   2. Run live smoke against MCP harness.
   3. If any out-of-bounds persists, apply fallback implementation path (table-manager based insertion).
4. Implement `RM-04` image verification suite.
5. Update roadmap/spec docs with objective pass/fail evidence.

## Wave 4: MCP Autonomous Verification System (Day 2-8, parallelized)
1. Build protocol-level harness tests (local MCP transport/process).
2. Build live smoke suite (real account, full-write, strict cleanup).
3. Build feature verification suite for Markdown and tool behavior.
4. Add OpenCode headless lane using `opencode serve` and SDK client automation.
5. Integrate into a repeatable command matrix so the agent can run it end-to-end.

## Public API / Interface / Type Changes

1. Add `dry_run: bool = True` to mutating MCP tools that currently mutate by default.
2. Standardize mutating tool behavior:
   1. `dry_run=True`: no remote/local mutation; returns planned actions/impact.
   2. `dry_run=False`: executes mutation and returns result summary.
3. Keep backward-compatible return style in Phase 1:
   1. Existing string-returning tools keep returning strings.
   2. Dry-run responses use deterministic prefix `DRY RUN:` plus concise action summary.
   3. No tool should silently mutate when `dry_run` argument is omitted.
4. Add env flag `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT`:
   1. Default: `false`.
   2. Purpose: temporary emergency compatibility only.
   3. Every use logs a high-severity warning.
5. Add live test env controls:
   1. `MCP_LIVE_TESTS=1`
   2. `MCP_TEST_USER_EMAIL=david@helmus.me`
   3. `MCP_TEST_ALLOW_WRITE=1`
   4. `MCP_TEST_PREFIX=codex-it-`
6. Add pytest markers:
   1. `@pytest.mark.mcp_protocol`
   2. `@pytest.mark.live_mcp`
   3. `@pytest.mark.live_write`

## SAFE-01: Mutating Tool Inventory and Rollout Matrix

### Contract (Applies to all mutating tools)
1. Function signature adds `dry_run: bool = True` as the final optional parameter.
2. `dry_run=True` must:
   1. skip API mutation calls and local file writes,
   2. return deterministic preview including target identifiers and planned operation,
   3. never create remote IDs as side effects.
3. `dry_run=False` preserves existing behavior and response structure as much as possible.
4. Destructive operations (`delete`, `remove`, `transfer`, `clear`, `send`) require explicit `dry_run=False`.

### Inventory Matrix (Decision Complete)
| Module | Mutating Tools | Current State | Rollout Wave |
|---|---|---|---|
| `gcalendar/calendar_tools.py` | `create_event`, `modify_event`, `delete_event` | `dry_run=True` default implemented | Wave 2A |
| `gdrive/files.py` | `create_drive_file`, `update_drive_file` | `dry_run=True` default implemented | Wave 2A |
| `gdrive/permissions.py` | `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership` | `dry_run=True` default implemented | Wave 2A |
| `gdrive/sync_tools.py` | `link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs` | No dry-run | Wave 2B |
| `gdrive/sync_tools.py` | `update_google_doc`, `download_google_doc` | Already dry-run | Wave 2A verification only |
| `gdocs/writing.py` | `create_doc`, `modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown` | No dry-run | Wave 2A |
| `gdocs/elements.py` | `insert_doc_elements`, `insert_doc_image` | No dry-run | Wave 2A |
| `gdocs/tables.py` | `create_table_with_data` | No dry-run | Wave 2A |
| `gsheets/sheets_tools.py` | `modify_sheet_values`, `format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, `create_spreadsheet`, `create_sheet` | No dry-run | Wave 2A |
| `gmail/messages.py` | `send_gmail_message`, `draft_gmail_message` | No dry-run | Wave 2A |
| `gmail/labels.py` | `manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels` | No dry-run | Wave 2B |
| `gmail/filters.py` | `create_gmail_filter`, `delete_gmail_filter` | No dry-run | Wave 2B |
| `gtasks/tasks_tools.py` | `create_task_list`, `update_task_list`, `delete_task_list`, `create_task`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks` | No dry-run | Wave 2A |
| `gforms/forms_tools.py` | `create_form`, `set_publish_settings` | No dry-run | Wave 2B |
| `gslides/slides_tools.py` | `create_presentation`, `batch_update_presentation` | No dry-run | Wave 2A |
| `gchat/chat_tools.py` | `send_message` | No dry-run | Wave 2B |

### SAFE-01 Test Matrix
1. Add parameterized tests per module to assert:
   1. default invocation does not call mutating client method,
   2. explicit `dry_run=False` does call mutating client method,
   3. preview output includes operation and target.
2. Add one cross-service integration test that executes a representative dry-run call for each service.
3. Add static guard script (`scripts/check_dry_run_defaults.py`) that fails CI if mutating tools are missing `dry_run: bool = True`.

## MCP Self-Testing Enablement (Decision-Complete Design)

## Harness Architecture
1. Use `fastmcp.Client` as the MCP client implementation for tests.
2. Primary transport for automation: stdio against `main.py`.
3. Config format: MCP config dict with `mcpServers` + `command/args/env/cwd`.
4. Keep all live-created artifacts prefixed with `MCP_TEST_PREFIX`.
5. Persist created artifact IDs during tests and always run cleanup in `finally`.
6. Add a second transport/control plane via OpenCode server API (`opencode serve`) for external orchestration parity.

## Test Lanes
1. Lane A: Protocol lane (`tests/mcp_protocol/`).
2. Lane B: Live smoke lane (`tests/live_mcp/`).
3. Lane C: Feature lane (`tests/live_mcp/test_markdown_features.py` + integration helpers).
4. Lane D: Optional visual diagnostics (non-blocking, Playwright/manual).
5. Lane E: OpenCode headless SDK lane (`tests/opencode/`) using spawned `opencode serve`.

## Required New Test Assets
1. `tests/mcp_protocol/test_stdio_handshake.py`
2. `tests/mcp_protocol/test_tool_registry_contract.py`
3. `tests/live_mcp/conftest.py`
4. `tests/live_mcp/helpers.py` (artifact registry + cleanup)
5. `tests/live_mcp/test_live_smoke.py`
6. `tests/live_mcp/test_markdown_features.py`
7. `scripts/mcp_live_cleanup.py`
8. `docs/MCP_AUTONOMOUS_TESTING.md`
9. `tests/opencode/test_opencode_serve_smoke.py`
10. `tests/opencode/test_opencode_sdk_session_flow.py`
11. `scripts/opencode_serve_smoke.sh`
12. `scripts/opencode_sdk_smoke.mjs`

## Live Test Safety Model (Full Write, as selected)
1. Only create/update/delete artifacts with enforced prefix match.
2. Abort test if target ID/name does not match owned-test artifact policy.
3. Mandatory cleanup pass after each test session.
4. Nightly cleanup script for orphan artifacts older than retention window.
5. OpenCode server auth must be enabled for non-localhost exposure (`OPENCODE_SERVER_PASSWORD` required outside local loopback smoke).

## Test Cases and Scenarios

## Security and Runtime
1. Unsigned/forged JWT cannot set authenticated identity.
2. Verified provider token path still works for legitimate user.
3. Cross-user credential access denied on session/token mismatch.
4. `import fastmcp_server` passes.
5. `import main` passes.

## Dry-Run Safety
1. Each mutating tool returns non-mutating preview when `dry_run=True`.
2. Each mutating tool performs actual mutation only when `dry_run=False`.
3. Deletion/move/share/send operations are safe by default.
4. Existing read-only tools remain unchanged.
5. CI static check fails if any mutating tool lacks `dry_run: bool = True`.

## Markdown/Roadmap
1. Code blocks include expected style fields (font, shading, border).
2. Table creation/population succeeds in kitchen-sink and focused table docs.
3. No extra bullet after task list transitions.
4. Images insert and appear as expected in structure/content checks.
5. Known fixed items (style bleed, list nesting, blockquotes) remain non-regressed.

## Protocol and Live MCP
1. MCP client can initialize, ping, list tools, and call representative tools.
2. Live write smoke test creates and cleans prefixed artifacts.
3. End-to-end Markdown scenario passes through MCP tool invocation (not direct function call).
4. OpenCode SDK can create a session against spawned `opencode serve`, execute a prompt, and teardown cleanly.

## CI and Validation Strategy

## Local Verification Protocol
1. `uv run ruff check .`
2. `uv run ruff format --check .`
3. `uv run pytest`
4. `uv run pytest -m mcp_protocol tests/mcp_protocol`
5. `uv run pytest -m "live_mcp and live_write" tests/live_mcp` (when env enabled)

## CI Pipeline Changes
1. Keep existing lint/test jobs.
2. Keep formatter in check mode only (`uv run ruff format --check .`).
3. Add blocking startup smoke job for both entrypoints:
   1. `python -c "import main"`
   2. `python -c "import fastmcp_server"`
4. Add blocking protocol lane in CI (no live credentials required).
5. Add blocking static safety checks:
   1. `scripts/check_dry_run_defaults.py`
   2. `scripts/check_tool_decorators.py`
6. Keep live lane opt-in/manual or scheduled with secure secrets.
7. Keep type-check job non-blocking initially, then promote to blocking after error budget reaches zero.
8. Add non-blocking OpenCode lane initially (nightly/manual), then promote to blocking after 7 consecutive green runs.

## Documentation and Roadmap Reconciliation Plan
1. Add `docs/STATUS.md` as canonical current state.
2. Update `ROADMAP.md` with explicit closure criteria and current phase.
3. Update `TESTING_PLAN_MARKDOWN.md` with current test counts and true open items.
4. Mark `TEST_RESULTS.md` and stale historical plans as archived snapshots.
5. Add a short “source of truth” banner to historical files in `ralph-wiggum/_archive/`.

## Rollout and Risk Mitigation
1. Rollout by wave; do not mix security and feature closure in one large merge.
2. Merge Wave 1 behind targeted tests first.
3. For potentially breaking behavior (`dry_run` defaults), ship with clear release notes and migration examples.
4. Keep emergency compatibility switch for JWT path but disabled by default.
5. Use fast rollback strategy: per-wave branch isolation and revertable commits.

## Acceptance Criteria (Definition of Done)
1. All Wave 1 issues (`SEC-01`, `RUN-01`, `SEC-02`, `CONV-01`) are closed with tests.
2. All tools in the SAFE-01 inventory matrix implement `dry_run: bool = True` and pass module-level dry-run tests.
3. CI no longer permits format regressions, missing dry-run defaults, or silent startup breakages.
4. MCP protocol harness and live smoke suite are operational and repeatable by the agent.
5. Open roadmap/spec items (`RM-01`..`RM-04`) are either closed with proof or explicitly re-scoped with dated rationale.
6. Canonical status docs reflect current reality without contradictions.
7. `DIST-00` is closed: docs, release workflows, and examples all use `@skeptomenos/gws-mcp-advanced`.
8. OpenCode headless SDK lane (`OPC-01`) is operational with spawn, health check, prompt execution, and deterministic teardown.

## Assumptions and Defaults (Locked)
1. Scope: actionable current issues only.
2. Sequence: risk-first waves.
3. Live test principal: `david@helmus.me`.
4. Live test mutation profile: full write with strict prefix + cleanup safeguards.
5. MCP autonomous verification is required, not optional.
6. OpenCode manual testing remains supported, but autonomous harness becomes primary verification path.

## npm/npx Distribution Extension (Added 2026-02-27)

### Objective
Enable stable MCP distribution via `npx` for consumers while preserving a fast local-development execution path for repository contributors.

### Distribution Strategy
1. Stable channel: `npx -y @skeptomenos/gws-mcp-advanced` using npm `latest`.
2. Prerelease channel: `npx -y @skeptomenos/gws-mcp-advanced@next` using npm `next`.
3. Local development channel: `uv run --project <repo-path> gws-mcp-advanced --transport stdio`.
4. Deterministic release pinning: production docs use explicit version examples (`@x.y.z`) for rollback and reproducibility.
5. Version coupling: npm wrapper version `x.y.z` launches Python package `gws-mcp-advanced==x.y.z` by default.

### Packaging Design (Thin Launcher + uvx)
1. Add npm package `@skeptomenos/gws-mcp-advanced` with a single `bin` entry.
2. Launcher implementation:
   1. Resolve target Python spec from `GWS_MCP_PYPI_SPEC` or default to `gws-mcp-advanced==<npm-version>`.
   2. Execute `uvx --from <spec> gws-mcp-advanced ...args`.
   3. Pass through stdio cleanly with no wrapper-side JSON/log pollution.
3. Launcher safety behavior:
   1. If `uvx` is unavailable, fail with actionable install instructions.
   2. Exit non-zero on process spawn or transport errors.
   3. Do not handle secrets; only forward env provided by MCP client config.
4. MCP config examples to document:
   1. Stable install path via `npx`.
   2. Local dev path via `uv run --project`.
   3. Optional pinned package version for deterministic environments.
   4. Scoped package path is canonical (`@skeptomenos/gws-mcp-advanced`) for all examples.

### Release Pipeline
1. Publish order is strict:
   1. Publish Python package to PyPI first.
   2. Publish npm wrapper second.
2. npm publish guard:
   1. Block publish when matching PyPI version is not yet available.
   2. Block `latest` tag promotion when smoke tests fail.
3. Trust and provenance:
   1. Use GitHub Actions OIDC trusted publishing for PyPI and npm.
   2. Enable npm provenance metadata on publish.
4. Tag policy:
   1. `latest` for production-ready versions.
   2. `next` for prerelease validation.
5. Rollback policy:
   1. Rapid npm dist-tag rollback (`latest` back to previous good version).
   2. Keep previous Python versions installable for rollback compatibility.

### Additional Issue Register Entries (Distribution)

| ID | Severity | Issue | Mitigation Strategy | Primary Files |
|---|---|---|---|---|
| DIST-00 | P1 | Package scope/name mismatch across planning/docs/release artifacts | Canonicalize all references to `@skeptomenos/gws-mcp-advanced` and enforce in CI checks | `PLAN.md`, `README.md`, npm metadata, release workflows |
| DIST-01 | P1 | Wrapper/Python version drift | Enforce publish order and version-coupling checks in release CI | `.github/workflows/*`, npm package metadata |
| DIST-02 | P1 | Missing `uvx` on consumer machine causes hard failure | Add launcher preflight and clear remediation output | npm launcher script |
| DIST-03 | P2 | npx non-determinism without pinned version usage | Document pinned installs and keep `latest` strict to vetted builds | `README.md`, release docs |
| DIST-04 | P2 | Supply-chain integrity risk | OIDC trusted publishing + provenance + minimal launcher surface | publish workflows |

### Execution Waves (Distribution Add-On)

#### Wave 5: Distribution Infrastructure (Day 8-9)
1. Create npm wrapper package and launcher script.
2. Add release workflows for Python + npm with publish ordering guarantees.
3. Add release smoke checks for both `latest` and `next`.
4. Document stable vs local-dev MCP configuration in `README.md` with scoped package examples only.

#### Wave 6: Distribution Validation and Adoption (Day 9-10)
1. Validate clean-machine install path using `npx`.
2. Validate upgrade/downgrade behavior via dist-tags.
3. Validate local developer path remains faster and unaffected.
4. Add support notes and troubleshooting for `uvx` prerequisites.

### MCP Test Matrix Additions (Distribution)

| Lane | Transport | Package Source | Purpose |
|---|---|---|---|
| DIST-A | `stdio` via `uv run --project <repo-path>` | local project path | Verify local dev loop and immediate code changes |
| DIST-B | `stdio` via `npx -y @skeptomenos/gws-mcp-advanced` | npm `latest` | Verify production install path |
| DIST-C | `stdio` via `npx -y @skeptomenos/gws-mcp-advanced@next` | npm `next` | Verify prerelease channel before promotion |
| DIST-D | `stdio` via `npx -y @skeptomenos/gws-mcp-advanced@x.y.z` | pinned version | Verify deterministic versioned deployments |

### Concrete Distribution Test Cases
1. `list_tools` parity between local (`uv run --project`) and stable (`npx latest`) channels.
2. CLI arg passthrough (`--transport`, `--tools`, `--tool-tier`) via npm launcher.
3. Environment passthrough for auth variables from MCP client config.
4. Failure-path test when `uvx` is missing.
5. Version-coupling test that npm `x.y.z` resolves and launches Python `x.y.z`.
6. End-to-end smoke: initialize client, list tools, call representative read tool, clean exit.
7. Scope integrity test: wrapper install/launch only through `@skeptomenos/gws-mcp-advanced`.

### Acceptance Gates (Expanded)
1. Existing gates remain mandatory:
   1. `uv run ruff check .`
   2. `uv run ruff format --check .`
   3. `uv run pytest`
2. New distribution gates:
   1. Launcher smoke (`npx` path) passes in CI.
   2. Local dev smoke (`uv run --project` path) passes in CI.
   3. Publish workflow blocks npm release on failed smoke or missing matching PyPI version.
   4. Publish workflow blocks release if package scope/name differs from `@skeptomenos/gws-mcp-advanced`.
3. Documentation gate:
   1. `README.md` contains both stable and local-dev MCP configuration examples.
   2. Stable examples use `@skeptomenos/gws-mcp-advanced` only.
   3. Release notes include pinned install example and rollback note.

## Update Protocol (Required)
1. On every issue transition (`Not Started` -> `In Progress` -> `Blocked`/`Done`), update the row in `Issue Execution Tracker (Living)`.
2. On every implementation session end:
   1. update `Last Updated (UTC)` in `Living Document Controls`,
   2. append one entry to `Execution Changelog`,
   3. update `Current Focus` in `Session Handoff`.
3. On every PR:
   1. add PR number/link in the tracker row,
   2. add verification commands run and pass/fail summary in `Verification Evidence`,
   3. if scope changed, update the relevant wave section and acceptance criteria.
4. On any decision change:
   1. add a row to `Decision Log`,
   2. include date, decision, rationale, and affected IDs.
5. If plan and code diverge:
   1. update plan first, then continue implementation,
   2. do not leave stale status in this file across sessions.

## Verification Evidence (Living)

| Date (UTC) | Scope | Commands | Result | Notes |
|---|---|---|---|---|
| 2026-02-27 | Baseline | `uv run ruff check .` | Pass | - |
| 2026-02-27 | Baseline | `uv run ruff format --check .` | Fail | `gcalendar/calendar_tools.py` requires formatting |
| 2026-02-27 | Baseline | `uv run pytest -q` | Pass | 459 passed |
| 2026-02-27 | Wave 0 Preflight | `uv run ruff format gcalendar/calendar_tools.py` | Pass | Formatting drift corrected |
| 2026-02-27 | Wave 0 Preflight | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Local verification protocol fully green |
| 2026-02-27 | RUN-01 | `uv run python -c "import main"` | Pass | Entrypoint import smoke |
| 2026-02-27 | RUN-01 | `uv run python -c "import fastmcp_server"` | Pass | Cloud entrypoint import smoke |
| 2026-02-27 | RUN-01 | `uv run ruff check . && uv run ruff format . && uv run pytest -q` | Pass | Full verification protocol after RUN-01 changes |
| 2026-02-27 | SEC-01 | `uv run pytest -q tests/unit/auth/test_unverified_jwt_identity_guardrails.py` | Pass | 5 guardrail tests passing |
| 2026-02-27 | SEC-01 | `uv run ruff check . && uv run ruff format . && uv run pytest -q` | Pass | Full verification protocol after SEC-01 changes (464 passed) |
| 2026-02-27 | SEC-02 | `uv run pytest -q tests/unit/auth/test_security_io.py tests/unit/auth/test_credential_store.py tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_session_store.py` | Pass | 47 targeted auth persistence tests passing |
| 2026-02-27 | SEC-02 | `uv run ruff check . && uv run ruff format . && uv run pytest -q` | Pass | Full verification protocol after SEC-02 changes (468 passed) |
| 2026-02-27 | CONV-01 | `uv run python scripts/check_tool_decorators.py && uv run pytest -q tests/unit/core/test_tool_decorator_checker.py` | Pass | Decorator order checker and tests passing |
| 2026-02-27 | CONV-01 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after CONV-01 changes (470 passed) |
| 2026-02-27 | SAFE-01 (`gcalendar`) | `uv run pytest -q tests/unit/tools/test_calendar_tools.py` | Pass | Added dry-run contract coverage for calendar mutators (57 passed) |
| 2026-02-27 | SAFE-01 (`gcalendar`) | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after calendar dry-run rollout (472 passed) |
| 2026-02-27 | SAFE-01 (`gdrive/files.py`) | `uv run pytest -q tests/unit/tools/test_drive_tools.py` | Pass | Added runtime tests for dry-run skip behavior and explicit `dry_run=False` mutation path (39 passed) |
| 2026-02-27 | SAFE-01 (`gdrive/files.py`) | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after Drive file dry-run rollout (476 passed) |
| 2026-02-27 | SAFE-01 (`gdrive/permissions.py`) | `uv run pytest -q tests/unit/tools/test_drive_tools.py` | Pass | Added runtime tests for all permission mutators covering default dry-run skip and explicit `dry_run=False` mutation paths (49 passed) |
| 2026-02-27 | SAFE-01 (`gdrive/permissions.py`) | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after Drive permission dry-run rollout (486 passed) |
| 2026-02-27 | OPC-01 discovery | `opencode --version && opencode serve --help` | Pass | Confirmed local OpenCode server capability (`1.2.10`) and serve command availability |
| 2026-02-27 | OPC-01 discovery | `opencode serve --hostname 127.0.0.1 --port 42877 --print-logs` | Pass | Server started and accepted local binding; warning confirms password should be set for non-local exposure |

## Decision Log (Living)

| Date (UTC) | Decision | Rationale | Affected IDs |
|---|---|---|---|
| 2026-02-27 | Adopt scoped npm package `@skeptomenos/gws-mcp-advanced` | Prevent naming drift and keep distribution canonical | DIST-00..DIST-04 |
| 2026-02-27 | Keep `PLAN.md` as canonical living execution plan | Reduce planning drift and duplicate sources | DOC-01 |
| 2026-02-27 | Track dry-run rollout progress in dedicated matrix doc | Improve execution transparency for `SAFE-01` and avoid checklist drift | SAFE-01, DOC-01 |
| 2026-02-27 | Enforce default-deny for unverified JWT identity extraction | Remove unsigned-token identity trust by default while retaining emergency compatibility path | SEC-01 |
| 2026-02-27 | Centralize auth persistence writes in shared security I/O module | Eliminate duplicated write logic and enforce consistent secure file/dir modes | SEC-02 |
| 2026-02-27 | Enforce decorator ordering with static CI guard | Prevent divergence in tool safety/readability convention over time | CONV-01, QUAL-01 |
| 2026-02-27 | Add OpenCode `serve` + SDK as secondary autonomous test lane | Provides realistic external control-plane validation beyond in-process MCP harness | OPC-01, QUAL-02 |

## Session Handoff (Living)
1. Current Focus: `Wave 2 SAFE-01 rollout (continue Wave 2A) + DOC-01 reconciliation`
2. Next 3 Actions:
   1. keep `TASKS.md` statuses synchronized with active implementation changes,
   2. continue `SAFE-01` Wave 2A dry-run defaults in high-risk mutating tools (`gdocs/writing.py` next),
   3. implement `OPC-01` skeleton (`scripts/opencode_serve_smoke.sh` + minimal SDK smoke runner) before wiring CI lane.
3. Active Blockers:
   1. none recorded.

## Execution Changelog (Living)
1. 2026-02-27: Promoted `PLAN.md` to canonical living execution doc; added readiness verdict, wave schedule, issue tracker, update protocol, evidence log, decision log, and session handoff.
2. 2026-02-27: Completed Wave 0 preflight tasks for formatting and living-doc scaffolding; added `docs/STATUS.md` and `docs/DRY_RUN_MATRIX.md`; initialized tracker owners and set `DOC-01` to `In Progress`.
3. 2026-02-27: Replaced external ticket dependency with local tracker `TASKS.md` and aligned Wave 0 tracking workflow accordingly.
4. 2026-02-27: Closed `RUN-01` by fixing `fastmcp_server.py` docs import path and adding blocking CI startup smoke checks for `main` and `fastmcp_server`.
5. 2026-02-27: Closed `SEC-01` by default-denying unverified JWT identity extraction in auth/session middleware, introducing `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT` break-glass behavior, and adding guardrail tests.
6. 2026-02-27: Closed `SEC-02` by introducing `auth/security_io.py` and migrating credential/session JSON persistence to secure atomic writes with explicit permission tests.
7. 2026-02-27: Closed `CONV-01` by normalizing decorator order in `gmail/threads.py`, adding `scripts/check_tool_decorators.py` with unit tests, and wiring the check into CI lint gates.
8. 2026-02-27: Started `SAFE-01` Wave 2A by implementing `dry_run=True` defaults and deterministic dry-run previews for `gcalendar` mutators (`create_event`, `modify_event`, `delete_event`) with calendar dry-run contract tests.
9. 2026-02-27: Continued `SAFE-01` Wave 2A by implementing `dry_run=True` defaults and deterministic dry-run previews for `gdrive/files.py` mutators (`create_drive_file`, `update_drive_file`) with runtime tests validating dry-run skip and explicit mutation behavior.
10. 2026-02-27: Added `OPC-01` planning track for OpenCode headless server + SDK automation; verified local `opencode serve` startup and documented auth mitigation requirements.
11. 2026-02-27: Continued `SAFE-01` Wave 2A by implementing `dry_run=True` defaults and deterministic dry-run previews for `gdrive/permissions.py` mutators with runtime tests covering `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, and `transfer_drive_ownership`.
