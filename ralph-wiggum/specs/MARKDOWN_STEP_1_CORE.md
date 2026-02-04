# Spec: Native Markdown Parser Core (Step 1-2)

**Goal:** Implement the core `MarkdownToDocsConverter` engine.
**Effort:** ~30 minutes
**Ref:** `IMPLEMENTATION_PLAN_MARKDOWN.md` (Sections 1.2, 2, 6)

## 1. Dependencies
Add `markdown-it-py` to `pyproject.toml`.

## 2. Core Implementation (`gdocs/markdown_parser.py`)

Create the `MarkdownToDocsConverter` class.

### Class Structure
```python
from markdown_it import MarkdownIt

class MarkdownToDocsConverter:
    def __init__(self):
        self.md = MarkdownIt("commonmark")
        self.requests = []
        self.cursor_index = 1
        self.active_styles = [] # Stack of style dicts

    def convert(self, markdown_text: str, start_index: int = 1) -> list[dict]:
        self.cursor_index = start_index
        tokens = self.md.parse(markdown_text)
        for token in tokens:
            self._handle_token(token)
        return self.requests
```

### Required Handlers
Implement logic for:
1.  **Text (`inline`):** Insert text at `cursor_index`. Advance cursor.
2.  **Headings (`heading_open`):**
    *   Map `h1` -> `HEADING_1`, etc.
    *   Generate `updateParagraphStyle` request for the range.
3.  **Styles (`strong_open`, `em_open`):**
    *   Push style `{"bold": True}` to stack.
    *   On text insertion, merge all active styles.
    *   On `close`, pop style.
4.  **Lists (`bullet_list_open`):**
    *   Track `nesting_level`.
    *   Generate `createParagraphBullets` request.
5.  **Code Blocks (`fence`):**
    *   Insert text with `Consolas` font and gray background.

**Crucial:** Follow the "Index Tracker" pattern from `IMPLEMENTATION_PLAN_MARKDOWN.md` Section 6.1.

## 3. Unit Tests (`tests/unit/gdocs/test_markdown_parser.py`)
Create comprehensive tests *without* mocking the API (test the request generation logic).

*   `test_simple_text()`: "Hello" -> 1 request.
*   `test_heading()`: "# H1" -> insert + updateParagraphStyle.
*   `test_bold_italic()`: "**B**_I_" -> correct style ranges.
*   `test_list_nesting()`: Verify nesting level calculation.

## Verification
Run `pytest tests/unit/gdocs/test_markdown_parser.py`.
