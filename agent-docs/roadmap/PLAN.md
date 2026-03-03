# ExecPlan: GWS MCP Hardening, Roadmap Closure, and Autonomous MCP Verification

## Living Document Controls
1. Status: `IN_IMPLEMENTATION`
2. Last Updated (UTC): `2026-03-03T10:40:00Z`
3. Canonical Path: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`
4. Active Branch: `main`
5. Local Task Board: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/TASKS.md`
6. Overall Progress: `87.5%` (`21/24` issues `Done`; `0/24` `In Progress`; `3/24` `Not Started`)
7. Update Cadence:
   1. update this file after every completed issue ID (`SEC-*`, `SAFE-*`, `DIST-*`, etc.),
   2. update this file at the end of each implementation session,
   3. update this file before opening or merging any PR,
   4. during active OpenCode/manual test loops, update this file immediately after each attempt result (`PASS`/`FAIL`/`BLOCKED`) and each local verification rerun.
8. Source-of-Truth Rule: if another planning file conflicts with this document, this document wins until reconciliation.

## Active Hotfix Track
1. Authentication stabilization is now tracked in a dedicated living plan:
   `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/AUTH_STABILIZATION_PLAN.md`
2. Issue ID for this track: `AUTH-01` (P0, done).
3. Single-MCP multi-client tenant support is tracked as `AUTH-02` (P0, done).

## Enterprise/Private Single-MCP Multi-Client Authentication (Primary Strategy)
1. Status: `DONE`
2. Priority: `P0` (required for enterprise + private coexistence in one MCP entry)
3. Objective:
   1. keep one MCP server config in OpenCode/Claude Code,
   2. allow account/domain-specific OAuth client routing inside that one MCP process,
   3. isolate credentials and sessions by `(oauth_client, user_email)`.
4. Strategy baseline:
   1. adopt `gogcli`-style client registry + deterministic selection precedence,
   2. introduce client-aware credential/session persistence,
   3. add manual callback completion path (`start` + `complete`) for MCP-hosted lifecycles.
5. Setup contract (selected):
   1. if `auth_clients.json` is missing, MCP auto-creates a skeleton and returns actionable setup instructions,
   2. OAuth client secrets are added via explicit setup/import flow (not authored free-text by LLM),
   3. selection mode is `mapped_only` with hard-fail mismatch behavior and no fallback to other clients,
   4. explicit client override is internal/admin-only (not exposed on normal user tool calls),
   5. `complete_google_auth` uses hybrid input with `callback_url` as primary and optional `code/state` fallback.
6. Reference analysis:
   1. `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/AUTHENTICATION_GOGCLI_REVIEW.md`

### Temporary Fallback (Not Target End-State)
1. Dual-MCP-entry tenant split remains a contingency workaround for immediate operations.
2. It is explicitly not the target architecture and should be retired after `AUTH-02` closes.

## Implementation Readiness Verdict
1. Verdict: `YES`, preflight is complete and implementation is active.
2. Immediate preflight tasks (execute first):
   1. [x] Reformat `gcalendar/calendar_tools.py` so local quality protocol is green (`uv run ruff format --check .`).
   2. [x] Create `agent-docs/roadmap/STATUS.md` and `agent-docs/roadmap/DRY_RUN_MATRIX.md` (both are referenced by this plan).
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
| Wave 5 | Distribution infra | 2026-03-06 to 2026-03-07 | PyPI release workflow + uvx distribution path working |
| Wave 6 | Distribution validation | 2026-03-07 to 2026-03-08 | uvx stable/pinned validation complete |

## Issue Execution Tracker (Living)

| ID | Status | Owner | Branch | PR | Test Evidence | Last Update |
|---|---|---|---|---|---|---|
| AUTH-01 | Done | Codex | main | - | WS-06.6 is now closed in OpenCode host: OP-74/OP-76 PASS with persistence proof. AUTH-R2 fallback is validated end-to-end in runtime. | 2026-03-03 |
| AUTH-02 | Done | Codex | main | - | WS-07 runtime closeout complete: one MCP entry routed private+enterprise tenants to distinct OAuth clients, mismatch hard-fail verified, and protected tool retries succeeded without re-auth prompts. | 2026-03-03 |
| SEC-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Middleware now rejects unverified JWT identity by default; `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT=true` break-glass override; guardrail tests added | 2026-02-27 |
| RUN-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | `uv run python -c "import main"` + `uv run python -c "import fastmcp_server"`; CI startup smoke job added | 2026-02-27 |
| SEC-02 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Shared secure atomic JSON writer added; credential and session persistence wired to strict permissions; security I/O tests added | 2026-02-27 |
| SAFE-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Full SAFE-01 mutator rollout is implemented and closed: runtime dry-run harness coverage now includes `gcalendar` mutators, `gmail/messages`, and `gdrive/sync_tools` verified-existing mutators; static checker and full suite are green (`576 passed`) | 2026-02-28 |
| QUAL-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Incremental type-check promotion completed: source-scoped `pyrightconfig.json` added, `pyright` promoted to blocking CI gate, and baseline reduced to zero errors | 2026-02-28 |
| QUAL-02 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | OpenCode manual matrix is complete (`81 PASS`, `0 FAIL`, `1 BLOCKED`, `0 NOT RUN`, `13 defects fixed`). `OP-70` kitchen-sink gate is PASS (Attempt 5), Chat validation rows (`OP-21/22`, `EX-06`) are PASS, and `OP-06` (PSE search env) remains roadmap-deferred by product decision. | 2026-03-02 |
| CONV-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Decorator order normalized in `gmail/threads.py`; `scripts/check_tool_decorators.py` + unit tests added; checker wired into CI | 2026-02-27 |
| DOC-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Reconciled `ROADMAP.md` and `TESTING_PLAN_MARKDOWN.md` to current execution truth and marked `TEST_RESULTS.md`/`ISSUE_REPORT.md` as archived snapshots. | 2026-03-01 |
| OPC-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Real OpenCode lifecycle smoke is operational (`serve` spawn -> `/global/health` -> attached prompt -> deterministic teardown) via `scripts/opencode_*` and pytest wrappers (`2 passed, 1 skipped`; live lane `2 passed`) | 2026-02-28 |
| RM-01 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Implemented code block visual parity in parser: paragraph shading + 4-side borders + fenced language label injection/styling; added parser unit + integration coverage; OpenCode visual regression `OP-68` is PASS. | 2026-03-01 |
| RM-02 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Markdown table flow closure is complete with deterministic integration coverage (preceding-content + multi-table order + fail-fast incomplete population) and manual matrix confirmation. | 2026-03-01 |
| RM-03 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | List bullet range now excludes trailing list-closing newline to prevent empty post-list bullet artifacts; parser regressions added and full verification green (`590 passed`, `3 skipped`); OpenCode live regression `OP-67` PASS confirms no extra empty bullet between task list and following heading/paragraph | 2026-03-01 |
| RM-04 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | OpenCode `OP-69` run 4 is PASS and DEF-012 is fixed. Follow-on OP-70 kitchen-sink gate is PASS after DEF-013 nuance fixes, confirming end-to-end markdown rendering stability on current HEAD. | 2026-03-02 |
| RM-05 | Not Started | Codex | codex/run-01-fastmcp-import-smoke | - | Future extension: native Docs checklist bullets for markdown task lists via `BULLET_CHECKBOX`, with explicit Unicode fallback mode to preserve deterministic behavior. | 2026-03-02 |
| RM-06 | Not Started | Codex | codex/run-01-fastmcp-import-smoke | - | Future extension: markdown mention-to-chip support using Docs `InsertPersonRequest` with graceful fallback for unresolved mentions. | 2026-03-02 |
| RM-07 | Not Started | Codex | codex/run-01-fastmcp-import-smoke | - | Future extension: evaluate/add Google Workspace Add-ons path for third-party smart chips (`workspace.linkpreview` / `workspace.linkcreate`) where Docs API direct writes are not available. | 2026-03-02 |
| DIST-00 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Canonical package identity is standardized (`google-workspace-mcp-advanced`) across npm metadata/docs, and distribution guard checks are enforced in CI + release workflows. | 2026-03-01 |
| DIST-01 | Done | Codex | main | - | PyPI release workflow is operational and verified on current `main`: baseline publish run `22577853068` (`1.0.0`) plus post-fix revalidation run `22618871138` (`1.0.2`) after Pyright gate repair. | 2026-03-03 |
| DIST-02 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | npm launcher preflight/remediation path is implemented and automated smoke tests are in place (`tests/unit/core/test_npm_launcher.py`) and wired into CI. | 2026-03-01 |
| DIST-03 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | Deterministic pinned install and rollback guidance is documented in README + `docs/DISTRIBUTION_RELEASE.md`. | 2026-03-01 |
| DIST-04 | Done | Codex | codex/run-01-fastmcp-import-smoke | - | npm provenance/auth path is de-scoped by product decision because npm/npx distribution is no longer in the release-critical path. | 2026-03-02 |
| DIST-05 | Done | Codex | main | - | Canonical rename/migration hardening is complete: runtime/config defaults use `google-workspace-mcp-advanced`, legacy config path fallback is preserved, migration guide is published, and verification is green (`628 passed`, `3 skipped`). | 2026-03-02 |

## Summary
This plan follows the Codex ExecPlan model and is scoped to **actionable current issues**, sequenced in **risk-first waves**, with a **full MCP harness + live smoke testing** strategy using `david@helmus.me` in **full-write mode**.

The plan is **decision-complete** for:
1. dry-run rollout across mutating tools (inventory + contract + migration waves),
2. runtime/security hardening,
3. canonical distribution path via PyPI + `uvx` with explicit scope alignment,
4. single-MCP multi-client authentication direction for enterprise/private coexistence.

The plan resolves:
1. Security and runtime blockers.
2. Safety and quality gate gaps.
3. Open roadmap/spec items.
4. The core gap: enabling autonomous, repeatable MCP verification (not just unit tests).
5. The architecture gap: one-MCP multi-tenant OAuth client routing and credential isolation.

## Goals
1. Eliminate current critical security/runtime risks.
2. Enforce mutation safety and stronger CI guarantees.
3. Close open roadmap items (Markdown/docs feature stream).
4. Give the agent a deterministic way to test MCP protocol + live feature behavior end-to-end.
5. Normalize planning docs into one canonical status source.
6. Deliver one-MCP multi-client authentication that supports enterprise and private tenants without dual MCP configs.

## Non-Goals
1. Re-opening archived historical work that is already closed and non-impacting.
2. Major auth architecture rewrite beyond what is required to close current actionable risk.
3. Visual pixel-perfect UI automation as a merge blocker (optional diagnostic only; manual kitchen-sink visual acceptance remains mandatory before merge/push).

## Baseline (Current Reality to Plan Against)
1. Lint: `ruff check` passes.
2. Formatter is enforced in CI with `--check`, and local verification is now green.
3. Tests: `pytest` passes (`648 passed`, `3 skipped`), coverage remains in the same approximate range.
4. Runtime regression in `fastmcp_server.py` import path has been fixed in `RUN-01`.
5. `SEC-01` implemented: unverified JWT identity extraction is denied by default; break-glass override is explicit and logged.
6. `SEC-02` implemented: credential and session JSON persistence now use centralized secure atomic writes with restrictive permissions.
7. Planning/status docs are internally inconsistent and stale in places.
8. Distribution packaging is operational for the primary lane: PyPI publish + uvx stable/pinned paths are verified.

## Issue Register and Mitigation Strategy

| ID | Severity | Issue | Mitigation Strategy | Primary Files |
|---|---|---|---|---|
| AUTH-02 | P0 | One MCP process cannot route auth by tenant/account to different OAuth clients | Add named OAuth-client registry + account/domain mapping + client-aware credential/session storage + manual completion tool + compatibility migration; enforce `mapped_only` + hard-fail/no-fallback domain/client policy | `auth/config.py`, `auth/google_auth.py`, `auth/credential_types/store.py`, `auth/oauth21_session_store.py`, `core/server.py`, new `specs/AUTH_MULTI_CLIENT_SINGLE_MCP_SPEC.md` |
| SEC-01 | P0 | Auth trust boundary (unverified JWT identity path) | Allow identity only from verified token/provider paths; reject unsigned JWT identity claims by default; add break-glass env flag off by default | `auth/middleware/auth_info.py`, `auth/oauth21_session_store.py`, `auth/service_decorator.py`, `core/server.py` |
| RUN-01 | P1 | Cloud entrypoint import regression | Replace stale import and add import smoke tests in CI | `fastmcp_server.py`, `.github/workflows/ci.yml` |
| SEC-02 | P1 | Credential files written without strict permission guarantees | Centralize atomic secure JSON write with strict file/dir modes and apply to credential/session persistence | `auth/credential_types/store.py`, `auth/oauth21_session_store.py`, new `auth/security_io.py` |
| SAFE-01 | P1 | Mutating tools not dry-run-by-default | Roll out `dry_run: bool = True` via explicit mutator inventory, response contract, and phased compatibility plan | tool modules across `gcalendar`, `gdrive`, `gdocs`, `gsheets`, `gmail`, `gtasks`, `gforms`, `gslides`, `gchat`; new `agent-docs/roadmap/DRY_RUN_MATRIX.md` |
| QUAL-01 | P2 | CI quality gates still allow critical blind spots | Keep formatter gate, but add blocking startup smoke for both entrypoints, plus incremental blocking type gate and static compliance checks | `.github/workflows/ci.yml`, new `pyrightconfig.json`, new `scripts/check_*` |
| QUAL-02 | P2 | Low coverage in high-risk runtime paths | Add targeted tests for auth/session/runtime + live MCP scenarios | `tests/unit/auth/*`, `tests/integration/*`, new `tests/live_mcp/*`, new `tests/mcp_protocol/*` |
| CONV-01 | P3 | Decorator order inconsistency | Normalize decorator order in outliers and add static check | `gmail/threads.py`, new `scripts/check_tool_decorators.py` |
| DOC-01 | P3 | Planning/roadmap status drift | Introduce canonical status doc and mark stale/archived docs clearly | `ROADMAP.md`, `TESTING_PLAN_MARKDOWN.md`, `TEST_RESULTS.md`, `ISSUE_REPORT.md`, new `agent-docs/roadmap/STATUS.md` |
| OPC-01 | P2 | No automated OpenCode headless control plane for end-to-end MCP validation | Add `opencode serve` orchestration + SDK smoke lane with auth hardening and deterministic teardown | new `scripts/opencode_*`, new `tests/opencode/*`, CI workflow updates |
| RM-01 | P2 | Code block visual parity still open | Implement paragraph shading/border + language label handling for fenced code blocks | `gdocs/markdown_parser.py`, tests |
| RM-02 | P2 | Table reliability still tracked as open in roadmap/testing docs | Add regression e2e and close with proof; if failing, apply pre-defined fallback path via table manager flow | `gdocs/markdown_parser.py`, integration/live tests, docs |
| RM-03 | P3 | Extra empty bullet after task lists | Add explicit post-task-list bullet reset behavior and regression tests | `gdocs/markdown_parser.py`, tests |
| RM-04 | P3 | Images are implemented but insufficiently verified | Add deterministic tests for image insertion paths and structure assertions | `gdocs/markdown_parser.py`, integration/live tests |
| DIST-00 | P1 | Distribution package naming mismatch across docs/plans | Standardize to `google-workspace-mcp-advanced` for PyPI/uvx examples and release automation | `PLAN.md`, `README.md`, `docs/DISTRIBUTION_RELEASE.md`, release metadata |
| DIST-05 | P1 | Legacy runtime/config naming drift (`gws-mcp-advanced`) persists in defaults/docs/log output | Rename canonical runtime/config identifiers to `google-workspace-mcp-advanced`, add startup migration from legacy config dir, and publish explicit migration steps for existing users | `auth/config.py`, `auth/credential_types/store.py`, `core/managers.py`, `core/utils.py`, `README.md`, `docs/setup/*` |

## Open Roadmap Items Included
1. PSE-backed `search_custom` enablement remains intentionally deferred (`OP-06`) by product decision.
2. Smart-chip extension roadmap is now tracked as `RM-05`, `RM-06`, `RM-07` (not started).

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
| `gdrive/sync_tools.py` | `link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs` | `dry_run=True` default implemented across all listed mutators | Wave 2B |
| `gdrive/sync_tools.py` | `update_google_doc`, `download_google_doc` | Already dry-run; now included in static checker scope | Wave 2A verification only |
| `gdocs/writing.py` | `create_doc`, `modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown` | `dry_run=True` default implemented across all listed mutators | Wave 2A |
| `gdocs/elements.py` | `insert_doc_elements`, `insert_doc_image` | `dry_run=True` default implemented (`insert_doc_elements`, `insert_doc_image`) | Wave 2A |
| `gdocs/tables.py` | `create_table_with_data` | `dry_run=True` default implemented (`create_table_with_data`) | Wave 2A |
| `gsheets/sheets_tools.py` | `modify_sheet_values`, `format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, `create_spreadsheet`, `create_sheet` | `dry_run=True` default implemented across all listed mutators | Wave 2A |
| `gmail/messages.py` | `send_gmail_message`, `draft_gmail_message` | `dry_run=True` default implemented | Wave 2A |
| `gmail/labels.py` | `manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels` | `dry_run=True` default implemented (`manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels`) | Wave 2B |
| `gmail/filters.py` | `create_gmail_filter`, `delete_gmail_filter` | `dry_run=True` default implemented (`create_gmail_filter`, `delete_gmail_filter`) | Wave 2B |
| `gtasks/tasks_tools.py` | `create_task_list`, `update_task_list`, `delete_task_list`, `create_task`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks` | `dry_run=True` default implemented across all listed mutators | Wave 2A |
| `gforms/forms_tools.py` | `create_form`, `set_publish_settings` | `dry_run=True` default implemented (`create_form`, `set_publish_settings`) | Wave 2B |
| `gslides/slides_tools.py` | `create_presentation`, `batch_update_presentation` | `dry_run=True` default implemented (`create_presentation`, `batch_update_presentation`) | Wave 2A |
| `gchat/chat_tools.py` | `send_message` | `dry_run=True` default implemented (`send_message`) | Wave 2B |

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
8. `agent-docs/testing/MCP_AUTONOMOUS_TESTING.md`
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
7. Type-check job is now blocking with source-scoped `pyrightconfig.json` (`uv run pyright --project pyrightconfig.json`).
8. Add non-blocking OpenCode lane initially (nightly/manual), then promote to blocking after 7 consecutive green runs.

## Documentation and Roadmap Reconciliation Plan
1. Add `agent-docs/roadmap/STATUS.md` as canonical current state.
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
7. `DIST-00` is closed: docs, release workflows, and examples all use `google-workspace-mcp-advanced`.
8. OpenCode headless SDK lane (`OPC-01`) is operational with spawn, health check, prompt execution, and deterministic teardown.
9. OpenCode `OP-70` (kitchen-sink markdown fixture from `tests/manual/kitchen_sink.md`) is `PASS` on current HEAD with visual checklist evidence before merge/push.

## Assumptions and Defaults (Locked)
1. Scope: actionable current issues only.
2. Sequence: risk-first waves.
3. Live test principal: `david@helmus.me`.
4. Live test mutation profile: full write with strict prefix + cleanup safeguards.
5. MCP autonomous verification is required, not optional.
6. OpenCode manual testing remains supported, but autonomous harness becomes primary verification path.

## Distribution Strategy Update (uvx-first, 2026-03-02)

### Decision
1. Primary distribution is `uvx` from PyPI.
2. npm/npx wrapper lane is de-scoped for now and not required for release readiness.
3. Core delivery is considered complete when PyPI release + uvx startup validation pass.

### Primary Distribution Contract
1. Stable channel:
   1. `uvx google-workspace-mcp-advanced --transport stdio`
2. Deterministic pinned channel:
   1. `uvx google-workspace-mcp-advanced==x.y.z --transport stdio`
3. Local development channel:
   1. `uv run --project <repo-path> google-workspace-mcp-advanced --transport stdio`

### Release Pipeline (Primary Lane)
1. Required workflow:
   1. `.github/workflows/release-pypi.yml`
2. Required trust setup:
   1. PyPI trusted publisher for repository `Skeptomenos/google-workspace-mcp-advanced`
3. Required validations:
   1. `scripts/check_distribution_scope.py`
   2. `uvx google-workspace-mcp-advanced==<version> --help`

### Deferred npm Wrapper Lane
1. Wrapper workflow and launcher assets are retained in-repo for potential future reactivation.
2. This lane is intentionally out of scope for current release readiness.

### Distribution Acceptance (Updated)
1. Primary lane:
   1. PyPI release successful for target version.
   2. uvx stable and uvx pinned commands start successfully.
2. Deferred lane:
   1. npm publish/provenance may be validated later without blocking shipment.

## Update Protocol (Required)
1. On every issue transition (`Not Started` -> `In Progress` -> `Blocked`/`Done`), update the row in `Issue Execution Tracker (Living)`.
2. On every implementation session end:
   1. update `Last Updated: $(date -u +"%Y-%m-%d")
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
   2. validate code truth (`signatures`, implemented behavior, tests, and scripts) before setting any issue to `Done`,
   3. do not leave stale status in this file across sessions.
6. During rapid debug/test cycles:
   1. treat this file as the first write target for status changes,
   2. append a changelog heartbeat entry even when no issue status changes, so compaction/handoffs retain current truth.

## Verification Evidence (Living)

| Date (UTC) | Scope | Commands | Result | Notes |
|---|---|---|---|---|
| 2026-03-03 | DIST-01 release gate recovery | `uv run ruff check . && uv run ruff format --check . && uv run pyright --project pyrightconfig.json && uv run pytest -q` | Pass | Fixed release-blocking Pyright/type issues (`648 passed`, `3 skipped`; `0` pyright errors) |
| 2026-03-03 | DIST-01 publish verification (`main`) | `gh workflow run release-pypi.yml -f version=1.0.2` + `gh run watch 22618871138 --exit-status` | Pass | `verify`, `build`, and `publish` jobs all green on run `22618871138` (head `28509fc`) |
| 2026-03-03 | AUTH-01 release installability (`WS-06.5`) | `uvx --from google-workspace-mcp-advanced==1.0.1 google-workspace-mcp-advanced --help` | Pass | Published package resolves and launches via `uvx` |
| 2026-03-03 | AUTH-01 parity/env-path/refresh/diagnostics closure | `uv run pytest tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_auth_runtime_paths.py tests/integration/test_auth_flow.py -q` | Pass | Added WS-01.5 + WS-04.1/2/3 coverage (`29 passed`) |
| 2026-03-03 | AUTH-01 full verification rerun | `uv run ruff check . && uv run ruff format --check . && uv run pytest` | Pass | Full suite remains green after auth updates (`633 passed`, `3 skipped`) |
| 2026-03-02 | DIST-05 rename/migration hardening | `uv run ruff check . && uv run ruff format --check . && uv run pytest` | Pass | Canonical runtime/config rename + migration-guide/docs/test naming cleanup verified (`628 passed`, `3 skipped`) |
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
| 2026-02-27 | OPC-01 manual validation | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` session run | Pass with caveats | `23 PASS`, `0 FAIL`, `2 BLOCKED` (Chat API env), `1 NOT RUN` (transport interrupt manual step) |
| 2026-02-27 | OPC-01 manual validation (expanded) | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` OP-15..22 run | Pass with caveats | Expanded manual matrix to `29 PASS`, `0 FAIL`, `4 BLOCKED`, `1 NOT RUN`; fixed `DEF-007` (`set_publish_settings` payload mapping) and re-verified OP-18 |
| 2026-02-27 | Post-review mitigation verification | `uv run ruff check . && uv run ruff format . --check && uv run pytest -q` | Pass | Full verification after multi-table table-population targeting + fail-fast error-surfacing updates (`487 passed`) |
| 2026-02-27 | SAFE-01 static guard | `uv run python scripts/check_dry_run_defaults.py && uv run pytest -q tests/unit/core/test_dry_run_defaults_checker.py` | Pass | Added phase-gated dry-run default checker and dedicated unit coverage (`4 passed`) |
| 2026-02-27 | Post-checker full verification | `uv run ruff check . && uv run ruff format . --check && uv run pytest -q` | Pass | Full verification after adding dry-run checker and CI lint integration (`491 passed`) |
| 2026-02-27 | SAFE-01 (`gslides/slides_tools.py`) | `uv run pytest -q tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Slides dry-run runtime tests for both mutators and extended static checker coverage (`8 passed`) |
| 2026-02-27 | SAFE-01 (`gslides/slides_tools.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after Slides dry-run rollout and checker update (`495 passed`) |
| 2026-02-27 | SAFE-01 (`gforms/forms_tools.py`) | `uv run pytest -q tests/unit/tools/test_forms_tools.py tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Forms dry-run runtime tests and extended static checker coverage to `set_publish_settings` (`12 passed`) |
| 2026-02-27 | SAFE-01 (`gforms/forms_tools.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after Forms dry-run rollout and checker update (`499 passed`) |
| 2026-02-27 | SAFE-01 (`gtasks/tasks_tools.py`) | `uv run pytest -q tests/unit/tools/test_tasks_tools.py tests/unit/tools/test_forms_tools.py tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Tasks dry-run runtime tests and extended static checker coverage to `update_task_list` (`16 passed`) |
| 2026-02-27 | SAFE-01 (`gtasks/tasks_tools.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after Tasks dry-run rollout and checker update (`503 passed`) |
| 2026-02-27 | SAFE-01 (`gchat/chat_tools.py`) | `uv run pytest -q tests/unit/tools/test_chat_tools.py tests/unit/tools/test_tasks_tools.py tests/unit/tools/test_forms_tools.py tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Chat dry-run runtime tests and extended static checker coverage to `send_message` (`18 passed`) |
| 2026-02-27 | SAFE-01 (`gchat/chat_tools.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after Chat dry-run rollout and checker update (`505 passed`) |
| 2026-02-27 | SAFE-01 (`gmail/labels.py`) | `uv run pytest -q tests/unit/tools/test_gmail_labels_tools.py tests/unit/tools/test_chat_tools.py tests/unit/tools/test_tasks_tools.py tests/unit/tools/test_forms_tools.py tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Gmail label dry-run runtime tests and extended static checker coverage to `manage_gmail_label` (`22 passed`) |
| 2026-02-27 | SAFE-01 (`gmail/labels.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after Gmail label dry-run rollout and checker update (`509 passed`) |
| 2026-02-27 | SAFE-01 (`gmail/labels.py`, message-label mutator) | `uv run pytest -q tests/unit/tools/test_gmail_labels_tools.py tests/unit/tools/test_chat_tools.py tests/unit/tools/test_tasks_tools.py tests/unit/tools/test_forms_tools.py tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added message-label dry-run runtime tests and extended static checker coverage to `modify_gmail_message_labels` (`24 passed`) |
| 2026-02-27 | SAFE-01 (`gmail/labels.py`, message-label mutator) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after message-label dry-run rollout and checker update (`511 passed`) |
| 2026-02-27 | SAFE-01 (`gmail/labels.py`, batch-message-label mutator) | `uv run pytest -q tests/unit/tools/test_gmail_labels_tools.py tests/unit/tools/test_chat_tools.py tests/unit/tools/test_tasks_tools.py tests/unit/tools/test_forms_tools.py tests/unit/tools/test_slides_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added batch message-label dry-run runtime tests and extended static checker coverage to `batch_modify_gmail_message_labels` (`26 passed`) |
| 2026-02-27 | SAFE-01 (`gmail/labels.py`, batch-message-label mutator) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after batch message-label dry-run rollout and checker update (`513 passed`) |
| 2026-02-28 | SAFE-01 (`gdocs/writing.py`) | `uv run pytest tests/unit/tools/test_docs_writing_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Docs writing dry-run runtime tests and extended static checker coverage (`14 passed`) |
| 2026-02-28 | SAFE-01 (`gdocs/writing.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest` | Pass | Full verification protocol after Docs writing dry-run rollout and checker update (`523 passed`) |
| 2026-02-28 | RM-02 regression coverage | `uv run pytest tests/integration/test_create_doc_table_population_flow.py` | Pass | Added create_doc integration coverage for preceding-content table flow, multi-table order, and incomplete-population fail-fast (`3 passed`) |
| 2026-02-28 | Post-RM-02 integration full verification | `uv run ruff check . && uv run ruff format . --check && uv run pytest && uv run python scripts/check_dry_run_defaults.py` | Pass | Full verification protocol after integration regression addition (`526 passed`) |
| 2026-02-28 | SAFE-01 (`gdocs/elements.py`, `gdocs/tables.py`) | `uv run pytest tests/unit/tools/test_docs_elements_tools.py tests/unit/tools/test_docs_tables_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added Docs elements/tables dry-run runtime tests and extended static checker coverage (`10 passed`) |
| 2026-02-28 | SAFE-01 (`gdocs/elements.py`, `gdocs/tables.py`) | `uv run ruff check . && uv run ruff format . --check && uv run pytest && uv run python scripts/check_dry_run_defaults.py` | Pass | Full verification protocol after Docs elements/tables dry-run rollout and checker update (`532 passed`) |
| 2026-02-28 | SAFE-01 (`gtasks/tasks_tools.py`, remaining mutators) | `uv run pytest tests/unit/tools/test_tasks_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added dry-run runtime tests for remaining Tasks mutators (`delete_task_list`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks`) and extended checker coverage (`18 passed`) |
| 2026-02-28 | Post-Tasks full verification | `uv run ruff check . && uv run ruff format . --check && uv run pytest && uv run python scripts/check_dry_run_defaults.py` | Pass | Full verification protocol after Tasks mutator dry-run rollout (`542 passed`) |
| 2026-02-28 | SAFE-01 (`gdocs/writing.py`, `create_doc`) | `uv run pytest -q tests/integration/test_create_doc_table_population_flow.py tests/unit/tools/test_docs_writing_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added `create_doc` default dry-run behavior, updated integration expectations to explicit `dry_run=False`, and expanded docs writing runtime coverage (`19 passed`) |
| 2026-02-28 | Post-`create_doc` full verification | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after `create_doc` dry-run rollout (`544 passed`) |
| 2026-02-28 | SAFE-01 (`gsheets/sheets_tools.py`, remaining mutators) | `uv run pytest -q tests/unit/tools/test_sheets_tools_dry_run.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added dry-run runtime tests for remaining Sheets mutators (`format_sheet_range`, conditional-format add/update/delete, `create_sheet`) and extended checker coverage (`14 passed`) |
| 2026-02-28 | Post-Sheets full verification | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after Sheets mutator dry-run rollout (`554 passed`) |
| 2026-02-28 | SAFE-01 (`gdrive/sync_tools.py`, Wave 2B mutators) | `uv run pytest -q tests/unit/tools/test_drive_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added dry-run runtime tests for `link_local_file`, `upload_folder`, `mirror_drive_folder`, and `download_doc_tabs`; checker scope expanded to include remaining sync mutators (`61 passed`) |
| 2026-02-28 | Post-Drive-sync full verification | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after Drive sync mutator dry-run rollout (`562 passed`) |
| 2026-02-28 | SAFE-01 residual runtime closure (`gcalendar`, `gmail/messages`, `gdrive/sync_tools` verified-existing mutators) | `uv run pytest -q tests/unit/tools/test_calendar_mutators_tools.py tests/unit/tools/test_gmail_messages_tools.py tests/unit/tools/test_drive_tools.py tests/unit/core/test_dry_run_defaults_checker.py && uv run python scripts/check_dry_run_defaults.py` | Pass | Added isolated runtime dry-run harness coverage for remaining SAFE-01 gaps (`75 passed`), checker remained green |
| 2026-02-28 | Post-SAFE-01 full verification | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Full verification protocol after SAFE-01 closure updates (`576 passed`) |
| 2026-02-28 | OPC-01 manual validation (`OP-59..66`, initial pass) | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` session run | Pass with defects | OP-59/60/63/65/66 passed; OP-61/62 blocked (`drive_write` scope key), OP-64 failed (folder name resolution). Logged DEF-010 and DEF-011 for remediation and rerun |
| 2026-02-28 | OPC-01 manual validation (`OP-61..64`, rerun) | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` rerun | Pass with caveats | After DEF-010/011 fixes and restart, OP-61..64 all passed. Manual matrix now extends through OP-66 with `11 defects found, 11 fixed`; later Chat validation rows (`OP-21/22`, `EX-06`) were unblocked and passed; only `OP-06` remains roadmap-deferred |
| 2026-02-28 | QUAL-01 type gate promotion | `uv run pyright --project pyrightconfig.json` | Pass | Added source-scoped `pyrightconfig.json`, reduced baseline to zero, and promoted pyright to blocking CI gate |
| 2026-02-28 | QUAL-02 automated lane scaffolding | `uv run pytest -q tests/mcp_protocol tests/live_mcp tests/opencode` | Pass | Added protocol/live/opencode automation lane scaffolding and validated baseline execution (`5 passed, 2 skipped`) |
| 2026-02-28 | Post-QUAL-01/QUAL-02 full verification | `uv run ruff check . && uv run ruff format --check . && uv run pyright --project pyrightconfig.json && uv run pytest -q` | Pass | Full verification after type-gate promotion + lane scaffolding (`581 passed, 2 skipped`) |
| 2026-02-28 | OPC-01 live serve smoke | `bash scripts/opencode_serve_smoke.sh` | Pass | Verified server lifecycle spawn + `/global/health` + teardown (`1.2.15`) |
| 2026-02-28 | OPC-01 SDK wrapper smoke (live) | `OPENCODE_SMOKE_LIVE=1 node scripts/opencode_sdk_smoke.mjs --live` | Pass | Verified attached prompt flow returns sentinel text and deterministic server teardown (`session` created and closed) |
| 2026-02-28 | OPC-01 pytest lane validation | `uv run pytest -q tests/opencode && OPENCODE_SMOKE_LIVE=1 uv run pytest -q tests/opencode/test_opencode_sdk_session_flow.py` | Pass | Default lane (`2 passed, 1 skipped`) + live lane (`2 passed`) |
| 2026-02-28 | Post-OPC-01 full verification | `uv run ruff check . && uv run ruff format --check . && uv run pyright --project pyrightconfig.json && uv run pytest -q` | Pass | Full verification after OpenCode lifecycle smoke implementation (`581 passed, 3 skipped`) |
| 2026-02-28 | Error-path closure (`ER-06`) | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` ER-06 run | Pass | Transport interruption now verified (`ER-01..06 = 6/6 PASS`); dead MCP subprocess is handled cleanly and tools are removed without crash/hang |
| 2026-02-28 | QUAL-02 targeted auth/session coverage | `uv run pytest -q tests/unit/auth/test_auth_runtime_paths.py` | Pass | Added middleware stdio/session-binding runtime tests + token-bridge regression tests (`7 passed`) |
| 2026-02-28 | Post-QUAL-02 auth-coverage full verification | `uv run ruff check . && uv run ruff format --check . && uv run pyright --project pyrightconfig.json && uv run pytest -q` | Pass | Full verification after targeted auth/session coverage addition (`588 passed, 3 skipped`) |
| 2026-02-28 | RM-03 list-exit bullet regression fix | `uv run pytest -q tests/unit/gdocs/test_markdown_parser.py && uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Updated list bullet range to exclude trailing list-closing newline; added task-list regression assertions for bullet/delete range boundary; full verification green (`590 passed, 3 skipped`) |
| 2026-03-01 | RM-03 live regression validation (`OP-67`) | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` OP-67 run | Pass | Manual live check confirms clean transition after task list (`☐ one`, `☑ two`, `After`, paragraph) with no extra empty bullet; running total `78 PASS`, `0 FAIL`, `1 BLOCKED`, `0 NOT RUN` |
| 2026-03-01 | RM-01 code-block visual parity implementation | `uv run pytest -q tests/unit/gdocs/test_markdown_parser.py tests/integration/test_create_doc_table_population_flow.py && uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Added code-block paragraph shading + borders and fenced-language label handling in parser; added unit + integration regression coverage; full verification green (`593 passed`, `3 skipped`). Pending manual visual confirmation via `OP-68`. |
| 2026-03-01 | RM-04 image-path deterministic integration coverage | `uv run pytest -q tests/integration/test_create_doc_table_population_flow.py && uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Added integration assertions for markdown image insertion with surrounding-text stability and deterministic multi-image order; full verification green (`595 passed`, `3 skipped`). Pending manual visual confirmation via `OP-69`. |
| 2026-03-01 | DEF-012 markdown image insertion fix (phase 1) | `uv run pytest -q tests/unit/gdocs/test_markdown_parser.py tests/integration/test_create_doc_table_population_flow.py && uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Implemented robust inline-image placeholder replacement in `MarkdownToDocsConverter` (`deleteContentRange` + `insertInlineImage`) and added regression assertions for image request generation/order; full verification green (`596 passed`, `3 skipped`). |
| 2026-03-01 | DEF-012 markdown image insertion fix (phase 2) | `uv run pytest -q tests/unit/tools/test_docs_writing_tools.py tests/integration/test_create_doc_table_population_flow.py && uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | Pass | Updated `create_doc` to execute markdown image placeholder replacement in a dedicated second `batchUpdate` (separate from structure/style requests) and added integration coverage for phase ordering and image/table interaction; full verification green (`598 passed`, `3 skipped`). |
| 2026-03-01 | RM-04 live closure (`OP-69`) | `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` OpenCode run | Pass | OpenCode run 4 (`doc 1pE9JML...`) confirmed inline images render correctly in order; DEF-012 set to Fixed. |
| 2026-03-01 | Distribution guardrails kickoff (`DIST-00`/`DIST-01`) | `uv run python scripts/check_distribution_scope.py && uv run python scripts/check_release_version_match.py` | Pass | Added canonical package-name guard (`google-workspace-mcp-advanced`) and version-coupling guard (`pyproject.toml` vs `package.json`) and wired both into CI lint job. |
| 2026-03-01 | Distribution automation + launcher smoke | `uv run pytest -q tests/unit/core/test_npm_launcher.py tests/unit/core/test_distribution_checks.py && uv run python scripts/check_distribution_scope.py && uv run python scripts/check_release_version_match.py` | Pass | Added release workflows (`release-pypi.yml`, `release-npm.yml`) with PyPI-first gating, OIDC, and npm provenance; added launcher smoke tests and distribution release runbook. |

## Decision Log (Living)

| Date (UTC) | Decision | Rationale | Affected IDs |
|---|---|---|---|
| 2026-02-27 | Adopt canonical npm package `google-workspace-mcp-advanced` | Prevent naming drift and keep distribution canonical | DIST-00..DIST-04 |
| 2026-02-27 | Keep `PLAN.md` as canonical living execution plan | Reduce planning drift and duplicate sources | DOC-01 |
| 2026-02-27 | Track dry-run rollout progress in dedicated matrix doc | Improve execution transparency for `SAFE-01` and avoid checklist drift | SAFE-01, DOC-01 |
| 2026-02-27 | Enforce default-deny for unverified JWT identity extraction | Remove unsigned-token identity trust by default while retaining emergency compatibility path | SEC-01 |
| 2026-02-27 | Centralize auth persistence writes in shared security I/O module | Eliminate duplicated write logic and enforce consistent secure file/dir modes | SEC-02 |
| 2026-02-27 | Enforce decorator ordering with static CI guard | Prevent divergence in tool safety/readability convention over time | CONV-01, QUAL-01 |
| 2026-02-27 | Add OpenCode `serve` + SDK as secondary autonomous test lane | Provides realistic external control-plane validation beyond in-process MCP harness | OPC-01, QUAL-02 |
| 2026-02-27 | Treat Chat API missing for personal account as environment blocker, not code defect | Prevent false negatives in manual quality status while preserving explicit blocker tracking | QUAL-02, OPC-01 |
| 2026-02-28 | Defer PSE-backed `search_custom` env setup (`OP-06`) | Web search is currently covered by other MCPs; keep focus on protocol automation and roadmap closure while preserving documented setup path for later enablement | QUAL-02, DOC-01 |
| 2026-02-27 | Fail `create_doc` when phase-2 table population is incomplete | Prevent silent partial-success responses and preserve correctness guarantees for markdown table writes | RM-02, QUAL-02 |
| 2026-02-27 | Resolve status drift using code truth as authority | Avoid premature closure by requiring signature/behavior/test/script verification before `Done` transitions | SAFE-01, QUAL-02, DOC-01 |
| 2026-03-01 | Use visual verification as authoritative signal for markdown image rendering regression closure | `inspect_doc_structure` does not reliably surface inline image objects for OP-69; visual document confirmation is required for inline-image pass/fail decisions | RM-04, QUAL-02 |
| 2026-03-01 | Enforce canonical npm identity and Python/npm version coupling in CI before publish workflows | Prevent naming drift and wrapper/runtime version mismatch while distribution infrastructure is being built | DIST-00, DIST-01 |
| 2026-02-27 | Use phase-gated dry-run checker coverage while rollout is incomplete | Add immediate CI regression protection for completed SAFE-01 modules without falsely closing remaining inventory | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Slides batch updates once implemented | Lock in no-regression protection immediately after rolling out `batch_update_presentation` dry-run defaults | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Forms publish-setting mutator once implemented | Prevent regression on form publish updates after adding default-safe dry-run behavior | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Tasks task-list update mutator once implemented | Prevent regression on task-list rename/update mutations after adding default-safe dry-run behavior | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Chat send-message mutator once implemented | Prevent regression on outbound chat message mutation safety defaults | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Gmail label-management mutator once implemented | Prevent regression on Gmail label create/update/delete safety defaults as rollout continues | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Gmail message-label mutator once implemented | Prevent regression on per-message label mutation safety defaults during remaining Gmail label rollout | SAFE-01, QUAL-01 |
| 2026-02-27 | Expand phase-gated dry-run checker to include Gmail batch message-label mutator once implemented | Prevent regression on batch message-label mutation safety defaults and close Gmail labels checker coverage | SAFE-01, QUAL-01 |
| 2026-02-28 | Expand phase-gated dry-run checker to include Docs writing mutators once implemented | Prevent regression on Docs text/header/batch/markdown mutation safety defaults while `create_doc` remains a tracked pending mutator | SAFE-01, QUAL-01 |
| 2026-02-28 | Expand phase-gated dry-run checker to include Docs elements/table mutators once implemented | Prevent regression on Docs structural insertion and table creation safety defaults as SAFE-01 rollout continues | SAFE-01, QUAL-01 |
| 2026-02-28 | Expand phase-gated dry-run checker to include remaining Tasks mutators once implemented | Prevent regression on task update/move/delete/clear and list-delete safety defaults after completing full Tasks mutator rollout | SAFE-01, QUAL-01 |
| 2026-02-28 | Expand phase-gated dry-run checker to include `gdocs.create_doc` once implemented | Lock in no-regression protection for document creation safety so omitted `dry_run` never creates remote docs | SAFE-01, QUAL-01 |
| 2026-02-28 | Expand phase-gated dry-run checker to include remaining Sheets mutators once implemented | Prevent regression on formatting/conditional-rule/sheet-creation mutation safety defaults after completing full Sheets mutator rollout | SAFE-01, QUAL-01 |
| 2026-02-28 | Expand phase-gated dry-run checker to include remaining `gdrive.sync_tools` mutators once implemented | Prevent regression on local-link/upload/mirror/tab-download safety defaults and lock in full sync-tool dry-run coverage | SAFE-01, QUAL-01 |
| 2026-02-28 | Promote pyright to blocking CI using a source-scoped config | Enforce strict static typing in production code without introducing test/build false positives during migration | QUAL-01 |
| 2026-02-28 | Keep OpenCode live lifecycle smoke opt-in (`OPENCODE_SMOKE_LIVE=1`) | Preserve deterministic local validation of prompt execution/teardown without forcing model/provider credentials in default test runs | OPC-01, QUAL-02 |

## Session Handoff (Living)
1. Current Focus: `Auth release readiness and rollout documentation`
2. Next 3 Actions:
   1. prepare release notes/version bump for auth stabilization + single-MCP multi-client rollout,
   2. optionally improve `complete_google_auth` messaging when callback server already consumed OAuth state,
   3. run post-release smoke on pinned package version and archive evidence.
3. Active Blockers:
   1. None for auth track closure.

## Execution Changelog (Living)
1. 2026-02-27: Promoted `PLAN.md` to canonical living execution doc; added readiness verdict, wave schedule, issue tracker, update protocol, evidence log, decision log, and session handoff.
2. 2026-02-27: Completed Wave 0 preflight tasks for formatting and living-doc scaffolding; added `agent-docs/roadmap/STATUS.md` and `agent-docs/roadmap/DRY_RUN_MATRIX.md`; initialized tracker owners and set `DOC-01` to `In Progress`.
3. 2026-02-27: Replaced external ticket dependency with local tracker `TASKS.md` and aligned Wave 0 tracking workflow accordingly.
4. 2026-02-27: Closed `RUN-01` by fixing `fastmcp_server.py` docs import path and adding blocking CI startup smoke checks for `main` and `fastmcp_server`.
5. 2026-02-27: Closed `SEC-01` by default-denying unverified JWT identity extraction in auth/session middleware, introducing `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT` break-glass behavior, and adding guardrail tests.
6. 2026-02-27: Closed `SEC-02` by introducing `auth/security_io.py` and migrating credential/session JSON persistence to secure atomic writes with explicit permission tests.
7. 2026-02-27: Closed `CONV-01` by normalizing decorator order in `gmail/threads.py`, adding `scripts/check_tool_decorators.py` with unit tests, and wiring the check into CI lint gates.
8. 2026-02-27: Started `SAFE-01` Wave 2A by implementing `dry_run=True` defaults and deterministic dry-run previews for `gcalendar` mutators (`create_event`, `modify_event`, `delete_event`) with calendar dry-run contract tests.
9. 2026-02-27: Continued `SAFE-01` Wave 2A by implementing `dry_run=True` defaults and deterministic dry-run previews for `gdrive/files.py` mutators (`create_drive_file`, `update_drive_file`) with runtime tests validating dry-run skip and explicit mutation behavior.
10. 2026-02-27: Added `OPC-01` planning track for OpenCode headless server + SDK automation; verified local `opencode serve` startup and documented auth mitigation requirements.
11. 2026-02-27: Continued `SAFE-01` Wave 2A by implementing `dry_run=True` defaults and deterministic dry-run previews for `gdrive/permissions.py` mutators with runtime tests covering `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, and `transfer_drive_ownership`.
12. 2026-02-27: Ingested OpenCode manual test session results from `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`; marked `QUAL-02`/`OPC-01` as in progress, recorded `23 PASS` manual matrix outcome, and captured remaining blocked/not-run items as next-step actions.
13. 2026-02-27: Completed targeted code-review mitigation pass: fixed multi-table markdown table targeting in table phase-2 population, added fail-fast incomplete-table-population error surfacing in `create_doc`, reconciled manual-test status counters across living docs, and re-ran full verification (`487 passed`).
14. 2026-02-27: Intermediate tracker normalization moved `SAFE-01` and `QUAL-02` to `Done`; later superseded by code-truth readiness reconciliation.
15. 2026-02-27: Readiness pass reconciliation corrected premature closure signals: returned `SAFE-01`/`QUAL-02` to `In Progress`, aligned session handoff to concrete closure gates, and synchronized with `agent-docs/roadmap/DRY_RUN_MATRIX.md`, `TASKS.md`, and `agent-docs/roadmap/STATUS.md`.
16. 2026-02-27: Performed code-truth audit of dry-run inventory across service modules; updated inventory current-state rows and formalized code-first drift resolution rule in update protocols.
17. 2026-02-27: Implemented `scripts/check_dry_run_defaults.py` with unit tests and CI lint integration; checker currently enforces rolled-out SAFE-01 mutators and full verification remains green (`491 passed`).
18. 2026-02-27: Continued `SAFE-01` Wave 2A by implementing `dry_run=True` default and deterministic preview for `gslides.batch_update_presentation`, adding runtime tests for both Slides mutators (`dry_run=True` and `dry_run=False` paths), extending static checker coverage, and re-running full verification (`495 passed`).
19. 2026-02-27: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gforms.set_publish_settings`, adding dedicated Forms dry-run runtime tests, extending static checker coverage, and re-running full verification (`499 passed`).
20. 2026-02-27: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gtasks.update_task_list`, adding dedicated Tasks dry-run runtime tests, extending static checker coverage, and re-running full verification (`503 passed`).
21. 2026-02-27: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gchat.send_message`, adding dedicated Chat dry-run runtime tests, extending static checker coverage, and re-running full verification (`505 passed`).
22. 2026-02-27: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gmail.labels.manage_gmail_label`, adding dedicated Gmail label dry-run runtime tests, extending static checker coverage, and re-running full verification (`509 passed`).
23. 2026-02-27: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gmail.labels.modify_gmail_message_labels`, adding dedicated Gmail message-label dry-run runtime tests, extending static checker coverage, and re-running full verification (`511 passed`).
24. 2026-02-27: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gmail.labels.batch_modify_gmail_message_labels`, adding dedicated Gmail batch message-label dry-run runtime tests, extending static checker coverage, and re-running full verification (`513 passed`).
25. 2026-02-28: Continued `SAFE-01` by implementing `dry_run=True` defaults and deterministic previews for `gdocs.writing` mutators (`modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown`), adding dedicated runtime tests, extending checker coverage, and re-running full verification (`523 passed`).
26. 2026-02-28: Added deterministic create_doc integration regression coverage for table-with-preceding-content and multi-table order (`tests/integration/test_create_doc_table_population_flow.py`), including incomplete-table-population fail-fast assertions, and re-ran full verification (`526 passed`).
27. 2026-02-28: Continued `SAFE-01` by implementing `dry_run=True` defaults and deterministic previews for Docs element/table mutators (`insert_doc_elements`, `insert_doc_image`, `create_table_with_data`), adding dedicated runtime tests, extending checker coverage, and re-running full verification (`532 passed`).
28. 2026-02-28: Continued `SAFE-01` by implementing `dry_run=True` defaults and deterministic previews for remaining Tasks mutators (`delete_task_list`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks`), adding full Tasks mutator runtime tests, extending checker coverage, and re-running full verification (`542 passed`).
29. 2026-02-28: Reconciled latest OpenCode manual test status into tracker truth (`53 PASS`, `0 FAIL`, `4 BLOCKED`), confirmed remaining SAFE-01 mutator gaps (`gdocs.create_doc`, remaining `gsheets`, and `gdrive/sync_tools.py`), and queued `create_doc` as the next implementation slice.
30. 2026-02-28: Continued `SAFE-01` by implementing `dry_run=True` default and deterministic preview for `gdocs.create_doc`, extending checker coverage to include `create_doc`, updating create-doc integration tests to explicit `dry_run=False`, preparing OpenCode handoff rows `OP-47..48`, and re-running full verification (`544 passed`).
31. 2026-02-28: Continued `SAFE-01` by implementing `dry_run=True` defaults and deterministic previews for remaining Sheets mutators (`format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, `create_sheet`), adding dedicated runtime tests, extending checker coverage, preparing OpenCode handoff rows `OP-49..58`, and re-running full verification (`554 passed`).
32. 2026-02-28: Reconciled OpenCode post-handoff execution results for OP-47..58 (`create_doc` + remaining Sheets mutators) into tracker truth; manual matrix now `65 PASS`, `0 FAIL`, `4 BLOCKED` with zero new defects and cleanup confirmed.
33. 2026-02-28: Continued `SAFE-01` by implementing `dry_run=True` defaults and deterministic previews for `gdrive/sync_tools.py` Wave 2B mutators (`link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs`), adding dedicated runtime tests, extending checker coverage (including `update_google_doc` and `download_google_doc`), preparing OpenCode handoff rows `OP-59..66`, and re-running full verification (`562 passed`).
34. 2026-02-28: OpenCode executed OP-59..66 and surfaced DEF-010 (`mirror_drive_folder` name-resolution failure) plus DEF-011 (`drive_write` scope-key mismatch). Applied fixes, restarted OpenCode, reran OP-61..64, and confirmed all OP-59..66 rows are PASS with cleanup complete.
35. 2026-02-28: Reconciled post-OP-66 tracker drift across living docs; removed stale “OP-59..66 pending” language and kept `SAFE-01` open only for code-truth residual runtime gaps and manual/env blockers (`ER-06`, `OP-06`, `OP-21/22`, `EX-06`).
36. 2026-02-28: Added isolated runtime dry-run tests for `gmail/messages.py` and `gdrive/sync_tools.py` verified-existing mutators (`update_google_doc`, `download_google_doc`), resolving two remaining SAFE-01 runtime coverage gaps.
37. 2026-02-28: Added isolated runtime dry-run harness tests for `gcalendar` mutators (`create_event`, `modify_event`, `delete_event`), re-ran full verification (`576 passed`), and closed `SAFE-01` to `Done`.
38. 2026-02-28: Documented roadmap deferral for PSE-backed `search_custom` env setup (`OP-06`) because web search is currently covered by other MCPs; removed `OP-06` from active blocker path while preserving setup docs for future enablement.
39. 2026-02-28: Closed `QUAL-01` by adding source-scoped `pyrightconfig.json`, fixing remaining source typing errors to zero, and promoting pyright to a blocking CI gate; advanced `QUAL-02`/`OPC-01` by adding and validating protocol/live/opencode automated lane scaffolding (`5 passed, 2 skipped`) and re-running full verification (`581 passed, 2 skipped`).
40. 2026-02-28: Closed `OPC-01` by implementing real OpenCode lifecycle smoke flows (`scripts/opencode_serve_smoke.sh`, `scripts/opencode_sdk_smoke.mjs --live`) with deterministic teardown, adding pytest wrappers (default + live opt-in), and re-running full verification (`581 passed, 3 skipped`).
41. 2026-02-28: Ingested OpenCode ER-06 transport interruption result (`PASS`): manual matrix now has no `NOT RUN` rows (`74 PASS`, `0 FAIL`, `4 BLOCKED`), removed stale ER-06 pending references from handoff/blocker tracking, and kept QUAL-02 open only for targeted auth/session coverage plus Chat env blockers.
42. 2026-02-28: Completed targeted `QUAL-02` auth/session runtime coverage by adding `tests/unit/auth/test_auth_runtime_paths.py` (middleware stdio/session-binding + token bridge paths), validated targeted tests (`7 passed`), and re-ran full verification (`588 passed, 3 skipped`); remaining `QUAL-02` risk is now limited to environment-blocked Chat validation.
43. 2026-02-28: Reconciled living docs after final Chat validation run (`OP-21`, `OP-22`, `EX-06` all PASS). Closed `QUAL-02` as complete with `OP-06` explicitly deferred by product decision; updated `PLAN.md`, `TASKS.md`, `agent-docs/roadmap/STATUS.md`, and `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` metadata/status for cross-doc consistency.
44. 2026-02-28: Closed `RM-03` in code by preventing list bullet ranges from including the trailing list-closing newline (fixing extra empty post-list bullet artifacts), added parser regressions for task-list boundary handling, and re-ran the full verification protocol (`590 passed`, `3 skipped`).
45. 2026-03-01: Ingested OpenCode `OP-67` result (`PASS`) and synchronized living trackers; `RM-03` is now closed in both code-truth and live-manual verification (`78 PASS`, `0 FAIL`, `1 BLOCKED`, `0 NOT RUN` in manual matrix).
46. 2026-03-01: Advanced `RM-01` to `In Progress` by implementing code-block paragraph shading + border styling and fenced language label handling in `gdocs/markdown_parser.py`, adding parser unit and create-doc integration coverage, and re-running full verification (`593 passed`, `3 skipped`); added `OP-68` as next OpenCode visual regression row.
47. 2026-03-01: Advanced `RM-04` to `In Progress` by adding deterministic create-doc integration coverage for markdown image insertion (single-image flow + multi-image order), re-running the full verification protocol (`595 passed`, `3 skipped`), and adding `OP-69` as next OpenCode visual regression row.
48. 2026-03-01: Ingested OpenCode OP-68/OP-69 outcomes (`OP-68 PASS`, `OP-69 FAIL`) and logged DEF-012 (`create_doc` markdown images missing inline objects); updated trackers to mark `RM-01` complete and `RM-04` blocked on defect verification.
49. 2026-03-01: Implemented DEF-012 fix by replacing buffered image placeholders with deterministic `deleteContentRange` + `insertInlineImage` requests in the markdown parser, added unit/integration regressions for image replacement behavior, and re-ran full verification (`596 passed`, `3 skipped`).
50. 2026-03-01: Implemented DEF-012 phase-2 remediation in `create_doc` by splitting inline-image delete+insert operations into a dedicated second `batchUpdate` (after structure/style phase and before table population), added unit/integration regressions for split-phase ordering, and re-ran full verification (`598 passed`, `3 skipped`).
51. 2026-03-01: Ingested OpenCode OP-69 run 4 (`PASS`), closed `RM-04`, and marked DEF-012 as fixed with visual verification note (`inspect_doc_structure` limitation documented).
52. 2026-03-01: Closed `DOC-01` and `RM-02` documentation tail by reconciling `ROADMAP.md` + `TESTING_PLAN_MARKDOWN.md` to current status and marking `TEST_RESULTS.md`/`ISSUE_REPORT.md` as archived snapshots.
53. 2026-03-01: Started distribution work (`DIST-00`..`DIST-02`) by adding canonical npm launcher metadata (`package.json`), launcher preflight script (`bin/google-workspace-mcp-advanced.cjs`), and CI guard scripts for package name and version coupling.
54. 2026-03-01: Fixed a source-scoped pyright regression in `gdocs/markdown_parser.py` by narrowing markdown image `src` extraction to `str` before appending to typed pending-image state; re-ran full verification (`ruff`, `pyright`, `pytest` all green).
55. 2026-03-01: Completed distribution implementation milestones ahead of next test phase: added `release-pypi.yml` + `release-npm.yml` workflows with PyPI->npm gating, added PyPI-version presence guard (`scripts/check_pypi_version_available.py`), added launcher smoke tests (`tests/unit/core/test_npm_launcher.py`) and distribution check tests, and published rollout/rollback runbook (`docs/DISTRIBUTION_RELEASE.md`).
56. 2026-03-01: Prepared next distribution validation handoff matrix in `agent-docs/testing/DISTRIBUTION_TEST_PHASE.md` (`DT-01`..`DT-08`) covering release sequencing, channel validation (`latest`/`next`/pinned), and rollback execution.
57. 2026-03-01: Added mandatory pre-merge rendering gate `OP-70` (kitchen-sink markdown fixture) and updated living docs so merge/push is blocked until full visual rendering PASS evidence is captured.
58. 2026-03-02: Implemented shared markdown-path mitigation for `DEF-013` (table placeholder replacement instead of post-table cursor prediction, centralized structural phase partitioning for `create_doc` + `insert_markdown`, task-list checkbox no-bullet behavior), added regression coverage, and re-ran full verification (`609 passed`, `3 skipped`). Pending manual `OP-70` rerun for closure.
59. 2026-03-02 (in progress): Started DEF-013 attempt 3 after OpenCode regression (`deleteContentRange` out-of-bounds). Root cause identified as placeholder indices not compensating for TAB removal by `createParagraphBullets`; patch landed in shared parser path with new tab-shift regression tests. Full verification rerun is in progress.
60. 2026-03-02: Completed DEF-013 attempt 3 code verification: added TAB-removal compensation for image/table placeholder indices in shared parser path and validated full protocol green (`611 passed`, `3 skipped`). OP-70 rerun in OpenCode is now the only remaining closure gate for DEF-013.
61. 2026-03-02: Reinforced living-doc discipline for compaction safety: update cadence now explicitly requires immediate `PLAN.md` updates after each OpenCode/manual attempt result and each local verification rerun during active debug loops.
62. 2026-03-02: Status heartbeat (no state change): branch remains blocked only by `OP-70` rerun after DEF-013 attempt 3; distribution live validation (`DT-01`..`DT-07`) remains queued behind gate clearance and workflow availability on `main`.
63. 2026-03-02 (in progress): Started DEF-013 nuance-fix slice from latest OpenCode handoff (Attempt 4): targeting only residual issues — table-cell font-size reset, source blank-line preservation around heading/hr regions, and minor strikethrough alignment drift validation.
64. 2026-03-02: Landed DEF-013 nuance-fix patchset: added source-map-based blank-line preservation for top-level blocks, restored table block paragraph termination after placeholder insertion, and forced table cell baseline text style (`fontSize=11`, bold only for headers) during population to prevent inherited H2 sizing. Verification is green (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q` => `615 passed`, `3 skipped`).
65. 2026-03-02: Synced living trackers after DEF-013 nuance patch (`PLAN.md`, `TASKS.md`, `agent-docs/roadmap/STATUS.md`, `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`, `agent-docs/testing/OP_70_EVIDENCE.md`) and prepared explicit OpenCode rerun handoff: restart required, run preflight, then execute `OP-70` on current HEAD.
66. 2026-03-02: Ingested OpenCode `OP-70` Attempt 5 result (`PASS`) and finalized merge/push gate closure; manual matrix is now `81 PASS`, `0 FAIL`, `1 BLOCKED`, `0 NOT RUN`, with DEF-013 fixed.
67. 2026-03-02: Reconciled session handoff and blocker state to distribution-first execution truth (removed stale OP-70 fail blockers, retained `main` workflow availability and trusted-publisher prerequisites).
68. 2026-03-02: Added smart-chip roadmap extensions `RM-05`/`RM-06`/`RM-07` to the issue tracker as the next markdown feature wave after distribution closure.
69. 2026-03-02: Attempted first live release execution via `gh workflow run release-pypi.yml --ref codex/run-01-fastmcp-import-smoke`; GitHub returned `HTTP 404` because release workflows are still absent on default branch (`main`), confirming `DIST-01`/`DIST-04` remain externally blocked until merge.
70. 2026-03-02: Re-validated distribution blockers against `main` after merge (`a39b34f`): `gh workflow list` still exposes only `CI`, `DT-01..DT-03` remain blocked with workflow-404 responses on default branch, and `DT-07` remains blocked because npm package `google-workspace-mcp-advanced` is not yet published (`npm view` returns `E404`).
71. 2026-03-02: Completed mainline hardening and merge path for distribution: resolved CI-only FastMCP metadata drift (tool `.fn`/`.name` compatibility shim + Python 3.10 time API fix), repaired `release-pypi.yml` YAML parsing/dispatch issues, and merged follow-up PRs so both `Release PyPI` and `Release npm` are active on `main`.
72. 2026-03-02: Executed first live `Release PyPI` workflow-dispatch run (`22577418832`) through `verify` and `build`; publish step initially failed with PyPI trusted publishing exchange error `invalid-publisher` for claims `repository=Skeptomenos/google-workspace-mcp-advanced`, `workflow_ref=.../release-pypi.yml@refs/heads/main`, `environment=pypi`.
73. 2026-03-02: Re-ran `Release PyPI` after publisher setup (`22577853068`) and completed all jobs successfully (`verify`, `build`, `publish`), confirming PyPI package availability (`https://pypi.org/pypi/google-workspace-mcp-advanced/json` -> 200, version `1.0.0`).
74. 2026-03-02: `Release npm` auto-trigger run (`22577900946`) passed verification gates and provenance generation but failed final publish with npm auth error (`Access token expired or revoked`, `E404` PUT publish). Distribution closure now depends on npm auth/trusted-publisher remediation.
75. 2026-03-02: Product decision updated distribution scope to uvx-only for now; npm/npx wrapper lane is explicitly de-scoped (retained in-repo for possible future reactivation) and no longer tracked as a release blocker.
76. 2026-03-02: Finalized uvx-only user-doc rollout (README/setup/distribution guides), reconciled roadmap/testing docs to de-scope npm blockers, and re-ran full verification protocol (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`) with green results (`615 passed`, `3 skipped`).
77. 2026-03-02: Started `DIST-05` rename/migration hardening to make canonical runtime/config identity fully consistent (`google-workspace-mcp-advanced`) while preserving backward compatibility via legacy config-directory fallback; `PLAN.md` updated first to preserve state before compaction.
78. 2026-03-02: Closed `DIST-05` by completing canonical runtime/config naming cleanup (including `core/utils.py`, sync-map defaults, auth store fallback migration), publishing `docs/setup/MIGRATING_FROM_GWS_MCP_ADVANCED.md`, cleaning active docs/tests naming drift, and re-running full verification (`628 passed`, `3 skipped`).
79. 2026-03-03: Advanced `AUTH-01` by closing WS-01.5 and WS-04.1/WS-04.2/WS-04.3 with new parity/env-path/refresh/diagnostics coverage and logging improvements in `auth/google_auth.py`; targeted auth suite and full verification are green (`633 passed`, `3 skipped`), leaving only WS-06.5/WS-06.6 external validation gates.
80. 2026-03-03: Closed `WS-06.5` by validating published runtime installability using `uvx --from google-workspace-mcp-advanced==1.0.1 google-workspace-mcp-advanced --help`; `AUTH-01` is now blocked only by manual MCP-host smoke evidence (`WS-06.6`).
81. 2026-03-03: Advanced auth runtime closeout by executing live probes against `~/.config/google-workspace-mcp-advanced`: `setup_google_auth_clients` and dual-client import are complete, AUTH-R2 fallback is verified live (`auto+stdio` invalid_client -> callback), mismatch hard-fail policy is verified, and a new external blocker was identified (`AUTH-R9`: private OAuth client is deleted in GCP), which blocks OP-74/OP-76 completion until client replacement.
82. 2026-03-03: Resolved `AUTH-R9` by re-importing `private` mapping with valid local MCP client credentials (`684416...`), then re-ran runtime probes to confirm both tenant lanes now route to distinct client IDs (`private` -> `684416...`, `enterprise` -> `499833...`) with `auto+stdio` fallback active; remaining closeout is manual callback completion evidence (OP-76).
83. 2026-03-03: Performed final runtime config sanity check and living-doc sync: `auth_clients.json` now has `selection_mode=mapped_only`, clients `{private, enterprise}`, account/domain mappings for `david@helmus.me` and `david.helmus@hellofresh.com`, and all auth trackers (`PLAN.md`, `STATUS.md`, `TASKS.md`, `AUTH_STABILIZATION_PLAN.md`, `OPENCODE_MCP_MANUAL_TESTING.md`) are aligned to one remaining gate (`OP-74/OP-76` callback completion in OpenCode).
84. 2026-03-03: Ingested OpenCode runtime matrix closeout: OP-74 PASS (private+enterprise routed in one MCP entry with distinct client behavior) and OP-76 PASS (persistence proven by `list_calendars` success without re-auth prompts: private `8` calendars, enterprise `15` calendars). Auth tracks `AUTH-01` and `AUTH-02` are now closed.
85. 2026-03-03: Reproduced `Release PyPI` failure (`22617048674`) and fixed two release-gate type defects in `auth/oauth21_session_store.py` (protocol-compatible `store_session` signature and typed stats aggregation), then revalidated local release gate (`ruff`, `format --check`, `pyright`, `pytest`: `648 passed`, `3 skipped`).
86. 2026-03-03: Dispatched and watched `release-pypi.yml` from `main` after fix (`22618871138`, head `28509fc`); all jobs passed (`verify`, `build`, `publish`), confirming PyPI release lane is healthy on current mainline.
