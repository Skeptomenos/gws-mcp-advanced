# Spec: Fix List Style Inheritance ("The Bleed")

**Goal:** Prevent list formatting (bullets/indentation) from bleeding into subsequent non-list paragraphs.
**Context:** Google Docs paragraphs inherit the style of the previous paragraph on newline. We must explicitly reset it.

## 1. Logic Update (`gdocs/markdown_parser.py`)

Modify `_handle_token` or individual handlers (like `_handle_block`) to detect "List Exit".

**Strategy:**
*   Add state: `self.in_list_block: bool = False`.
*   Set `True` on `bullet_list_open` / `ordered_list_open`.
*   Set `False` on `bullet_list_close` / `ordered_list_close`.
*   **Crucial:** When handling `heading_open`, `paragraph_open`, `blockquote_open`, `code_block`:
    *   IF `not self.in_list_block` AND the *previous* element was a list (or just defensively):
    *   Generate a `deleteParagraphBullets` request for the range of the new block.

**Implementation Detail:**
The safest way is to issue `deleteParagraphBullets` for *every* Header, Code Block, and Blockquote range. This ensures they never have bullets.

**Requests:**
```python
{
    "deleteParagraphBullets": {
        "range": {
            "startIndex": start,
            "endIndex": end
        }
    }
}
```

## 2. Verification
*   **Unit Test:** `test_list_exit_clears_bullets()`:
    *   Input: `* Item\n# Heading`
    *   Expect: `createParagraphBullets` (for Item) AND `deleteParagraphBullets` (for Heading).
*   **Visual Test:** Run `kitchen_sink.md` (No Tables) and verify Headings/Code blocks are clean.
