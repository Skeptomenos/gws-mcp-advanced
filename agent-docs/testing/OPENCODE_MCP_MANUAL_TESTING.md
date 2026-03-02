# OpenCode MCP Manual Testing Guide (Living)

Use this file as the authoritative manual test runbook for MCP validation inside OpenCode.
OpenCode should update this document during testing with status, evidence, findings, and next actions.

## Document Controls
- Status: `ACTIVE`
- Last Updated (UTC): `2026-02-27`
- Canonical Path: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/docs/OPENCODE_MCP_MANUAL_TESTING.md`
- Related Plan: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/PLAN.md`
- Related Status: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/docs/STATUS.md`

## Living Document Rules
1. Append updates; do not erase prior run history.
2. Every test row must have: `Status`, `Evidence`, and `Notes`.
3. Allowed statuses: `PASS`, `FAIL`, `BLOCKED`, `NOT RUN`.
4. Any `FAIL` must be mirrored in `Defect Log`.
5. At run end, update `Session Summary` and `Next Actions`.

## Preflight Gate (Required Every Session)
Run:
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest -q`

Decision policy:
1. If any preflight command fails, set run status to `BLOCKED`.
2. Do not execute mutation tests when preflight fails.
3. You may execute read-only diagnostics only if clearly marked `CAVEAT: preflight failed`.
4. Log failure details in `Defect Log` and `Session Notes`.

Operational steps:
1. Restart OpenCode before MCP testing so latest code is loaded.
2. Confirm `USER_GOOGLE_EMAIL` and OAuth credentials are configured.
3. Confirm OpenCode MCP server `cwd` points at this exact repo path.

## Session Metadata (Fill at Run Start)
Fill with command output where applicable:
- Branch: `git branch --show-current`
- Commit SHA: `git rev-parse --short HEAD`
- OpenCode version: `opencode --version`

| Field | Value |
|---|---|
| Tester |  |
| Date (UTC) |  |
| Branch |  |
| Commit SHA |  |
| OpenCode Version |  |
| Scope |  |
| Preflight Result |  |

## Test Data Setup (Resolve Placeholders First)
Set concrete values before running test matrix:

| Variable | Required | How to Obtain | Value |
|---|---|---|---|
| `TEST_EMAIL` | Yes | Use a controlled recipient account |  |
| `TEST_FILE_ID` | Yes | Create/select a test Drive file |  |
| `TEST_PERMISSION_ID` | Optional | From `get_drive_file_permissions(TEST_FILE_ID)` |  |
| `TEST_THREAD_ID` | Optional | Search recent Gmail thread |  |
| `TEST_DOC_ID` | Optional | Create/select a test Doc |  |
| `TEST_SHEET_ID` | Optional | Create/select a test Sheet |  |
| `TEST_SLIDES_ID` | Optional | Create/select a test Presentation |  |
| `TEST_FORM_ID` | Optional | Create/select a test Form |  |
| `TEST_TASKLIST_ID` | Optional | Create/select a task list |  |

Notes:
1. Replace all placeholders like `<test-file-id>` and `<email>` with resolved values before execution.
2. Prefer isolated test artifacts prefixed with `opencode-manual-`.

## Service Coverage Matrix
Minimum manual coverage target per service for a full run:

| Service | Read Smoke | Dry-Run Mutation | Explicit Mutation (`dry_run=false`) | Error Path |
|---|---|---|---|---|
| Calendar | Required | Required | Required | Required |
| Drive (files) | Required | Required | Required | Required |
| Drive (permissions) | Required | Required | Required | Required |
| Gmail | Required | Required | Required | Required |
| Docs | Required | Required | Required | Required |
| Sheets | Required | Required | Required | Required |
| Slides | Required | Required | Required | Required |
| Forms | Required | Required | Required | Required |
| Tasks | Required | Required | Required | Required |
| Search | Required | N/A | N/A | Required |
| Chat | Required | Required | Optional | Required |

## Core Test Matrix
Run in order unless blocked.

| ID | Area | Prompt / Action | Expected Result | Status | Evidence | Notes |
|---|---|---|---|---|---|---|
| OP-01 | Discovery | Ask OpenCode to list MCP tools for `gws-mcp-advanced`. | Tool registry returns without transport/auth errors. | NOT RUN |  |  |
| OP-02 | Calendar Read | “List my calendars.” | Valid `list_calendars` response. | NOT RUN |  |  |
| OP-03 | Calendar Read | “Get events from my primary calendar for next 7 days.” | Valid `get_events` response. | NOT RUN |  |  |
| OP-04 | Gmail Read | “Search Gmail for messages from last 7 days.” | Read tool response with message/thread references. | NOT RUN |  |  |
| OP-05 | Drive Read | “List Drive items from root with max 10.” | Read tool response with item metadata. | NOT RUN |  |  |
| OP-06 | Search Read | “Run Google custom search for ‘OpenAI MCP’ with top 3 results.” | Read tool response with search results. | NOT RUN |  |  |
| OP-07 | Dry-Run Calendar | “Create a calendar event tomorrow 10am titled ‘opencode-manual-calendar’ using defaults.” | Response starts with `DRY RUN:`. | NOT RUN |  |  |
| OP-08 | Dry-Run Drive File | “Create Drive text file `opencode-manual-file.txt` with content ‘hello’.” | Response starts with `DRY RUN:`. | NOT RUN |  |  |
| OP-09 | Dry-Run Drive Permission | “Share file `TEST_FILE_ID` with `TEST_EMAIL` as reader.” | Response starts with `DRY RUN:`. | NOT RUN |  |  |
| OP-10 | Dry-Run Gmail | “Draft Gmail to `TEST_EMAIL` with subject ‘opencode dry-run test’ body ‘test’.” | Response starts with `DRY RUN:`. | NOT RUN |  |  |
| OP-11 | Explicit Calendar | Repeat OP-07 with `dry_run=false`. | Event created; response includes ID/link. | NOT RUN |  |  |
| OP-12 | Explicit Drive File | Repeat OP-08 with `dry_run=false`. | File created; response includes ID/link. | NOT RUN |  |  |
| OP-13 | Explicit Drive Permission | Repeat OP-09 with `dry_run=false`. | Permission created with details. | NOT RUN |  |  |
| OP-14 | Regression | “Get Gmail thread content for `TEST_THREAD_ID`.” | Thread tool runs cleanly; no auth/decorator regressions. | NOT RUN |  |  |

## Cross-Service Extended Matrix
Run for full product coverage.

| ID | Area | Prompt / Action | Expected Result | Status | Evidence | Notes |
|---|---|---|---|---|---|---|
| EX-01 | Docs | Create doc via markdown with code block/table/checklist/image. | Output formatting is stable. | NOT RUN |  |  |
| EX-02 | Sheets | Create spreadsheet/sheet then update one range (`dry_run` then execute). | Dry-run safe by default; explicit mutation works. | NOT RUN |  |  |
| EX-03 | Slides | Create presentation (`dry_run` then execute). | Dry-run safe by default; explicit mutation works. | NOT RUN |  |  |
| EX-04 | Forms | Create form (`dry_run` then execute). | Dry-run safe by default; explicit mutation works. | NOT RUN |  |  |
| EX-05 | Tasks | Create task list/task (`dry_run` then execute). | Dry-run safe by default; explicit mutation works. | NOT RUN |  |  |
| EX-06 | Chat | Send chat message (`dry_run` then execute if allowed). | Dry-run safe by default; explicit mutation behavior validated. | NOT RUN |  |  |

## Error-Path Matrix (Required)
Use intentionally invalid inputs and verify graceful errors.

| ID | Area | Action | Expected Result | Status | Evidence | Notes |
|---|---|---|---|---|---|---|
| ER-01 | Invalid ID | Use clearly invalid Drive file ID in read call. | User-safe error, no crash. | NOT RUN |  |  |
| ER-02 | Missing Permission | Attempt restricted tool without required auth/scope. | Clear authorization/scopes message. | NOT RUN |  |  |
| ER-03 | Validation | Call mutation tool missing required field(s). | Clear validation error message. | NOT RUN |  |  |
| ER-04 | Not Found | Use invalid calendar event ID for update/delete. | Clear not-found or API error. | NOT RUN |  |  |
| ER-05 | Quota/Rate | Simulate rapid repeated reads (bounded). | Graceful API error handling/retry behavior. | NOT RUN |  |  |
| ER-06 | Transport | Stop MCP process mid-run and retry a tool call. | OpenCode reports transport failure clearly. | NOT RUN |  |  |

## Defect Log
| Defect ID | Test ID | Severity | Summary | Repro Prompt | Actual Result | Expected Result | Status |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  | Open |

## Session Notes (Append-Only)
- `2026-02-27T00:00:00Z` - Template initialized.

## Session Summary
- Overall Result: `NOT COMPLETE`
- Preflight Gate: `NOT RUN`
- Pass Count: `0`
- Fail Count: `0`
- Blocked Count: `0`
- Key Findings: `TBD`

## Next Actions
1. Re-run failed/blocked tests after fixes.
2. Update `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/PLAN.md`, `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/TASKS.md`, and `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/docs/STATUS.md` with outcomes.
3. Keep this file current as the source of truth for manual OpenCode MCP runs.
