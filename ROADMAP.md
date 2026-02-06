# Product Roadmap

## Active Features

### Google Docs Markdown Formatting
**Status:** In Progress
**Branch:** `feature/gdocs-markdown-formatting`

#### Problem
The current `create_doc` tool treats all input as plain text. When AI assistants generate content (which is typically Markdown), it appears in the Google Doc with raw syntax (e.g., `# Heading`, `**bold**`) rather than proper formatting. This creates a poor user experience requiring manual cleanup.

#### Research & Options
We investigated three approaches to solve this:

1.  **Drive Import (HTML Conversion)**
    *   **Strategy:** Convert Markdown → HTML locally, then upload to Drive using the `convert=True` option.
    *   **Pros:** Easy implementation; handles complex HTML elements.
    *   **Cons:** **Cannot update existing files** easily (overwrites file); styles depend on Google's default HTML import (often looks like a "webpage" printout, not a native Doc).

2.  **Native Markdown Parser (Recommended by User)**
    *   **Strategy:** Write a custom Python parser to translate Markdown syntax directly into Google Docs API `batchUpdate` requests (`insertText`, `updateParagraphStyle`, `createParagraphBullets`, `insertTable`).
    *   **Pros:** 
        *   **Native Formatting:** Uses proper Google Docs styles (e.g., `HEADING_1`, `NORMAL_TEXT`) so the Outline view works.
        *   **Updatable:** Can insert formatted content into *existing* docs at any index.
        *   **Clean Data:** Results in a clean document structure, not a "converted HTML" blob.
    *   **Cons:** Higher initial development effort to write the parser.

3.  **Client-Side HTML**
    *   **Strategy:** Require the AI to send HTML.
    *   **Pros:** Zero dev effort.
    *   **Cons:** Poor UX; prone to errors.

#### Implementation Plan (Option 2 - Native Parser)
We will implement a robust **Native Markdown Parser** to satisfy the requirement for high-quality, updatable documents.

1.  **New Module:** Create `gdocs/markdown_parser.py`.
    *   Implement a parser that tokenizes Markdown (CommonMark subset).
    *   Map tokens to Google Docs API `Request` objects.
    *   **Support:**
        *   Headings (`#`) -> `updateParagraphStyle` (namedStyleType: HEADING_1, etc.)
        *   Bold/Italic (`**`, `*`) -> `updateTextStyle`
        *   Lists (`-`, `1.`) -> `createParagraphBullets`
        *   Tables (`| col |`) -> `insertTable` + cell population
        *   Code blocks (```) -> Monospace font + background

2.  **Tool Updates:**
    *   **`create_doc`**: Add `parse_markdown=True` flag (default). Use the parser to generate the initial `batchUpdate` requests.
    *   **`append_to_doc`** (or `modify_doc_text`): Enable Markdown support for inserting text into existing documents.

3.  **Testing:**
    *   Create test cases for mixed formatting (lists inside sections, tables).
    *   Verify "native" feel (Outline view works).
