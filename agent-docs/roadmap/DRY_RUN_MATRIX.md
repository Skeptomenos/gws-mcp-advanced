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

## Module Rollout Board

| Module | Mutating Tools | Rollout Wave | Implementation Status | Test Status | Notes |
|---|---|---|---|---|---|
| `gcalendar/calendar_tools.py` | `create_event`, `modify_event`, `delete_event` | Wave 2A | Done | In Progress | `dry_run=True` defaults + deterministic previews implemented; static contract tests added; runtime mutation-path harness still to be expanded |
| `gdrive/files.py` | `create_drive_file`, `update_drive_file` | Wave 2A | Done | Done | `dry_run=True` defaults + deterministic previews implemented; runtime tests verify dry-run skip and explicit `dry_run=False` mutation behavior |
| `gdrive/permissions.py` | `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership` | Wave 2A | Done | Done | `dry_run=True` defaults + deterministic previews implemented; runtime tests verify default dry-run skip and explicit `dry_run=False` mutation behavior across all permission mutators |
| `gdrive/sync_tools.py` | `update_google_doc`, `download_google_doc` | Wave 2A | Verified Existing | Not Started | Already default-safe; validate tests |
| `gdrive/sync_tools.py` | `link_local_file`, `upload_folder`, `mirror_drive_folder`, `download_doc_tabs` | Wave 2B | Not Started | Not Started | Includes local filesystem effects |
| `gdocs/writing.py` | `create_doc`, `modify_doc_text`, `find_and_replace_doc`, `update_doc_headers_footers`, `batch_update_doc`, `insert_markdown` | Wave 2A | Not Started | Not Started | High-frequency mutators |
| `gdocs/elements.py` | `insert_doc_elements`, `insert_doc_image` | Wave 2A | Not Started | Not Started | Docs element mutations |
| `gdocs/tables.py` | `create_table_with_data` | Wave 2A | Not Started | Not Started | Table mutation path |
| `gsheets/sheets_tools.py` | `modify_sheet_values`, `format_sheet_range`, `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`, `create_spreadsheet`, `create_sheet` | Wave 2A | Not Started | Not Started | Broad write surface |
| `gmail/messages.py` | `send_gmail_message`, `draft_gmail_message` | Wave 2A | Not Started | Not Started | Outbound email safeguards |
| `gmail/labels.py` | `manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels` | Wave 2B | Not Started | Not Started | Label mutation |
| `gmail/filters.py` | `create_gmail_filter`, `delete_gmail_filter` | Wave 2B | Not Started | Not Started | Filter lifecycle |
| `gtasks/tasks_tools.py` | `create_task_list`, `update_task_list`, `delete_task_list`, `create_task`, `update_task`, `delete_task`, `move_task`, `clear_completed_tasks` | Wave 2A | Not Started | Not Started | Multiple destructive operations |
| `gforms/forms_tools.py` | `create_form`, `set_publish_settings` | Wave 2B | Not Started | Not Started | Form creation/settings |
| `gslides/slides_tools.py` | `create_presentation`, `batch_update_presentation` | Wave 2A | Not Started | Not Started | Presentation mutation |
| `gchat/chat_tools.py` | `send_message` | Wave 2B | Not Started | Not Started | Outbound message safety |

## Verification Plan
1. Add unit tests for each module that assert default call path does not mutate.
2. Add unit tests that assert `dry_run=False` calls the mutating API method.
3. Add CI static checker (`scripts/check_dry_run_defaults.py`) to prevent regressions.
4. Keep this matrix synchronized with issue `SAFE-01` and `PLAN.md`.

## Update Protocol
1. When a module starts implementation, set `Implementation Status` to `In Progress`.
2. When tests are added for a module, set `Test Status` to `In Progress`.
3. Mark a row `Done` only after implementation + tests + CI checks are green.
