# Implementation Plan

> **Created**: 2026-01-13  
> **Status**: Ready for Ralphus loop  
> **Approach**: Incremental refactoring following existing specs, then enhancements

---

## Executive Summary

This plan prioritizes the modularization of three large monolithic tool files (`gmail`, `gdrive`, `gdocs`) following the existing specifications in `specs/`. Secondary priorities include test coverage expansion and minor enhancements.

### Current State
| Module | Lines | State | Helpers Extracted | Modularized |
|--------|-------|-------|-------------------|-------------|
| gmail/ (modular) | ~1,120 | ✅ MODULAR | Yes (helpers.py) | Yes |
| gdrive/ (modular) | ~1,400 | ✅ MODULAR | Yes (drive_helpers.py) | Yes |
| gdocs/docs_tools.py | 1,266 | MONOLITH | Yes (managers/) | No |
| gcalendar/calendar_tools.py | 952 | Stable | No | N/A |
| gsheets/sheets_tools.py | 923 | Stable | Yes (sheets_helpers.py) | N/A |
| gtasks/tasks_tools.py | 858 | Stable | No | N/A |
| Others | <400 | Stable | N/A | N/A |

---

## Phase 1: Gmail Refactoring (Spec 01 + 02)

**Priority**: HIGH  
**Risk**: LOW (internal restructuring only)  
**Dependencies**: None

### Task 1.1: Extract Gmail Helpers (Spec 01) ✅ COMPLETE
**Spec**: `specs/01_gmail_helpers.md`

Created `gmail/helpers.py` with all internal functions moved from `gmail_tools.py`:
- [x] `_HTMLTextExtractor` class
- [x] `_html_to_text`
- [x] `_extract_message_body`
- [x] `_extract_message_bodies`
- [x] `_format_body_content`
- [x] `_extract_attachments`
- [x] `_extract_headers`
- [x] `_prepare_gmail_message`
- [x] `_generate_gmail_web_url`
- [x] `_format_gmail_results_plain`
- [x] `_format_thread_content`

**Verification**: ✅ All 123 tests pass, ruff clean

### Task 1.2: Modularize Gmail Tools (Spec 02) ✅ COMPLETE
**Spec**: `specs/02_gmail_modules.md`  
**Depends on**: Task 1.1

Split `gmail_tools.py` into domain-specific modules:
- [x] `gmail/search.py`: `search_gmail_messages`
- [x] `gmail/messages.py`: `get_gmail_message_content`, `get_gmail_messages_content_batch`, `send_gmail_message`, `draft_gmail_message`, `get_gmail_attachment_content`
- [x] `gmail/threads.py`: `get_gmail_thread_content`, `get_gmail_threads_content_batch`
- [x] `gmail/labels.py`: `list_gmail_labels`, `manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels`
- [x] `gmail/filters.py`: `list_gmail_filters`, `create_gmail_filter`, `delete_gmail_filter`
- [x] Update `gmail/__init__.py` to re-export all tools
- [x] Update `main.py` (line 176: `import_module("gmail")`)
- [x] Update `fastmcp_server.py` (line 127: `import gmail`)
- [x] Update `core/log_formatter.py` (added gmail submodule prefixes)
- [x] Update `tests/unit/tools/test_gmail_tools.py` (line 127: `from gmail import`)
- [x] Delete `gmail/gmail_tools.py`

**Verification**: ✅ All 123 tests pass, ruff clean, main.py --help works

---

## Phase 2: Drive Refactoring (Spec 03) ✅ COMPLETE

**Priority**: HIGH  
**Risk**: LOW  
**Dependencies**: None (can run parallel to Phase 1)

### Task 2.1: Modularize Drive Tools (Spec 03) ✅ COMPLETE
**Spec**: `specs/03_drive_refactor.md`

Note: `gdrive/drive_helpers.py` already exists (285 lines). Skip helper extraction.

Split `drive_tools.py` into domain-specific modules:
- [x] `gdrive/search.py`: `search_drive_files`, `list_drive_items`, `check_drive_file_public_access`
- [x] `gdrive/files.py`: `get_drive_file_content`, `get_drive_file_download_url`, `create_drive_file`, `update_drive_file`
- [x] `gdrive/permissions.py`: `get_drive_file_permissions`, `get_drive_shareable_link`, `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership`
- [x] Keep `gdrive/sync_tools.py` as-is (already separate)
- [x] Update `gdrive/__init__.py` to re-export all tools
- [x] Update `main.py` if needed
- [x] Delete `gdrive/drive_tools.py`

**Verification**: ✅ All 123 tests pass, ruff clean

---

## Phase 3: Docs Refactoring (Spec 04)

**Priority**: MEDIUM  
**Risk**: MEDIUM (complex manager dependencies)  
**Dependencies**: None (can run parallel to Phases 1-2)

### Task 3.1: Modularize Docs Tools (Spec 04)
**Spec**: `specs/04_docs_refactor.md`

Note: `gdocs/managers/` already exists with modular logic. Integrate carefully.

Split `docs_tools.py` into domain-specific modules:
- [ ] `gdocs/reading.py`: `search_docs`, `get_doc_content`, `list_docs_in_folder`, `inspect_doc_structure`
- [ ] `gdocs/writing.py`: `create_doc`, `modify_doc_text`, `find_and_replace_doc`, `batch_update_doc`, `update_doc_headers_footers`
- [ ] `gdocs/elements.py`: `insert_doc_elements`, `insert_doc_image`
- [ ] `gdocs/tables.py`: `create_table_with_data`, `debug_table_structure`
- [ ] `gdocs/export.py`: `export_doc_to_pdf`
- [ ] `gdocs/comments.py`: `read_document_comments`, `create_document_comment`, `reply_to_document_comment`, `resolve_document_comment`
- [ ] Update `gdocs/__init__.py` to re-export all tools
- [ ] Delete `gdocs/docs_tools.py`

**Verification**:
```bash
uv run ruff check gdocs/
uv run pytest tests/
```

---

## Phase 4: Enhancements

**Priority**: LOW  
**Risk**: LOW  
**Dependencies**: Phases 1-3 complete

### Task 4.1: Add Search Alias Support to Docs
Currently `gdocs/` doesn't use `resolve_file_id_or_alias()` from `gdrive/drive_helpers.py`.

- [ ] Import `resolve_file_id_or_alias` in docs tools that accept `document_id`
- [ ] Apply to: `get_doc_content`, `modify_doc_text`, `find_and_replace_doc`, `batch_update_doc`, `create_table_with_data`, `debug_table_structure`, `export_doc_to_pdf`, `inspect_doc_structure`

### Task 4.2: Complete download_doc_tabs Implementation
`gdrive/sync_tools.py` has a placeholder for tab-level document sync.

- [ ] Integrate Google Docs API to fetch individual tab content
- [ ] Save each tab as `[TabName].md` in the output directory
- [ ] Maintain the `_Full_Export.md` for complete document

### Task 4.3: Expand Test Coverage
Current gaps identified:
- [ ] `tests/unit/tools/test_drive_tools.py` - Drive tool unit tests
- [ ] `tests/unit/tools/test_docs_tools.py` - Docs tool unit tests
- [ ] `tests/unit/tools/test_calendar_tools.py` - Calendar tool unit tests
- [ ] `tests/unit/tools/test_sheets_tools.py` - Sheets tool unit tests
- [ ] `tests/unit/auth/test_service_decorator.py` - Decorator unit tests

---

## Phase 5: Auth Consolidation (Future)

**Priority**: LOW  
**Risk**: HIGH  
**Dependencies**: Phases 1-4 complete

Defer to `AUTH_IMPROVEMENT_PLAN.md` Phase 5. This involves major restructuring of the auth module and should only be undertaken after the tool refactoring is stable.

---

## Verification Checklist (Per Phase)

Before marking any phase complete:
- [ ] `uv run ruff check .` returns no errors
- [ ] `uv run ruff format .` makes no changes
- [ ] `uv run pytest` passes with exit code 0
- [ ] `python main.py --help` shows all expected tools
- [ ] Manual smoke test of 1-2 tools from refactored module

---

## Execution Order

```
Phase 1 (Gmail)     ─────────────────────────────►
Phase 2 (Drive)     ─────────────────────────────►  (parallel)
Phase 3 (Docs)      ─────────────────────────────►  (parallel)
                                                    │
                                                    ▼
Phase 4 (Enhancements) ──────────────────────────►
                                                    │
                                                    ▼
Phase 5 (Auth - Future) ─────────────────────────►
```

**Estimated Effort**:
- Phase 1: 2-3 hours
- Phase 2: 1-2 hours
- Phase 3: 2-3 hours
- Phase 4: 3-4 hours
- Phase 5: 8+ hours (defer)

---

## Notes

1. **Rollback Strategy**: Each phase can be rolled back independently using `git checkout` on the affected directory.
2. **No Breaking Changes**: All refactoring is internal. External tool names and signatures remain unchanged.
3. **Import Updates**: After modularization, `main.py` imports the module package (e.g., `gmail`) which triggers `__init__.py` to load all submodules.
4. **Existing Patterns**: Follow the established patterns in `gsheets/` (which already has `sheets_helpers.py` + `sheets_tools.py` separation).
