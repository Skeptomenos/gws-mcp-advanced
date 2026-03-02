# Dry Run Rollout Matrix

This matrix tracks implementation progress for `SAFE-01`:
all mutating tools must default to `dry_run: bool = True`.

## Contract
1. Mutating tools must define `dry_run: bool = True`.
2. `dry_run=True` must not perform remote mutations or local file writes.
3. `dry_run=False` executes the existing mutation behavior.
4. Responses must make dry-run behavior explicit and deterministic.

## Status Legend
- `Not Started`: signature/behavior unchanged.
- `In Progress`: partial implementation or partial test coverage.
- `Done`: signature, behavior, and tests complete.
- `Verified Existing`: already default-safe and validated.

## Readiness Snapshot (2026-02-28)
1. `SAFE-01` is **Done**.
2. Default-safe `dry_run=True` rollout is now implemented across all tracked mutator modules, including `gdrive/sync_tools.py`.
3. Static CI guard is implemented and wired: `scripts/check_dry_run_defaults.py`.
4. Runtime closure requirements are complete for all matrix rows (`dry_run=True` skip paths and explicit `dry_run=False` mutation paths).
5. Manual matrix closure is complete for Chat and transport paths; only `OP-06` (PSE search env) remains product-deferred in `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`.

## Module Rollout Board

| Module | Mutating Tools | Rollout Wave | Implementation Status | Test Status | Notes |
|---|---|---|---|---|---|
| `gcalendar/calendar_tools.py` | `create_event`, `modify_event`, `delete_event` | Wave 2A | Done | Done | `dry_run=True` defaults + deterministic previews implemented; isolated runtime dry-run harness now verifies default skip and explicit `dry_run=False` mutation paths |
| `gdrive/files.py` | `create_drive_file`, `update_drive_file` | Wave 2A | Done | Done | `dry_run=True` defaults + deterministic previews implemented; runtime tests verify dry-run skip and explicit `dry_run=False` mutation behavior |
| `gdrive/permissions.py` | `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership` | Wave 2A | Done | Done | `dry_run=True` defaults + deterministic previews implemented; runtime tests verify default dry-run skip and explicit `dry_run=False` mutation behavior across all permission mutators |
| `gdrive/sync_tools.py` | `update_google_doc`, `download_google_doc` | Wave 2A | Verified Existing | Done | Defaults already safe; static dry-run checker coverage plus runtime tests now verify default skip and explicit execution paths |
| `gdrive/sync_tools.py` | `link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs` | Wave 2B | Done | Done | `dry_run=True` defaults + deterministic previews implemented; runtime tests cover dry-run skip and explicit `dry_run=False` paths; manual OP-59..66 verification completed (DEF-010/011 fixed) |
| `gdocs/writing.py` | `create_doc`, `modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown` | Wave 2A | Done | Done | Full writing mutator set now defaults to `dry_run=True`; runtime coverage includes `create_doc` default-safe behavior and explicit `dry_run=False` integration paths |
| `gdocs/elements.py` | `insert_doc_elements`, `insert_doc_image` | Wave 2A | Done | Done | Both mutators now default to `dry_run=True`; runtime tests cover dry-run skip and explicit mutation paths |
| `gdocs/tables.py` | `create_table_with_data` | Wave 2A | Done | Done | Mutator now defaults to `dry_run=True`; runtime tests cover dry-run skip and explicit table-manager path |
| `gsheets/sheets_tools.py` | `modify_sheet_values`, `format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, `create_spreadsheet`, `create_sheet` | Wave 2A | Done | Done | Full mutator set now defaults to `dry_run=True`; runtime tests cover dry-run skip and explicit `dry_run=False` mutation paths for remaining format/conditional/sheet-create mutators |
| `gmail/messages.py` | `send_gmail_message`, `draft_gmail_message` | Wave 2A | Done | Done | Both mutators now default to `dry_run=True`; dedicated runtime tests verify default skip and explicit mutation paths |
| `gmail/labels.py` | `manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels` | Wave 2B | Done | Done | All mutators now default to `dry_run=True`; runtime tests cover default dry-run skip and explicit `dry_run=False` mutation paths |
| `gmail/filters.py` | `create_gmail_filter`, `delete_gmail_filter` | Wave 2B | Done | Done | Both mutators now default to `dry_run=True`; runtime tests + manual OP-23..26 validation confirm dry-run and explicit mutation paths |
| `gtasks/tasks_tools.py` | `create_task_list`, `update_task_list`, `delete_task_list`, `create_task`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks` | Wave 2A | Done | Done | All mutators now default to `dry_run=True`; runtime tests cover dry-run skip and explicit mutation paths across the full Tasks mutator set |
| `gforms/forms_tools.py` | `create_form`, `set_publish_settings` | Wave 2B | Done | Done | Both mutators now default to `dry_run=True`; runtime tests cover default dry-run skip and explicit `dry_run=False` mutation path |
| `gslides/slides_tools.py` | `create_presentation`, `batch_update_presentation` | Wave 2A | Done | Done | Both mutators now default to `dry_run=True`; runtime tests cover default dry-run skip and explicit `dry_run=False` mutation path |
| `gchat/chat_tools.py` | `send_message` | Wave 2B | Done | Done | `send_message` now defaults to `dry_run=True`; runtime tests cover default dry-run skip and explicit `dry_run=False` mutation path |

## Verification Plan
1. Add unit tests for each module that assert default call path does not mutate.
2. Add unit tests that assert `dry_run=False` calls the mutating API method.
3. Add CI static checker (`scripts/check_dry_run_defaults.py`) to prevent regressions.
4. Keep this matrix synchronized with issue `SAFE-01` and `PLAN.md`.

## SAFE-01 Exit Criteria
1. Every row is either `Done` or `Verified Existing` for both implementation and test status.
2. `scripts/check_dry_run_defaults.py` exists and is wired as a blocking CI check.
3. `PLAN.md`, `TASKS.md`, and `agent-docs/roadmap/STATUS.md` all report `SAFE-01` with identical status.

## Update Protocol
1. When a module starts implementation, set `Implementation Status` to `In Progress`.
2. When tests are added for a module, set `Test Status` to `In Progress`.
3. Mark a row `Done` only after implementation + tests + CI checks are green.
4. If status is disputed, use code truth as authority: check function signatures, runtime behavior/tests, and CI/static scripts before updating this table.
