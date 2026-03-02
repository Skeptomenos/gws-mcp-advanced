# Execution Task Board

This file is the local task system for implementation.
Use this instead of external tickets.

Canonical plan: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`
Status dashboard: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/STATUS.md`
Dry-run tracker: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/DRY_RUN_MATRIX.md`

## Metadata
- Last Updated (UTC): 2026-03-02T11:54:53Z
- Active Branch: `codex/run-01-fastmcp-import-smoke`
- Owner: Codex

## Status Legend
- `Not Started`
- `In Progress`
- `Blocked`
- `Done`

## Status Discipline
1. If task status is ambiguous across docs, verify code truth first (actual signatures/behavior/tests/scripts) before updating status fields.

## Master Queue

| ID | Wave | Status | Next Action |
|---|---|---|---|
| SEC-01 | 1 | Done | Completed: default-deny unverified JWT identity, break-glass env override, and guardrail tests |
| RUN-01 | 1 | Done | Completed: import path fixed and CI startup smoke added |
| SEC-02 | 1 | Done | Completed: centralized secure atomic persistence + permission enforcement + tests |
| CONV-01 | 1 | Done | Completed: decorator order normalized, static checker added, CI gate + tests added |
| SAFE-01 | 2 | Done | Completed: all mutator modules now have runtime dry-run coverage (including `gcalendar`, `gmail/messages`, and `gdrive/sync_tools` verified-existing mutators) |
| QUAL-01 | 2 | Done | Completed: source-scoped pyright config is in place, pyright is blocking in CI, and baseline is zero |
| QUAL-02 | 2 | Done | Completed: OpenCode matrix closed with Chat rows passing (`OP-21/22`, `EX-06`); only `OP-06` remains intentionally deferred by product decision |
| RM-01 | 3 | Done | Completed: code block shading/border/language-label behavior landed with unit/integration coverage and OpenCode visual validation (`OP-68` PASS) |
| RM-02 | 3 | Done | Completed: parser/table manager reliability fixes validated by deterministic integration tests + OpenCode matrix; roadmap/testing docs reconciled |
| RM-03 | 3 | Done | Completed: list bullet range excludes trailing list-closing newline; regression tests added to prevent empty post-list bullet artifacts |
| RM-04 | 3 | Done | Completed: OP-69 PASS in OpenCode run 4; DEF-012 fixed and closed |
| RM-05 | 7 | Not Started | Future extension: add native checklist bullet mode for markdown task lists (`BULLET_CHECKBOX`) with Unicode fallback |
| RM-06 | 7 | Not Started | Future extension: add markdown mention-to-person-chip mapping (`InsertPersonRequest`) with graceful fallback |
| RM-07 | 7 | Not Started | Future extension: evaluate/add Workspace Add-ons smart-chip path (`workspace.linkpreview` / `workspace.linkcreate`) |
| GATE-01 | 3/6 | Done | Completed: OP-70 PASS (Attempt 5), kitchen-sink rendering gate cleared, merge/push no longer blocked by markdown rendering |
| DOC-01 | 0/3 | Done | Completed: roadmap/testing docs reconciled; historical reports marked archived snapshots |
| OPC-01 | 4 | Done | Completed: real OpenCode lifecycle smoke is operational (`serve` spawn, health check, attached prompt, deterministic teardown) |
| DIST-00 | 5 | Done | Completed: canonical npm identity standardized; distribution guard enforced in CI + release workflows |
| DIST-01 | 5 | In Progress | PyPI/npm workflows and PyPI-first gating implemented; pending first live publish run validation |
| DIST-02 | 5 | Done | Completed: launcher preflight/remediation and automated launcher smoke tests added |
| DIST-03 | 6 | Done | Completed: pinned install and rollback runbook documented |
| DIST-04 | 5 | In Progress | OIDC/provenance wiring implemented in release workflows; pending external trusted-publisher config + live validation |

## Wave 0 Tasks

- [x] Fix formatter drift in `gcalendar/calendar_tools.py`
- [x] Add `agent-docs/roadmap/STATUS.md`
- [x] Add `agent-docs/roadmap/DRY_RUN_MATRIX.md`
- [x] Add local task system in this file (`TASKS.md`)
- [x] Reconcile stale roadmap/testing docs (`DOC-01`) (`ROADMAP.md`, `TESTING_PLAN_MARKDOWN.md`, legacy reports)

## Wave 1 Tasks (Security + Runtime)

### SEC-01
- [x] Map all identity sources in auth middleware/session store
- [x] Block unverified JWT identity claims by default
- [x] Add `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT=false` compatibility switch
- [x] Add negative tests for forged/unsigned identity tokens
- [x] Add positive tests for verified provider token path
- [x] Update `PLAN.md` + `agent-docs/roadmap/STATUS.md` evidence rows

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
- [x] Implement Wave 2A dry-run defaults (high-risk mutators)
- [x] Implement Wave 2A dry-run defaults for `gcalendar/calendar_tools.py` (`create_event`, `modify_event`, `delete_event`)
- [x] Implement Wave 2A dry-run defaults for `gdrive/files.py` (`create_drive_file`, `update_drive_file`)
- [x] Implement Wave 2A dry-run defaults for `gdrive/permissions.py` (`share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership`)
- [x] Implement dry-run defaults for `gmail/messages.py` (`send_gmail_message`, `draft_gmail_message`)
- [x] Implement dry-run defaults for full `gsheets/sheets_tools.py` mutator set (`modify_sheet_values`, `format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, `create_spreadsheet`, `create_sheet`)
- [x] Implement dry-run defaults for `gslides/slides_tools.py` (`create_presentation`, `batch_update_presentation`)
- [x] Implement dry-run defaults for `gforms/forms_tools.py` (`create_form`, `set_publish_settings`)
- [x] Implement dry-run defaults for `gtasks/tasks_tools.py` (`create_task_list`, `update_task_list`, `delete_task_list`, `create_task`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks`)
- [x] Implement dry-run defaults for `gchat/chat_tools.py` (`send_message`)
- [x] Implement dry-run defaults for `gmail/labels.py` (`manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels`)
- [x] Implement dry-run defaults for `gmail/filters.py` (`create_gmail_filter`, `delete_gmail_filter`)
- [x] Implement dry-run defaults for `gdrive/sync_tools.py` Wave 2B mutators (`link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs`)
- [x] Implement dry-run defaults for full `gdocs/writing.py` mutator set (`create_doc`, `modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown`)
- [x] Implement dry-run defaults for `gdocs/elements.py` (`insert_doc_elements`, `insert_doc_image`)
- [x] Implement dry-run defaults for `gdocs/tables.py` (`create_table_with_data`)
- [x] Implement Wave 2B dry-run defaults (remaining mutators)
- [x] Add `scripts/check_dry_run_defaults.py`
- [x] Add module-level dry-run tests for `gslides/slides_tools.py` (`dry_run=True` skip + `dry_run=False` mutation path)
- [x] Add module-level dry-run tests for `gforms/forms_tools.py` (`dry_run=True` skip + `dry_run=False` mutation path)
- [x] Add module-level dry-run tests for `gtasks/tasks_tools.py` (`dry_run=True` skip + `dry_run=False` mutation paths across all mutators)
- [x] Add module-level dry-run tests for `gchat/chat_tools.py` (`dry_run=True` skip + `dry_run=False` mutation path)
- [x] Add module-level dry-run tests for `gmail/labels.py` (`manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels` dry-run + `dry_run=False` mutation paths)
- [x] Add module-level dry-run tests for `gdocs/writing.py` (`modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown`)
- [x] Add module-level dry-run tests for `gdocs/elements.py` (`insert_doc_elements`, `insert_doc_image`)
- [x] Add module-level dry-run tests for `gdocs/tables.py` (`create_table_with_data`)
- [x] Add module-level dry-run tests for `gdrive/sync_tools.py` Wave 2B mutators (`link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs`)
- [x] Add module-level dry-run tests per service
- [x] Update `agent-docs/roadmap/DRY_RUN_MATRIX.md` row statuses and readiness snapshot
- [x] Update `PLAN.md` evidence rows

### QUAL-01
- [x] Add blocking startup smoke checks in CI
- [x] Add blocking static safety checks in CI
- [x] Keep formatter gate in check mode only
- [x] Define incremental type-check promotion plan
- [x] Add source-scoped `pyrightconfig.json` and promote pyright to blocking CI gate

### QUAL-02
- [x] Execute OpenCode manual matrix and capture defects/evidence (session summary: `11 defects found, 11 fixed`; env/manual blockers remain)
- [x] Document roadmap deferral for `OP-06` / PSE env setup (non-blocking while web search is covered by other MCPs)
- [x] Add protocol lane tests in `tests/mcp_protocol/`
- [x] Add targeted auth/session regression coverage
- [x] Add live MCP lane scaffolding in `tests/live_mcp/`
- [x] Add OpenCode automated lane scaffolding in `tests/opencode/` + `scripts/opencode_*`
- [x] Update verification protocol in docs
- [x] Implement live OpenCode lifecycle smoke (`scripts/opencode_serve_smoke.sh`, `scripts/opencode_sdk_smoke.mjs --live`) with deterministic teardown

## Wave 3 Tasks (Roadmap Closure)

### RM-01
- [x] Implement code block shading/border/language label behavior
- [x] Add unit + integration coverage
- [x] Validate against kitchen-sink scenarios

### RM-02
- [x] Reproduce table reliability failures in deterministic/manual runs
- [x] Apply table-manager fallback style fix path (2-phase population + table targeting + fail-fast on incomplete population)
- [x] Add parser-level regression coverage for multi-table ordering
- [x] Add deterministic e2e proof case for multi-table markdown create flow
- [x] Close roadmap/spec docs with evidence references

### RM-03
- [x] Reproduce extra empty bullet after task lists
- [x] Implement bullet reset correction
- [x] Add regression tests for list transitions
- [x] Validate live OpenCode regression `OP-67` (no extra empty bullet between task list and following heading/paragraph)

### RM-04
- [x] Add deterministic image insertion verification tests
- [x] Validate structure assertions and non-regression behavior
- [x] Implement DEF-012 fix for markdown image insertion path
- [x] Implement DEF-012 phase-2 fix in `create_doc` (separate image batchUpdate)
- [x] Validate live OpenCode regression `OP-69` (image rendering + ordering in created docs)

### GATE-01 (Pre-Merge Rendering Gate)
- [x] Execute OpenCode `OP-70` using `tests/manual/kitchen_sink.md` and capture per-section visual checklist evidence
- [x] Confirm cleanup (kitchen-sink artifact trashed) and update runbook counters/status
- [x] Keep merge/push blocked until `OP-70` is marked `PASS`

## Wave 7 Tasks (Smart-Chip Extensions)

### RM-05
- [ ] Add parser/tool mode for native checklist bullets using `createParagraphBullets` + `BULLET_CHECKBOX`
- [ ] Preserve explicit Unicode checkbox fallback mode for deterministic markdown parity
- [ ] Add regression coverage for checklist mode switching and list-boundary behavior
- [ ] Add OpenCode manual validation rows for `native_checklist` and `unicode_fallback`

### RM-06
- [ ] Define mention syntax contract for markdown (`@user@example.com`) under opt-in parse mode
- [ ] Implement mention token handling to emit `InsertPersonRequest`
- [ ] Add fallback behavior and explicit warning path for unresolved mentions
- [ ] Add unit/integration/manual validation for mention chips and mixed markdown blocks

### RM-07
- [ ] Write feasibility/spec doc for Add-ons-based smart chips (`workspace.linkpreview` / `workspace.linkcreate`)
- [ ] Define architecture boundary between MCP Docs API path and Add-ons chip path
- [ ] Define auth/scope/deployment requirements and risk register for enterprise rollout
- [ ] Add go/no-go decision checkpoint with success criteria and estimated implementation budget

### DOC-01
- [x] Reconcile `ROADMAP.md` with current implementation reality
- [x] Reconcile `TESTING_PLAN_MARKDOWN.md` open/closed states
- [x] Mark stale reports as archived snapshots where appropriate
- [x] Keep `agent-docs/roadmap/STATUS.md` synchronized with actual state

## Wave 4 Tasks (Autonomous MCP Verification)

- [x] Add `tests/mcp_protocol/test_stdio_handshake.py`
- [x] Add `tests/mcp_protocol/test_tool_registry_contract.py`
- [x] Add `tests/live_mcp/conftest.py`
- [x] Add `tests/live_mcp/helpers.py`
- [x] Add `tests/live_mcp/test_live_smoke.py`
- [x] Add `tests/live_mcp/test_markdown_features.py`
- [ ] Add `scripts/mcp_live_cleanup.py`
- [x] Add `agent-docs/testing/MCP_AUTONOMOUS_TESTING.md`
- [x] Validate OpenCode lifecycle wrapper lane (`tests/opencode/*`, including live opt-in execution path)

## Wave 5-6 Tasks (Distribution)

### DIST-00
- [x] Standardize package name to `google-workspace-mcp-advanced` across npm metadata and README distribution examples
- [x] Add guard checks in release workflow

### DIST-01
- [x] Add PyPI publish workflow
- [x] Add npm publish workflow
- [x] Block npm publish until matching PyPI version exists
- [x] Add version-coupling check (`pyproject.toml` vs `package.json`) and enforce in CI
- [ ] Ensure `.github/workflows/release-pypi.yml` is committed and present on `main` (required for `workflow_dispatch`)
- [ ] Ensure `.github/workflows/release-npm.yml` is committed and present on `main` (required for `workflow_dispatch`)
- [ ] Re-run `DT-01`..`DT-03` after workflow files are visible on default branch

### DIST-02
- [x] Implement npm launcher preflight for `uvx`/`uv`
- [x] Add clear failure remediation text
- [x] Add launcher smoke tests

### DIST-03
- [x] Add pinned install examples (`@x.y.z`) in docs
- [x] Add rollback guidance for dist-tags

### DIST-04
- [x] Configure trusted publishing (OIDC) in release workflow permissions for PyPI and npm
- [x] Enable npm provenance publish command (`npm publish --provenance`)
- [ ] Verify release metadata checks in CI
- [ ] Complete external trusted publisher setup in PyPI and npm project settings

## Verification Commands

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest -q`
- `uv run pytest -m mcp_protocol tests/mcp_protocol`
- `uv run pytest -m "live_mcp and live_write" tests/live_mcp`
- `uv run python scripts/check_distribution_scope.py`
- `uv run python scripts/check_release_version_match.py`

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
- 2026-02-27: Readiness pass reconciled status drift across `PLAN.md`, `agent-docs/roadmap/DRY_RUN_MATRIX.md`, `TASKS.md`, and `agent-docs/roadmap/STATUS.md`; kept `SAFE-01`/`QUAL-02` open until full closure criteria are met.
- 2026-02-27: Code-truth audit completed for dry-run inventory (function signatures + `dry_run` behavior markers + script presence); used findings to correct task/status claims.
- 2026-02-27: Implemented `scripts/check_dry_run_defaults.py`, added unit tests (`tests/unit/core/test_dry_run_defaults_checker.py`), and wired the checker into CI lint gates.
- 2026-02-27: Extended `SAFE-01` rollout in `gslides/slides_tools.py` by adding `dry_run=True` default for `batch_update_presentation`, added dedicated slides dry-run runtime tests, and re-ran full verification (`495 passed`).
- 2026-02-27: Extended `SAFE-01` rollout in `gforms/forms_tools.py` by adding `dry_run=True` default for `set_publish_settings`, added dedicated forms dry-run runtime tests, and re-ran full verification (`499 passed`).
- 2026-02-27: Extended `SAFE-01` rollout in `gtasks/tasks_tools.py` by adding `dry_run=True` default for `update_task_list`, added dedicated tasks dry-run runtime tests for task-list mutators, and re-ran full verification (`503 passed`).
- 2026-02-27: Extended `SAFE-01` rollout in `gchat/chat_tools.py` by adding `dry_run=True` default for `send_message`, added dedicated chat dry-run runtime tests, and re-ran full verification (`505 passed`).
- 2026-02-27: Extended `SAFE-01` rollout in `gmail/labels.py` by adding `dry_run=True` default for `manage_gmail_label`, added dedicated Gmail label dry-run runtime tests, and re-ran full verification (`509 passed`).
- 2026-02-27: Extended `SAFE-01` rollout in `gmail/labels.py` by adding `dry_run=True` default for `modify_gmail_message_labels`, added dedicated Gmail message-label dry-run runtime tests, and re-ran full verification (`511 passed`).
- 2026-02-27: Extended `SAFE-01` rollout in `gmail/labels.py` by adding `dry_run=True` default for `batch_modify_gmail_message_labels`, added dedicated Gmail batch message-label dry-run runtime tests, and re-ran full verification (`513 passed`).
- 2026-02-28: Extended `SAFE-01` rollout in `gdocs/writing.py` by adding `dry_run=True` defaults for `modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, and `insert_markdown`, added dedicated runtime tests, expanded static checker coverage, and re-ran full verification (`523 passed`).
- 2026-02-28: Added integration regression coverage for table-with-preceding-content and multi-table create flow in `tests/integration/test_create_doc_table_population_flow.py` (including fail-fast incomplete population assertion), and re-ran full verification (`526 passed`).
- 2026-02-28: Extended `SAFE-01` rollout in Docs element/table mutators by adding `dry_run=True` defaults for `insert_doc_elements`, `insert_doc_image`, and `create_table_with_data`, adding dedicated runtime tests, expanding static checker coverage, and re-running full verification (`532 passed`).
- 2026-02-28: Extended `SAFE-01` rollout in remaining Tasks mutators by adding `dry_run=True` defaults for `delete_task_list`, `update_task`, `delete_task`, `move_task`, and `clear_completed_tasks`, adding full Tasks mutator runtime tests, expanding static checker coverage, and re-running full verification (`542 passed`).
- 2026-02-28: Extended `SAFE-01` rollout in `gdocs/writing.py` by adding `dry_run=True` default and deterministic preview for `create_doc`, updated create-doc integration tests to explicit `dry_run=False`, expanded static checker coverage, and re-ran full verification (`544 passed`).
- 2026-02-28: Extended `SAFE-01` rollout in remaining `gsheets/sheets_tools.py` mutators by adding `dry_run=True` defaults for `format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, and `create_sheet`, adding dedicated runtime tests, expanding static checker coverage, and re-running full verification (`554 passed`).
- 2026-02-28: Extended `SAFE-01` rollout in `gdrive/sync_tools.py` Wave 2B mutators by adding `dry_run=True` defaults for `link_local_file`, `upload_folder`, `mirror_drive_folder`, and `download_doc_tabs`, adding dedicated runtime tests, expanding static checker coverage (including `update_google_doc` and `download_google_doc`), and re-running full verification (`562 passed`).
- 2026-02-28: OpenCode executed OP-59..66 for Drive sync mutators. Initial run surfaced DEF-010 (mirror name-resolution failure) and DEF-011 (invalid `drive_write` scope key); both fixes were implemented and re-verified in follow-up run. Final OP-59..66 status is PASS with artifact cleanup completed.
- 2026-02-28: Reconciled tracker drift after OP-59..66 completion: removed stale “handoff pending” language and kept SAFE-01 open only for genuine residual runtime-test gaps (`gcalendar`, `gmail/messages`, `gdrive/sync_tools` verified-existing mutators).
- 2026-02-28: Added isolated runtime dry-run tests for `gmail/messages.py` and `gdrive/sync_tools.py` verified-existing mutators (`update_google_doc`, `download_google_doc`), and confirmed targeted + full verification remained green.
- 2026-02-28: Added isolated runtime dry-run harness tests for `gcalendar` mutators (`create_event`, `modify_event`, `delete_event`) and re-ran full verification (`576 passed`), closing `SAFE-01`.
- 2026-02-28: Documented roadmap deferral for `OP-06` / PSE-backed `search_custom` setup (non-blocking for current waves because web search is covered by other MCPs).
- 2026-02-28: Closed `QUAL-01` by adding `pyrightconfig.json`, reducing source pyright errors to zero, and promoting pyright to a blocking CI gate; added protocol/live/opencode automated lane scaffolding for `QUAL-02`/`OPC-01` and validated targeted lane tests (`5 passed, 2 skipped`) plus full verification (`581 passed, 2 skipped`).
- 2026-02-28: Closed `OPC-01` by implementing and validating real `opencode serve` lifecycle smoke (`serve` spawn, `/global/health`, attached prompt, deterministic teardown), adding live opt-in pytest coverage, and re-running full verification (`581 passed, 3 skipped`).
- 2026-02-28: Ingested OpenCode ER-06 result (`PASS`) from manual guide; error-path matrix is now fully complete (`ER-01..06 = 6/6 PASS`) and QUAL-02 residual scope is now limited to targeted auth/session runtime coverage plus Chat env blockers.
- 2026-02-28: Completed targeted auth/session runtime coverage by adding `tests/unit/auth/test_auth_runtime_paths.py` (middleware stdio/session-binding and token-bridge paths), validated targeted suite (`7 passed`), and re-ran full verification (`588 passed, 3 skipped`).
- 2026-02-28: Reconciled tracker docs after final Chat validation (`OP-21`, `OP-22`, `EX-06` all PASS) and closed `QUAL-02` to `Done`; `OP-06` remains deferred by product decision and is not a wave blocker.
- 2026-02-28: Closed `RM-03` by updating `gdocs/markdown_parser.py` to exclude trailing list-closing newline from `createParagraphBullets` range, added regression coverage in `tests/unit/gdocs/test_markdown_parser.py`, and re-ran full verification (`590 passed, 3 skipped`).
- 2026-03-01: Ingested OpenCode `OP-67` live regression result (`PASS`) and synced tracker truth (`78 PASS`, `0 FAIL`, `1 BLOCKED`, `0 NOT RUN`); `RM-03` is fully closed in both code and manual-live validation.
- 2026-03-01: Advanced `RM-01` by implementing parser-level code block paragraph box styling (shading + 4 borders) and fenced language label rendering, adding parser unit coverage + create_doc integration coverage, and re-running full verification (`593 passed, 3 skipped`). Pending manual visual check in OpenCode (`OP-68`).
- 2026-03-01: Advanced `RM-04` by adding deterministic create-doc integration coverage for markdown image insertion flows (single image with surrounding text + multi-image ordering), re-running full verification (`595 passed, 3 skipped`), and preparing OpenCode visual handoff row `OP-69`.
- 2026-03-01: Ingested OpenCode OP-68/OP-69 outcomes (`OP-68 PASS`, `OP-69 FAIL`) and logged DEF-012 (`create_doc` markdown image insertion missing inline objects).
- 2026-03-01: Implemented DEF-012 fix in `gdocs/markdown_parser.py` using placeholder replacement (`deleteContentRange` + `insertInlineImage`), added unit/integration regressions, and re-ran full verification (`596 passed, 3 skipped`). Pending OP-69 rerun for live closure.
- 2026-03-01: Implemented DEF-012 phase-2 remediation in `gdocs/writing.py` by splitting markdown image replacement into a dedicated second `batchUpdate` in `create_doc` (before table population), added split-phase ordering regressions in unit/integration tests, and re-ran full verification (`598 passed, 3 skipped`).
- 2026-03-01: Ingested OpenCode OP-69 run 4 (`PASS`) and closed `RM-04`/`DEF-012`; updated roadmap/testing status artifacts to reflect Wave 3 closure.
- 2026-03-01: Closed `DOC-01` by reconciling `ROADMAP.md` and `TESTING_PLAN_MARKDOWN.md` to current execution truth and marking `TEST_RESULTS.md`/`ISSUE_REPORT.md` as archived snapshots.
- 2026-03-01: Started distribution wave by adding canonical npm launcher package (`package.json`, `bin/google-workspace-mcp-advanced.cjs`), adding distribution/version CI guard scripts, and wiring them into `.github/workflows/ci.yml`.
- 2026-03-01: Fixed a pyright type regression in `gdocs/markdown_parser.py` (`_pending_inline_images` now only receives `str` image URIs), then re-ran full verification (`ruff`, `pyright`, `pytest`: `598 passed, 3 skipped`).
- 2026-03-01: Added release workflows (`release-pypi.yml`, `release-npm.yml`) with PyPI->npm ordering, PyPI-version existence gating, and OIDC/provenance publish configuration; added distribution runbook (`docs/DISTRIBUTION_RELEASE.md`) and launcher smoke tests (`tests/unit/core/test_npm_launcher.py`, `tests/unit/core/test_distribution_checks.py`) and wired launcher smoke lane into CI.
- 2026-03-01: Re-ran full verification after distribution automation/test additions (`ruff`, `pyright`, `pytest`): `606 passed, 3 skipped`, all static guard scripts green.
- 2026-03-01: Prepared next distribution test-phase matrix in `agent-docs/testing/DISTRIBUTION_TEST_PHASE.md` with release, channel, and rollback validation rows (`DT-01`..`DT-08`) for execution handoff.
- 2026-03-01: Added pre-merge rendering gate `GATE-01` with OpenCode `OP-70` (kitchen-sink markdown fixture) as mandatory PASS evidence before merge/push.
- 2026-03-02: Implemented `DEF-013` mitigation in shared markdown pipeline: table placeholder replacement (no post-table cursor prediction), centralized structural request partitioning used by both `create_doc` and `insert_markdown`, and task-list no-bullet behavior to prevent checkbox double markers. Added regressions and re-ran full verification (`609 passed, 3 skipped`). Pending OP-70 rerun.
- 2026-03-02: Implemented `DEF-013` attempt 3 fix for TAB-removal index drift in placeholder replacement (image/table indices now compensate for `createParagraphBullets` TAB deletions), added targeted tab-shift regressions, and re-ran full verification (`611 passed, 3 skipped`). Pending OP-70 rerun.
- 2026-03-02: Implemented DEF-013 nuance-fix patchset for Attempt-4 residuals: source-map blank-line preservation for top-level blocks, explicit table placeholder paragraph termination, and enforced table-cell baseline style (`fontSize=11`, header-only bold) in `TableOperationManager`. Added parser regressions for heading/HR spacing + table separation + post-table strikethrough range and re-ran full verification (`615 passed, 3 skipped`). Pending OP-70 rerun.
- 2026-03-02: Ingested OpenCode `OP-70` Attempt 5 result (`PASS`) and closed `GATE-01` (kitchen-sink full-rendering pre-merge gate). Merge/push is no longer blocked by markdown rendering quality.
- 2026-03-02: Added smart-chip roadmap wave tasks (`RM-05`, `RM-06`, `RM-07`) to track native checklist bullets, person-chip mentions, and add-ons-based third-party chip feasibility.
- 2026-03-02: Attempted live release dispatch (`gh workflow run release-pypi.yml --ref codex/run-01-fastmcp-import-smoke`); GitHub returned `HTTP 404` because release workflows are not present on default branch (`main`) yet. Distribution validation remains blocked pending merge to `main`.
- 2026-03-02: Re-validated distribution blockers against `main` after merge (`a39b34f`): `gh workflow list` still shows only `CI`, `DT-01..DT-03` fail with workflow 404 on default branch, and `DT-07` remains blocked (`npm view google-workspace-mcp-advanced` -> `E404`).
