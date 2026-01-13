# Refactor Spec 03: Drive Modularization

**Objective**: Split `gdrive/drive_tools.py` (1481 lines) into focused modules.

**Context**: Drive tools handle file CRUD, permissions, and listing.

## 1. Target Structure
Create the following files in `gdrive/`:
- `search.py`: `search_drive_files`, `list_drive_items`, `check_drive_file_public_access`
- `files.py`: `get_drive_file_content`, `get_drive_file_download_url`, `create_drive_file`, `update_drive_file`
- `permissions.py`: `get_drive_file_permissions`, `get_drive_shareable_link`, `share_drive_file`, `batch_share_drive_file`, `update_drive_permission`, `remove_drive_permission`, `transfer_drive_ownership`
- `sync_tools.py`: (Already exists - leave as is or ensure it integrates well)

## 2. Implementation Steps

### A. Helper Extraction (Inline)
If there are internal helpers (start with `_`), move them to `gdrive/helpers.py` first (similar to Spec 01).

### B. Split Tools
1. Move tools to their respective new files.
2. Ensure `server` decorator is imported.
3. Ensure `google_auth` decorators (`@require_google_service`) are imported.

### C. Update Facade
1. Update `gdrive/__init__.py` to export all tools.
2. Update `main.py` or other consumers to import from `gdrive` package, not `drive_tools.py`.
3. Delete `gdrive/drive_tools.py`.

## 3. Verification
1. `uv run ruff check gdrive/`
2. `uv run pytest tests/`
3. Verify specific Drive tests: `uv run pytest tests/integration/test_drive_flow.py` (if exists) or equivalent.

## 4. Rollback
Revert git changes and delete new files.
