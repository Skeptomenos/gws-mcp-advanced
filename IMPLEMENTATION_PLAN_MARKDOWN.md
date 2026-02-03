# Implementation Plan: Google Docs Native Markdown Parser

**Feature:** Native Markdown support for Google Docs
**Branch:** `feature/gdocs-markdown-formatting`
**Goal:** Enable users to create and update Google Docs using standard Markdown syntax, which is automatically converted into native Google Docs structural elements (Headings, Tables, Lists, Formatting) rather than plain text.

---

## 1. Core Architecture

We will implement a translation engine that converts a Markdown string into a sequence of Google Docs API `batchUpdate` requests.

### 1.1 Dependency
*   **Library:** `markdown-it-py`
*   **Reason:** Pure Python, spec-compliant (CommonMark), produces a flat token stream ideal for linear request generation.
*   **Action:** Add to `pyproject.toml`.

### 1.2 The Engine: `gdocs/markdown_parser.py`

Create a class `MarkdownToDocsConverter` that handles the stateful conversion process.

**State Management:**
*   `cursor_index`: Tracks the current insertion point in the Google Doc (starts at user-provided index).
*   `requests`: List of `dict` (Google Docs API requests) to be executed.
*   `list_nesting_level`: Tracks depth for nested lists.

**Key Methods:**
*   `convert(markdown_text: str, start_index: int = 1) -> list[dict]`
    *   Main entry point.
    *   Parses MD to tokens.
    *   Iterates tokens and delegates to handlers.
*   `_handle_inline(token)`: Processes text, bold, italic, links.
*   `_handle_block(token)`: Processes paragraphs, headings, code blocks.
*   `_handle_list(token)`: Processes bullet/ordered lists (handles nesting).
*   `_handle_table(token)`: Processes tables (calculates cell indices).

---

## 2. Feature Specification

### 2.1 Supported Markdown Elements & Mapping

| Markdown Element | Google Docs API Request | Implementation Details |
| :--- | :--- | :--- |
| **Heading 1-6** (`#`) | `updateParagraphStyle` | `namedStyleType`: `HEADING_1` to `HEADING_6`. |
| **Bold** (`**`) | `updateTextStyle` | `textStyle`: `{"bold": true}`. |
| **Italic** (`*`) | `updateTextStyle` | `textStyle`: `{"italic": true}`. |
| **Links** (`[text](url)`) | `updateTextStyle` | `textStyle`: `{"link": {"url": url}}`. |
| **Lists** (`-`, `1.`) | `createParagraphBullets` | `bulletPreset`: `BULLET_DISC_CIRCLE_SQUARE` or `NUMBERED_DECIMAL_ALPHA_ROMAN`. Support `nestingLevel` based on indentation. |
| **Code Block** (```) | `updateTextStyle` + `updateParagraphStyle` | Font: `Consolas` (or similar monospace). Background: Light Gray (`#f5f5f5`). |
| **Tables** (`\| col \|`) | `insertTable` + `insertText` | **Complex:** Must calculate cell indices. Formula: `TableStart + 1 + RowOffset + CellOffset`. |
| **Blockquote** (`>`) | `updateParagraphStyle` | Indent `start` and `end` margins. Italic text style. |

### 2.2 Formatting Logic (The "Cursor" Problem)

Google Docs is a single stream. Every insertion shifts subsequent indices.
*   **Strategy:** We generate `insertText` requests in **reverse order** (or strict linear order if we track the cursor perfectly).
*   **Decision:** We will use **strict linear tracking**.
    *   `cursor = start_index`
    *   Insert "Hello" (length 5).
    *   Request: `insertText(index=cursor, text="Hello")`
    *   `cursor += 5`
    *   Apply style to range `[old_cursor, cursor)`.

---

## 3. Integration Points

### 3.1 New Tool: `insert_markdown`
A dedicated tool for inserting formatted content into *existing* docs.

```python
async def insert_markdown(
    service,
    document_id: str,
    markdown_text: str,
    index: int = 1  # Default to start
):
    converter = MarkdownToDocsConverter()
    requests = converter.convert(markdown_text, index)
    service.documents().batchUpdate(body={"requests": requests}).execute()
```

### 3.2 Update `create_doc`
Modify the existing tool to use the converter by default.

*   **New Parameter:** `parse_markdown: bool = True`
*   **Logic:**
    *   If `content` is provided AND `parse_markdown=True`: Use `MarkdownToDocsConverter`.
    *   If `parse_markdown=False`: Use existing plain text insertion.

### 3.3 Update `batch_update_doc`
Add support for a new operation type: `insert_markdown`.

```python
# In operation handler:
if op["type"] == "insert_markdown":
    reqs = converter.convert(op["markdown"], op["index"])
    requests.extend(reqs)
```

---

## 4. Test Plan

### 4.1 Unit Tests (`tests/unit/gdocs/test_markdown_parser.py`)
*   **Headings:** Verify `# H1` generates `HEADING_1` style request.
*   **Styles:** Verify `**bold**` generates correct `updateTextStyle` range.
*   **Lists:** Verify nested lists generate correct `nestingLevel`.
*   **Tables:** Verify 2x2 table generates `insertTable` + 4 `insertText` requests at correct indices.

### 4.2 Integration Tests
*   Create a doc with mixed Markdown content.
*   Verify no API errors (400 Bad Request).
*   (Manual) Open doc to verify visual fidelity.

---

## 5. Execution Steps for Developer

1.  **Dependencies:** Add `markdown-it-py` to `pyproject.toml` and install.
2.  **Parser Implementation:** Create `gdocs/markdown_parser.py` following the logic in section 1.2 and section 6.
3.  **Tool Implementation:**
    *   Create `insert_markdown` in `gdocs/writing.py`.
    *   Modify `create_doc` signature and logic.
    *   Update `batch_update_doc` logic.
4.  **Verification:** Run unit tests. Verify with `create_doc(..., content="# Success\nIt works!")`.

---

## 6. Reference Algorithms (Crucial Implementation Details)

To avoid reinventing complex logic, follow these patterns established by open-source tools like `md2gdocs`.

### 6.1 The "Index Tracker" Pattern
Google Docs indices shift with every insertion. Do NOT use `batchUpdate` with fixed indices unless you calculate them perfectly.

**Recommended Approach:** Two-Phase Request Generation (Reverse Style Application)

To prevent style bleeding and index shifting issues, we separate content insertion from formatting:

1.  **Phase 1 (Insertions):** Generate all `insertText` requests in forward order. This builds the document structure.
2.  **Phase 2 (Styles):** Generate all `updateTextStyle` requests, but execute them in **REVERSE ORDER** (end of document first).

**Why Reverse Order?**
Applying styles from end-to-start ensures that modifying a range (e.g., [100, 110)) does not affect the indices of earlier ranges (e.g., [50, 60)). This pattern is robust for both creating new documents and updating existing ones.

```python
def convert(markdown_text):
    # ... generate all requests ...
    
    # Split by type
    inserts = [r for r in requests if "insertText" in r]
    styles = [r for r in requests if "updateTextStyle" in r]
    others = [r for r in requests if r not in inserts and r not in styles]
    
    # Reverse styles to apply from end-to-start
    styles.reverse()
    
    # Return ordered sequence
    return inserts + styles + others
```

### 6.2 Table Index Math
Tables are the hardest part. A table is NOT just text.
*   **Structure:** A table consumes indices for the table start, rows, and cells.
*   **Formula:**
    *   Inserting a table adds `1` index (the table itself).
    *   BUT, you cannot "insert text into cell (0,0)" immediately using the *original* cursor.
    *   **Strategy:** 
        1. Insert Table at `current_index`.
        2. `current_index += 1` (Move inside table).
        3. For each cell:
            *   Insert text at `current_index`.
            *   `current_index += len(text)`.
            *   `current_index += 2` (Cell end marker + padding? Verify this constant).
            *   *Correction:* It is safer to use **End-of-Segment** insertion or `tableStartLocation` if possible, BUT the most robust way (used by `md2gdocs`) is to calculate the specific offset.
            *   **Simplified Strategy for V1:** Insert the table first. Then, generate `insertText` requests for specific cells using the `create_table_with_data` logic we already have in `gdocs/tables.py` (which calculates indices post-creation).

### 6.3 List Nesting (CORRECTED - 2026-02-03)

**Key Discovery:** The Google Docs API determines nesting level by **counting leading TAB characters** in the text, NOT via a `nestingLevel` parameter.

From the official API docs for `CreateParagraphBulletsRequest`:
> "The nesting level of each paragraph will be determined by counting leading tabs in front of each paragraph. These leading tabs are removed by this request."

**Implementation:**
1. Track nesting depth via `_list_type_stack` length
2. Prepend `\t` characters to list item text based on depth
3. Apply `createParagraphBullets` - API handles nesting automatically

```python
def _insert_list_item_text(self, content: str) -> None:
    nesting_level = len(self._list_type_stack) - 1  # 0-based
    tabs = "\t" * nesting_level
    self._insert_text(tabs + content)
```

**Example:**
```
Text inserted: "Item 1\n\tNested A\n\t\tDeep B\n"
After createParagraphBullets: Proper 3-level nested list
```

### 6.4 Style Stack (Handling `**Bold _Italic_**`)
Markdown is hierarchical.
1.  Push "Bold" to `active_styles` stack.
2.  Push "Italic" to `active_styles` stack.
3.  Write "Italic Text" -> Apply `merge(active_styles)`.
4.  Pop "Italic".
5.  Write "Bold Text" -> Apply `merge(active_styles)`.
6.  Pop "Bold".

---

## 7. External References

### 7.1 Related Open Source Projects

| Project | URL | Relevance |
|---------|-----|-----------|
| **md2gdocs (original)** | https://gitlab.com/wryfi/md2gdocs | Uses Drive API HTML import (implicit list nesting via `<ul>`/`<ol>`) |
| **gravitas-md2gdocs** | https://github.com/Significant-Gravitas/gravitas-md2gdocs | Direct Docs API approach; calculates `nesting_level` but doesn't send it |
| **beancount** | https://github.com/beancount/beancount | Uses external tools (Pandoc) for doc conversion |

### 7.2 Research Findings (2026-02-03)

**List Nesting Approaches:**

1. **HTML Import (md2gdocs original):** Convert Markdown → HTML, upload via Drive API with `mimeType: text/html`. Google's import engine handles nested `<ul>`/`<ol>` automatically. *Pro:* Simple. *Con:* Less control, requires Drive API.

2. **Direct API (gravitas-md2gdocs):** Parse indentation, track `nesting_level = indent // 2`, generate `createParagraphBullets` requests. **BUG:** Current implementation calculates nesting but doesn't pass it to API.

3. **Key Insight:** The `createParagraphBullets` request does NOT directly accept `nestingLevel`. Nesting must be applied via `updateParagraphStyle` with the list's `listId` and `nestingLevel` properties AFTER bullets are created.

### 7.3 Google Docs API Documentation

- [CreateParagraphBulletsRequest](https://developers.google.com/docs/api/reference/rest/v1/documents/request#CreateParagraphBulletsRequest)
- [List Resource](https://developers.google.com/docs/api/reference/rest/v1/documents#List)
- [NestingLevel](https://developers.google.com/docs/api/reference/rest/v1/documents#NestingLevel)
