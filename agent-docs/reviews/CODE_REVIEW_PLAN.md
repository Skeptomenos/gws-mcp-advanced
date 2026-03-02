# Code Review Plan (Living)

Use this file as the persistent tracker for the post-test code review.
Update it during the review so findings and progress survive context compaction.

## Document Controls
- Status: `READY`
- Last Updated (UTC): `2026-02-27`
- Reviewer: `Codex`
- Branch: `codex/run-01-fastmcp-import-smoke`
- Scope: DEF-001..DEF-006 outcome validation + regression risk review

## Review Objectives
1. Verify code changes match manual test outcomes.
2. Validate no regressions were introduced in auth, dry-run safety, and markdown flows.
3. Capture actionable findings with severity, file references, and mitigation.

## Checklist (Update In-Place)
- [x] CR-01 Collect scope and changed files
  - Notes: Review scope set to uncommitted post-manual-test fixes in `auth/credential_types/store.py`, `gmail/messages.py`, `gsheets/sheets_tools.py`, `gslides/slides_tools.py`, `gforms/forms_tools.py`, `gtasks/tasks_tools.py`, `gdocs/markdown_parser.py`, `gdocs/writing.py`, `tests/unit/gdocs/test_markdown_parser.py`, and planning docs (`PLAN.md`, `agent-docs/roadmap/STATUS.md`, `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`).
  - Findings: None at scope collection stage.
- [x] CR-02 Re-run verification protocol (`ruff`, format check, full `pytest`)
  - Notes: Re-run after mitigation changes. `uv run ruff check .` passed, `uv run ruff format . --check` passed (`118 files already formatted`), `uv run pytest -q` passed (`487 passed`).
  - Findings: None.
- [x] CR-03 Review auth/credential path fixes (DEF-001, DEF-002)
  - Notes: `auth/credential_types/store.py` now sources base credential directory via `get_credentials_directory()` from `auth.config`, aligning file-store lookup with auth fallback path and `WORKSPACE_MCP_CONFIG_DIR`.
  - Findings: None.
- [x] CR-04 Review dry-run guard rollout consistency (DEF-004, DEF-006)
  - Notes: Dry-run defaults and deterministic previews confirmed in reviewed mutators: Gmail (`send_gmail_message`, `draft_gmail_message`), Sheets (`modify_sheet_values`, `create_spreadsheet`), Slides (`create_presentation`), Forms (`create_form`), Tasks (`create_task_list`, `create_task`).
  - Findings: None.
- [x] CR-05 Review markdown table 2-phase insertion flow (DEF-005)
  - Notes: Two-phase flow now includes deterministic table targeting (`table_index` propagation) and parser-level ordering coverage for multiple tables.
  - Findings: F-001 (mitigated).
- [x] CR-06 Review error handling and user-safe failure behavior
  - Notes: `create_doc` now surfaces phase-2 table population shortfalls by raising runtime error with per-table counts instead of silently warning.
  - Findings: F-002 (mitigated).
- [x] CR-07 Validate blocked/not-run manual cases are dispositioned (`EX-06`, `ER-06`)
  - Notes: Manual-test counters and status roll-ups were reconciled across `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md` and `agent-docs/roadmap/STATUS.md` (`OP-06` now classified as environment-blocked; wave summary counts aligned).
  - Findings: F-003 (mitigated).
- [x] CR-08 Summarize review verdict and required follow-ups
  - Notes: All identified findings have concrete mitigations applied and re-verified with full lint/format/test protocol.
  - Findings: None open.

## Findings Register
| ID | Severity | File | Line | Summary | Recommended Mitigation | Status | Notes |
|---|---|---|---|---|---|---|---|
| F-001 | P1 | gdocs/writing.py; gdocs/managers/table_operation_manager.py | writing.py:97; table_operation_manager.py:174 | Multi-table Markdown docs can populate the wrong table because phase-2 population iterates each pending table, but `_populate_single_cell()` always writes to `tables[-1]` (last table). | Added explicit `table_index` plumbing (`create_doc` passes index from `pending_tables`; manager methods target that index) and parser ordering regression coverage for multiple tables. | Mitigated | Verified by full test pass after change (`487 passed`). |
| F-002 | P2 | gdocs/writing.py | 98 | `create_doc` swallows table population exceptions and still returns a success message, which can hide partial data loss (empty or partially populated tables) from users and test automation. | Added explicit failure aggregation and raised runtime error when populated-cell counts do not match expected non-empty cell counts. | Mitigated | Failure now propagates instead of silent warning. |
| F-003 | P3 | agent-docs/roadmap/STATUS.md; agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md | STATUS.md:29; STATUS.md:38; OPENCODE_MCP_MANUAL_TESTING.md:128; OPENCODE_MCP_MANUAL_TESTING.md:204 | Manual-test status reporting was inconsistent (`OP-06` matrix status vs roll-up counts; Wave 2 count mismatch). | Reconciled matrix row status and roll-up counters (`23 PASS`, `0 FAIL`, `2 BLOCKED`, `1 NOT RUN`) and aligned Wave 2/status focus text. | Mitigated | Living docs are now internally consistent for this run snapshot. |

Severity scale:
- `P0`: Critical correctness/security issue
- `P1`: High-risk bug/regression
- `P2`: Medium-risk defect/maintainability risk
- `P3`: Low-risk improvement

Status values:
- `Open`
- `Mitigated`
- `Accepted Risk`

## Compaction Snapshot (Update at Milestones)
- Current Step: `CR-08 Completed`
- Completed Steps: `CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, CR-07`
- Open Findings: `None`
- Blockers: `None`
- Next Step: Keep this review as baseline and continue with Wave 3 roadmap execution.

## Final Review Verdict
- Result: `PASS`
- Merge Recommendation: `YES (review findings mitigated)`
- Required Follow-ups:
  1. Continue Wave 3 roadmap closure execution (`RM-01`..`RM-04`).
