# Implementation Plan: Native Markdown Parser for Google Docs

## Overview

Implement a native Markdown-to-Google-Docs conversion engine that translates Markdown syntax into Google Docs API `batchUpdate` requests, enabling proper headings, lists, formatting, and tables.

---

## Tasks

### Phase 0: Dependencies & Setup

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 0.1**: Add `markdown-it-py` to `pyproject.toml` dependencies | `IMPLEMENTATION_PLAN_MARKDOWN.md:L14-16` | Done in v0.0.4 |
| [x] | **Task 0.2**: Create empty `gdocs/markdown_parser.py` with module docstring and imports | `specs/MARKDOWN_STEP_1_CORE.md` | Done in v0.0.5 - MarkdownToDocsConverter skeleton with state management |

### Phase 1: Core Parser - MarkdownToDocsConverter

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 1.1**: Implement `MarkdownToDocsConverter` class skeleton with state management (`cursor_index`, `requests`, `active_styles` stack) | `specs/MARKDOWN_STEP_1_CORE.md` | Done in v0.0.5 (included in Task 0.2) |
| [x] | **Task 1.2**: Implement `convert()` entry method - parse MD to tokens, dispatch to handlers | `IMPLEMENTATION_PLAN_MARKDOWN.md:L28-31` | Done in v0.0.5 (included in Task 0.2) |
| [x] | **Task 1.3**: Implement inline text handling (`_handle_inline`) with `insertText` requests and cursor advancement | `IMPLEMENTATION_PLAN_MARKDOWN.md:L139-168` | Done in v0.0.6 - Index Tracker pattern with paragraph_close newlines |
| [x] | **Task 1.4**: Implement heading handling - map `#` to `HEADING_1`-`HEADING_6` via `updateParagraphStyle` | `IMPLEMENTATION_PLAN_MARKDOWN.md:L45` | Done in v0.0.7 - State machine with heading_open/close |
| [x] | **Task 1.5**: Implement bold/italic handling with style stack (push on `*_open`, merge on text, pop on `*_close`) | `IMPLEMENTATION_PLAN_MARKDOWN.md:L197-204` | Done in v0.0.8 - Style Stack pattern with merged updateTextStyle |
| [x] | **Task 1.6**: Implement link handling - apply `link` style with URL to text ranges | `IMPLEMENTATION_PLAN_MARKDOWN.md:L48` | Done in v0.0.9 - `_pop_link_style()` for link-specific stack removal |
| [x] | **Task 1.7**: Implement list handling (`_handle_list`) with `createParagraphBullets` and nesting level calculation | `IMPLEMENTATION_PLAN_MARKDOWN.md:L49,187-195` | Done in v0.0.10 - List type stack with nesting, bullet/ordered presets |
| [x] | **Task 1.8**: Implement code block handling - apply `Consolas` font + gray background styling | `IMPLEMENTATION_PLAN_MARKDOWN.md:L50` | Done in v0.0.11 - Fenced code blocks (fence) + inline code (code_inline) |
| [x] | **Task 1.9**: Implement blockquote handling - indent margins + italic style | `IMPLEMENTATION_PLAN_MARKDOWN.md:L52` | Done in v0.0.12 - blockquote_open/close handlers, indentStart/End margins (36PT), italic style |

### Phase 2: Core Parser Tests

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 2.1**: Create `tests/unit/gdocs/test_markdown_parser.py` with test fixtures and base setup | `IMPLEMENTATION_PLAN_MARKDOWN.md:L106-115` | Done in v0.0.13 - 37 comprehensive tests, importlib workaround for circular imports |
| [x] | **Task 2.2**: Add tests for headings - verify `HEADING_1`-`HEADING_6` style requests | `IMPLEMENTATION_PLAN_MARKDOWN.md:L107` | Done in v0.0.13 - `TestHeadings` class with H1-H6 coverage |
| [x] | **Task 2.3**: Add tests for inline formatting - verify `updateTextStyle` ranges for bold/italic/mixed | `IMPLEMENTATION_PLAN_MARKDOWN.md:L108` | Done in v0.0.13 - `TestBoldItalic` class with nested style tests |
| [x] | **Task 2.4**: Add tests for lists - verify `createParagraphBullets` with correct `nestingLevel` | `IMPLEMENTATION_PLAN_MARKDOWN.md:L109` | Done in v0.0.13 - `TestLists` class with bullet/ordered/nested tests |
| [x] | **Task 2.5**: Add tests for code blocks - verify font and background color requests | `specs/MARKDOWN_STEP_1_CORE.md` | Done in v0.0.13 - `TestCodeBlocks` class with fenced + inline code |
| [x] | **Task 2.6**: Add tests for links - verify link style applied to correct range | `specs/MARKDOWN_STEP_1_CORE.md` | Done in v0.0.13 - `TestLinks` class with URL verification |

### Phase 3: Tool Integration

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 3.1**: Create `insert_markdown` tool in `gdocs/writing.py` - resolve ID, convert, execute batchUpdate | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.14 - Full tool with decorators, validation, converter integration |
| [x] | **Task 3.2**: Update `create_doc` signature with `parse_markdown: bool = True` parameter | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.15 - parse_markdown=True default, uses MarkdownToDocsConverter |
| [x] | **Task 3.3**: Update `create_doc` logic - use converter when `parse_markdown=True` and content provided | `IMPLEMENTATION_PLAN_MARKDOWN.md:L84-91` | Done in v0.0.15 - conditional path with MarkdownToDocsConverter (lines 74-85 in writing.py) |
| [x] | **Task 3.4**: Update `batch_update_doc` to recognize `insert_markdown` operation type | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.16 - BatchOperationManager._build_operation_request() handles insert_markdown |
| [x] | **Task 3.5**: Add integration tests for `insert_markdown` tool - verify batchUpdate structure | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.17 - 17 tests in tests/integration/test_insert_markdown.py |
| [x] | **Task 3.6**: Add integration tests for `create_doc` with Markdown content | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.18 - 29 tests in tests/integration/test_create_doc_markdown.py |

### Phase 4: Table Support (Advanced)

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 4.1**: Enable `tables` plugin in markdown-it-py parser configuration | `specs/MARKDOWN_STEP_3_TABLES.md` | Done in v0.0.18 - `MarkdownIt("commonmark").enable("table")` in markdown_parser.py:L85 |
| [x] | **Task 4.2**: Implement table token buffering - collect 2D array from `table_open` → `td` → `table_close` | `specs/MARKDOWN_STEP_3_TABLES.md` | Done in v0.0.19 - _in_table, _table_data, _current_row, _current_cell_content state + handlers for table_open/close, tr_open/close, th/td_open/close |
| [x] | **Task 4.3**: Implement `_handle_table` method - generate `insertTable` request + integrate with existing table logic | `specs/MARKDOWN_STEP_3_TABLES.md` | Done in v0.0.20 - _handle_table_close generates insertTable with buffered dimensions, advances cursor using formula: 2 + rows * (2 * cols + 1). 4 new unit tests added. |
| [x] | **Task 4.4**: Implement table cell population with index tracking - use best-effort formula or delegate to TableOperationManager | `IMPLEMENTATION_PLAN_MARKDOWN.md:L171-184` | Done in v0.0.21 - `_handle_table_close()` generates insertText for each cell using best-effort formula: `base_cell_index = table_start + 4 + r * (2 * cols + 1) + c * 2 + text_offset`. Also adds `_apply_header_bold_style()` for first row. |
| [x] | **Task 4.5**: Add tests for table parsing - verify 2x2 table generates correct request sequence | `IMPLEMENTATION_PLAN_MARKDOWN.md:L110` | Done in v0.0.21 - 4 new tests: `test_table_cells_are_populated_with_content`, `test_table_header_row_gets_bold_style`, `test_table_cell_indices_are_calculated_correctly`, `test_empty_cells_are_skipped` |

---

### Phase 5: Critical Bug Fixes

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 5.1**: Fix table index calculation - change offset from `+4` to `+3` in `_handle_table_close()` and `_apply_header_bold_style()` | `specs/FIX_TABLE_MATH.md` | Done in v0.0.22 - Updated lines 554, 628 in markdown_parser.py |
| [x] | **Task 5.2**: Update table index unit tests to expect `+3` offset | `specs/FIX_TABLE_MATH.md` | Done in v0.0.23 - Enhanced test with explicit index verification per FIX_TABLE_MATH.md formula |
| [x] | **Task 5.3**: Implement list "bleed" fix - add `in_list_block` state tracking and `deleteParagraphBullets` emission | `specs/FIX_LIST_BLEED.md` | Done in v0.0.24 - Added _in_list_block, _just_exited_list state; emits deleteParagraphBullets for headings, paragraphs, code blocks, blockquotes after list exit |
| [x] | **Task 5.4**: Add unit test `test_list_exit_clears_bullets()` for bleed fix | `specs/FIX_LIST_BLEED.md` | Done in v0.0.25 - Added 6 tests in TestListBleedPrevention class covering headings, paragraphs, code blocks, blockquotes, nested lists |
| [x] | **Task 5.5**: Fix validation gap - add `insert_markdown` to `validate_operation()` in docs_helpers.py | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.26 - Added to required_fields with markdown_text required, index optional |
| [x] | **Task 5.6**: Update `batch_update_doc` docstring to include `insert_markdown` operation type | `specs/MARKDOWN_STEP_2_INTEGRATION.md` | Done in v0.0.27 - Already present from Task 3.4 (lines 398-399, 407 in writing.py); verified and confirmed |
| [x] | **Task 5.7**: Run full test suite and kitchen_sink.md integration test to verify all fixes | All specs | Done in v0.0.28 - All 425 tests pass (51 markdown parser tests, 46 integration tests) |

### Phase 6: Feature Enhancements (Optional)

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 6.1**: Implement horizontal rule handler (`hr` token) - insert page break or styled divider | `IMPLEMENTATION_PLAN_MARKDOWN.md` | Done in v0.0.29 - Uses borderBottom styling on empty paragraph; 7 new tests |
| [x] | **Task 6.2**: Implement strikethrough handler (`s_open`/`s_close`) with `strikethrough: true` style | `IMPLEMENTATION_PLAN_MARKDOWN.md` | Done in v0.0.30 - Enabled strikethrough plugin, added s_open/s_close handlers, 4 new tests |
| [x] | **Task 6.3**: Implement image handler (`image` token) - generate insertInlineImage requests for ![alt](src) syntax | `IMPLEMENTATION_PLAN_MARKDOWN.md` | Done in v0.0.31 - Added _handle_image method, supports public URLs and Drive URIs, 8 new tests |
| [x] | **Task 6.4**: Implement task list handler (`[ ]`, `[x]`) with checkbox characters | `IMPLEMENTATION_PLAN_MARKDOWN.md` | Done in v0.0.32 - tasklists plugin, ☐/☑ Unicode chars, 7 new tests |

---

## Legend

- `[ ]` Pending
- `[x]` Complete
- `[!]` Blocked

---

## Task Summary

| Phase | Tasks | Status | Description |
|-------|-------|--------|-------------|
| Phase 0 | 2 | Complete | Dependency setup |
| Phase 1 | 9 | Complete | Core parser implementation |
| Phase 2 | 6 | Complete | Core parser tests |
| Phase 3 | 6 | Complete | Tool integration |
| Phase 4 | 5 | Complete | Table support |
| Phase 5 | 7 | Complete | Critical bug fixes |
| Phase 6 | 4 | Complete | Feature enhancements |
| **Total** | **39** | Complete | |

---

## Implementation Notes

### Critical Patterns to Follow

1. **Parameter Type Constraints (Vertex AI / Gemini Compatibility)**
   - Always use `str | None` for complex parameters (like `operations` in `batch_update_doc`).
   - Accept input as a JSON string and parse using `json.loads()` internally.
   - Refer to [docs/MCP_PATTERNS.md](../../docs/MCP_PATTERNS.md#parameter-type-constraints-vertex-ai--gemini-compatibility) for details.

2. **Index Tracker Pattern** (`IMPLEMENTATION_PLAN_MARKDOWN.md:L136-168`)
   - Start at `cursor_index = start_index`
   - After each `insertText`, advance by `len(text)`
   - Style requests use `[old_cursor, new_cursor)` range

2. **Style Stack Pattern** (`IMPLEMENTATION_PLAN_MARKDOWN.md:L197-204`)
   - Push `{"bold": True}` on `strong_open`
   - Merge all active styles when inserting text
   - Pop on `strong_close`

3. **List Nesting Formula** (`IMPLEMENTATION_PLAN_MARKDOWN.md:L187-195`)
   - `nestingLevel = (token.level - 1) // 2`

4. **Table Index Math** (`specs/FIX_TABLE_MATH.md`)
   - **CORRECTED**: Base offset is `table_start + 3` (NOT `+4`)
   - Formula: `base_cell_index = table_start + 3 + (r * (cols * 2 + 1)) + (c * 2)`
   - Track `current_text_offset` for cumulative text insertions

5. **List Bleed Prevention** (`specs/FIX_LIST_BLEED.md`)
   - Track `in_list_block` state (True on list_open, False on list_close)
   - On heading_open, paragraph_open, blockquote_open, fence: emit `deleteParagraphBullets` if just exited list

### Dependencies

- `markdown-it-py` with CommonMark preset + tables plugin
- Existing: `gdocs/docs_tables.py`, `gdocs/docs_helpers.py`

### Verification Protocol

Before marking any phase complete:
1. `uv run ruff check .` - No lint errors
2. `uv run ruff format .` - No format changes
3. `uv run pytest tests/unit/gdocs/test_markdown_parser.py` - All tests pass
4. `uv run pytest` - Full test suite passes
