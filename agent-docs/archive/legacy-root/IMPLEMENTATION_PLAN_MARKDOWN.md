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

**Note:** To ensure compatibility with Vertex AI / Gemini function calling, complex parameters like `operations` must be passed as JSON strings rather than Python lists/dicts to avoid `anyOf` schema validation errors. See the "Parameter Type Constraints" section in [agent-docs/architecture/MCP_PATTERNS.md](agent-docs/architecture/MCP_PATTERNS.md) for the required implementation pattern.

```python
async def insert_markdown(
    service,
    user_google_email: str,
    document_id: str,
    markdown_text: str,
    index: int = 1
):
    ...
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

## 8. Development Constraints (Vertex AI / Gemini Compatibility)

### 8.1 Union Type Restrictions
Vertex AI and Gemini function calling have a strict requirement: if a parameter schema uses `anyOf`, it must be the **only field** in that schema object. Python union types (e.g., `str | list | None`) generate `anyOf` schemas with additional fields (like `default` or `description`), which causes validation errors.

**Rule:** Always use simple types (e.g., `str | None`) for tool parameters. If a tool needs to accept complex data (lists of dicts, mixed types), accept it as a **JSON string** and parse it using `json.loads()` inside the tool body.

### 8.2 Async Implementation
All tool logic must be `async`. Wrap blocking SDK calls in `asyncio.to_thread()`.

---

## 9. Future Extensions: Smart Chips and Advanced Linked Objects

This section captures the forward roadmap after Markdown rendering parity is complete, focused on smart-chip behavior in Google Docs.

### 9.1 Product Context for This MCP

Current behavior in this project:
1. Markdown task lists (`- [ ]`, `- [x]`) render as checkbox characters (`☐`, `☑`) in document text.
2. This gives stable visual output and preserves markdown semantics, but does not create native interactive Docs checklist bullets/chips.
3. Users now ask for native smart-chip behavior where technically possible.

### 9.2 Google API Capability Matrix (What We Can and Cannot Do)

| Target UX | API Status | Supported via Docs API batchUpdate? | Notes |
| :--- | :--- | :--- | :--- |
| Person chip / mention | Available | Yes | Use `InsertPersonRequest` (`documents.request`). |
| Native checklist bullets | Available | Yes | Use `createParagraphBullets` + `BULLET_CHECKBOX`. |
| Generic third-party smart chip insertion | Not exposed in Docs API writes | No (directly) | `RichLink` is modeled in document structure, but creation is not exposed as a Docs write request. |
| Rich link metadata mutation | Read-only in Docs model | No | `richLinkProperties` are output-only in `documents` resource. |
| Third-party smart chips based on URLs | Available via Add-ons platform | Not in plain Docs API flow | Requires Google Workspace Add-ons (`workspace.linkpreview` / `workspace.linkcreate`) and add-on deployment. |

### 9.3 Authoritative Documentation Links

Primary references for implementation and constraints:
1. Docs API request reference (`batchUpdate` request types, including `InsertPersonRequest` and `createParagraphBullets`):
   1. https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request
2. Docs API document resource (`RichLink`, `richLinkProperties` output-only model fields):
   1. https://developers.google.com/workspace/docs/api/reference/rest/v1/documents
3. Workspace Add-ons smart-chip insertion (resource chips):
   1. https://developers.google.com/workspace/add-ons/guides/create-insert-resource-smart-chip
4. Workspace Add-ons link-preview smart chips:
   1. https://developers.google.com/workspace/add-ons/guides/preview-links-smart-chips

### 9.4 Extension Roadmap (Phased)

#### Phase A: Native checklist bullets in Docs (Low-Medium complexity)
Goal: Upgrade markdown task lists from Unicode characters to native Docs checkbox bullets where possible.

Implementation outline:
1. Add parser mode for task-list paragraphs that applies `createParagraphBullets` with `bulletPreset=BULLET_CHECKBOX`.
2. Keep existing Unicode checkbox mode as explicit fallback (`task_list_mode="unicode"`), because native Docs checklist APIs may not preserve explicit checked-state fidelity from markdown in all cases.
3. Maintain existing anti-regression logic:
   1. no list-bleed after task lists,
   2. no empty trailing bullet paragraphs,
   3. no index drift in mixed table/image/list docs.

Acceptance criteria:
1. No visual regressions in `tests/manual/kitchen_sink.md`.
2. OP-70 gate remains PASS.
3. New manual matrix rows validate both modes:
   1. `native_checklist`,
   2. `unicode_fallback`.

Estimated effort:
1. Engineering: 1-2 days.
2. Manual validation and documentation: 0.5-1 day.

Risk:
1. Medium. Main risk is behavior mismatch between markdown checked/unchecked state and Docs native checklist rendering semantics.

#### Phase B: Person chip support (`@user`) (Medium complexity)
Goal: Add markdown-to-Docs person mentions using `InsertPersonRequest`.

Implementation outline:
1. Define deterministic markdown syntax extension for mentions (example: `@user@example.com` under opt-in parse mode).
2. Resolve mention tokens and emit `InsertPersonRequest` at calculated indices.
3. Provide fallback to plain text when mention resolution is unavailable/invalid.

Acceptance criteria:
1. Mention inserts produce native person chips in Docs.
2. Invalid mention inputs degrade gracefully with explicit warning in tool response.
3. No range/index regressions in mixed-content docs.

Estimated effort:
1. Engineering: 2-4 days.
2. Validation and hardening: 1 day.

Risk:
1. Medium. Main risk is token parsing ambiguity and account/identity resolution edge cases.

#### Phase C: Broad third-party smart chips (High complexity)
Goal: Enable richer third-party chip experiences beyond Docs API direct writes.

Implementation outline:
1. Build and deploy a Google Workspace Add-on with link preview/create integrations.
2. Use add-on scopes and callbacks for chip insertion flows.
3. Keep MCP integration as orchestration layer (not direct chip write path).

Acceptance criteria:
1. Add-on can render supported chips in Docs/Sheets under configured URL patterns.
2. End-to-end auth and permission model documented and testable.

Estimated effort:
1. Engineering + platform setup: 1-3+ weeks.

Risk:
1. High. Includes new deployment architecture, OAuth/scope governance, marketplace/admin constraints, and cross-product UX variability.

### 9.5 Proposed Defaults for This Repository

1. Keep current Unicode checkbox implementation as the stable default until Phase A is complete.
2. Treat native checklist mode as opt-in behind a parser/tool flag first.
3. Keep generic smart-chip promises out of user-facing claims until Add-ons path is implemented.
4. Track phases as roadmap items:
   1. `RM-05`: Native checklist bullets (`BULLET_CHECKBOX`) with fallback mode.
   2. `RM-06`: Person-chip markdown mentions (`InsertPersonRequest`).
   3. `RM-07`: Add-ons smart-chip integration feasibility and architecture.
