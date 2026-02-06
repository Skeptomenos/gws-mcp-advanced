# Spec: Fix Table Index Calculation

**Goal:** Fix the `HttpError 400` "index out of bounds" error when creating tables from Markdown.
**Context:** The previous formula used `table_start + 4`. Debugging confirmed the correct offset is `table_start + 3`.

## 1. Logic Update (`gdocs/markdown_parser.py`)

Modify `_handle_table_close` method.

**Correct Formula:**
```python
# Constants derived from 2x2 table debug:
# Table Start -> Cell (0,0) = +3
# Cell -> Next Cell = +2
# Row -> Next Row = +3 (effectively handled by the formula below)

# Formula for EMPTY table cells:
# base_cell_index = table_start + 3 + (r * (cols * 2 + 1)) + (c * 2)
```

**Algorithm:**
1.  Calculate `base_cell_index` for the cell using the formula above.
2.  Add `current_text_offset` (sum of lengths of text inserted in *previous* cells of the *same* table operation).
3.  Use this `final_index` for `insertText`.
4.  Update `current_text_offset += len(text)`.

**Example (2x2 Table at index 2):**
*   (0,0): `2 + 3 + 0 + 0 = 5`.
*   (0,1): `2 + 3 + 0 + 2 = 7`.
*   (1,0): `2 + 3 + 5 + 0 = 10`.
*   (1,1): `2 + 3 + 5 + 2 = 12`.

## 2. Verification
*   **Unit Test:** Update `test_markdown_parser.py` -> `test_table_cell_indices_are_calculated_correctly`.
    *   Change assertion to expect `table_start + 3`.
*   **Integration Test:** Run `kitchen_sink.md` (uncomment table) and verify it passes without error.
