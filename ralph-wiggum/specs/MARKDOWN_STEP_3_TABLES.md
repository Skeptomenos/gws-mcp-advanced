# Spec: Markdown Tables (Step 4 - Advanced)

**Goal:** Implement table support in the Markdown parser.
**Effort:** ~30 minutes
**Ref:** `IMPLEMENTATION_PLAN_MARKDOWN.md` (Section 6.2)

## 1. Table Logic (`gdocs/markdown_parser.py`)

Implement `_handle_table` logic.

*   **Tokenizer:** Initialize with `MarkdownIt("gfm-like")` to get table support out-of-the-box. Do NOT use "commonmark" preset if you want tables.
*   **Structure:**
    *   `table_open` -> Start table.
    *   `tr_open` -> Start row.
    *   `td_open` -> Start cell.
    *   `inline` -> Cell content.

### The Challenge: Indices
See "Table Index Math" in the implementation plan.

**Strategy:**
1.  Buffer the table structure into a 2D list `data = [['Header'], ['Row']]`.
2.  On `table_close`:
    *   Generate `insertTable` request at `current_index`.
    *   Use `gdocs.docs_tables.build_table_population_requests` (existing logic!) to generate the text insertion requests.
    *   **Crucial:** You must calculate the *indices* for `build_table_population_requests` manually because you don't have the real doc structure yet.
    *   **Alternative:** Use the simpler formula:
        *   Table consumes `1` index.
        *   Cell (0,0) starts at `TableStart + 4` (Verify this constant!).
        *   Or just stick to the text-only plan for V1 if tables are too risky.

**Recommendation for V1:** Implement basic 2D list collection and use `insertTable`. If cell population indices are too hard to predict without an API roundtrip, consider creating the table *empty* and then returning a warning, OR perform a "Best Effort" calculation.

**Best Effort Formula:**
*   Start of Table: `I`
*   Cell (r, c): `I + 1 + (r * cols + c) * 2 + sum(length of text in previous cells)`
    *   *Correction:* Google Docs table indexing is tricky.
    *   Plan B: Use `create_table_with_data` logic *if* it supports offline index calculation.

## 2. Verification
*   Unit test: `test_table_parsing()`.
*   Verify a simple 2x2 table generates valid requests.
