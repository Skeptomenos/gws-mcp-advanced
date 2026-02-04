# Spec: Markdown Tools Integration (Step 3)

**Goal:** Expose Markdown capabilities via MCP tools.
**Effort:** ~30 minutes
**Ref:** `IMPLEMENTATION_PLAN_MARKDOWN.md` (Section 3)

## 1. New Tool: `insert_markdown`
Create `insert_markdown` in `gdocs/writing.py`.

```python
@server.tool()
async def insert_markdown(
    service,
    user_google_email: str,
    document_id: str,
    markdown_text: str,
    index: int = 1
):
    # Logic:
    # 1. Resolve ID
    # 2. Convert MD -> Requests using MarkdownToDocsConverter
    # 3. Execute batchUpdate
```

## 2. Update `create_doc`
Modify `create_doc` in `gdocs/writing.py`.

*   Add arg: `parse_markdown: bool = True`
*   If `content` and `parse_markdown`:
    *   Use converter to generate requests.
    *   Execute requests immediately after doc creation.
*   Preserve existing plain-text behavior if `parse_markdown=False`.

## 3. Update `batch_update_doc`
Modify `batch_update_doc` in `gdocs/writing.py`.

**Constraint:** Ensure the `operations` parameter follows the "Parameter Type Constraints" defined in [docs/MCP_PATTERNS.md](../../docs/MCP_PATTERNS.md) to maintain Vertex AI / Gemini compatibility. It should be typed as `str | None` and parsed as JSON internally.

*   Add handler for `op["type"] == "insert_markdown"`.
*   Delegate to converter.

## 4. Verification
1.  **Mock Test:** Create a test that calls `create_doc` with Markdown and verifies the internal `batchUpdate` call has the correct structure.
2.  **Manual Test (Optional):** Run the server and create a real doc:
    ```python
    create_doc(title="MD Test", content="# Heading\n* List item")
    ```
