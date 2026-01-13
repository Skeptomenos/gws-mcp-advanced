# Refactor Spec 04: Docs Modularization

**Objective**: Split `gdocs/docs_tools.py` (1266 lines) into focused modules.

**Context**: Docs tools are highly specific (formatting, tables, structure).

## 1. Target Structure
Create/Update in `gdocs/`:
- `reading.py`: `get_document_outline`, `get_doc_content`, `read_document_section`, `inspect_doc_structure`
- `writing.py`: `create_doc`, `modify_doc_text`, `find_and_replace_doc`, `batch_update_doc`, `update_doc_headers_footers`
- `elements.py`: `insert_doc_elements`, `insert_doc_image`
- `tables.py`: `create_table_with_data`, `debug_table_structure` (Note: `docs_tables.py` helper already exists, integrate logic carefully)
- `export.py`: `export_doc_to_pdf`

## 2. Implementation Steps

### A. Helper Check
Check `docs_tools.py` for `_private_functions`. Move to `gdocs/helpers.py` if they exist.

### B. Split Tools
1. Create the files above.
2. Move `@server.tool` functions to appropriate files.
3. Pay close attention to imports from `gdocs/managers/` - these are already modularized logic that the tools use. Ensure imports are preserved.

### C. Update Facade
1. Update `gdocs/__init__.py`.
2. Delete `gdocs/docs_tools.py`.

## 3. Verification
1. `uv run ruff check gdocs/`
2. `uv run pytest tests/`

## 4. Rollback
Revert git changes.
