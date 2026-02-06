# MCP Tool Patterns

## Standard Tool Structure

All MCP tools follow this decorator stack:

```python
@server.tool()
@handle_http_errors("tool_name", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def tool_name(
    service,                          # Injected by @require_google_service
    user_google_email: str,           # Required for session mapping
    param1: str,
) -> str:
    """
    Clear description of the tool's purpose.

    Args:
        user_google_email: The user's Google email address. Required.
        param1: Purpose of param1.
    """
    return "Result"
```

## Decorator Stack Order

1. `@server.tool()` - Registers with MCP server (outermost)
2. `@handle_http_errors(...)` - Catches and formats Google API errors
3. `@require_google_service(...)` - Injects authenticated service (innermost)

## Async Requirement

All MCP tools MUST be async. Wrap blocking Google API calls in `asyncio.to_thread()`:

```python
# CORRECT: Offload blocking I/O to a thread
result = await asyncio.to_thread(service.files().list(q=query).execute)

# WRONG: Blocks the event loop
result = service.files().list(q=query).execute()
```

## Parameter Type Constraints (Vertex AI / Gemini Compatibility)

**Problem:** Vertex AI and Gemini have stricter JSON schema requirements than OpenAI. When `anyOf` is used in a schema, it must be the **only field** - you cannot have `anyOf` alongside `default`, `description`, or other fields.

Python union types like `str | list[...] | None` generate schemas with `anyOf` plus other fields, causing this error:

```
Unable to submit request because `tool_name` functionDeclaration `parameters.param`
schema specified other fields alongside any_of. When using any_of, it must be the
only field set.
```

**Solution:** Avoid union types with lists/dicts. Use `str | None` and parse JSON internally:

```python
# ❌ BAD: Union types generate incompatible anyOf schemas
async def add_formatting(
    condition_values: str | list[str | int | float] | None = None,
    reminders: str | list[dict[str, Any]] | None = None,
) -> str:
    ...

# ✅ GOOD: Simple types, parse JSON internally
async def add_formatting(
    condition_values: str | None = None,  # Accepts JSON string: '["value1", "value2"]'
    reminders: str | None = None,         # Accepts JSON string: '[{"method": "popup", "minutes": 15}]'
) -> str:
    if condition_values:
        parsed = json.loads(condition_values)  # Parse in function body
    ...
```

**Allowed union patterns:**
- `str | None` - Safe, no anyOf generated
- `int | None` - Safe
- `bool | None` - Safe
- `T | None` where T is a simple type - Safe

**Forbidden union patterns:**
- `str | list[...]` - Generates anyOf
- `list[str] | list[dict]` - Generates anyOf
- Any union of complex types

## Error Handling Decorator

The `@handle_http_errors` decorator accepts:

| Parameter      | Description                                        |
| -------------- | -------------------------------------------------- |
| `tool_name`    | Name for error messages                            |
| `is_read_only` | `True` for read operations, `False` for mutations  |
| `service_type` | Google service type (drive, gmail, calendar, etc.) |

## Search Aliases

`SearchManager` (`core/managers.py`) caches search results with A-Z aliases.
Always use `resolve_file_id_or_alias()` when a tool accepts a file ID:

```python
from core.managers import resolve_file_id_or_alias

async def my_tool(file_id: str, ...):
    # Resolves "A" -> actual file ID, or passes through if already an ID
    resolved_id = resolve_file_id_or_alias(file_id)
```

## File Sync Safety

Sync tools (`gdrive/sync_tools.py`) use `SyncManager`.

**Critical**: Always default `dry_run=True` for any tool that modifies local or remote files:

```python
async def sync_file(
    ...,
    dry_run: bool = True,  # Safety default
) -> str:
    if dry_run:
        return "Dry run: would sync file..."
    # Actual sync logic
```

## Service Types and Scopes

Common service type mappings (see `auth/scopes.py` for full list):

| Service Type | Scopes                              |
| ------------ | ----------------------------------- |
| `drive`      | `drive_read`, `drive_write`         |
| `gmail`      | `gmail_read`, `gmail_send`          |
| `calendar`   | `calendar_read`, `calendar_write`   |
| `docs`       | `docs_read`, `docs_write`           |
| `sheets`     | `sheets_read`, `sheets_write`       |

## Architecture References

- For auth flow details, see `auth/ARCHITECTURE.md`
- For security considerations, see `docs/MCP_SECURITY_STRATEGY.md`

## Google Docs API batchUpdate Pattern

When generating complex `batchUpdate` sequences (like Markdown conversion), request ordering is critical to avoid index shifting bugs and style bleeding.

### The Single-Insert Architecture (Prevents Style Bleeding)

**Problem:** When inserting text sequentially, the Google Docs API inherits styles from adjacent text. This causes "style bleeding" where bold/italic extends past intended ranges.

**Solution:** Insert ALL text in a single `insertText` request, then apply styles to ranges within the already-inserted text.

```python
# ❌ BAD: Sequential insertion causes style bleeding
requests = [
    {"insertText": {"text": "Normal ", "location": {"index": 1}}},
    {"insertText": {"text": "bold", "location": {"index": 8}}},
    {"updateTextStyle": {"range": {"startIndex": 8, "endIndex": 12}, ...}},
    {"insertText": {"text": " normal", "location": {"index": 12}}},  # Inherits bold!
]

# ✅ GOOD: Single insert, then style
requests = [
    {"insertText": {"text": "Normal bold normal\n", "location": {"index": 1}}},
    {"updateTextStyle": {"range": {"startIndex": 8, "endIndex": 12}, "textStyle": {"bold": True}, ...}},
]
```

**Implementation Pattern:**
1. Buffer all text during parsing
2. Track style ranges as `(start, end, style)` tuples
3. Generate ONE `insertText` with the complete buffer
4. Generate `updateTextStyle` for each tracked range

See `gdocs/markdown_parser.py` for the reference implementation.

### Request Ordering

When using multiple request types, order them safely:

```python
return (
    insert_requests           # Text content first
    + style_requests          # Inline styles (bold, italic, links)
    + para_requests           # Paragraph formatting (headings, indents)
    + bullet_requests         # List bullets
    + table_requests          # Table structure
)
```

### Simulating Blockquotes (No Native Element)

**Problem:** Google Docs has no semantic "blockquote" element like HTML's `<blockquote>`.

**Solution:** Simulate blockquotes using paragraph styling with `borderLeft` and `indentStart`:

```python
{
    "updateParagraphStyle": {
        "range": {"startIndex": start, "endIndex": end},
        "paragraphStyle": {
            "indentStart": {"magnitude": 36, "unit": "PT"},      # Push text from margin
            "indentFirstLine": {"magnitude": 36, "unit": "PT"},  # Match indent (flush block)
            "borderLeft": {
                "color": {"color": {"rgbColor": {"red": 0.7, "green": 0.7, "blue": 0.7}}},
                "width": {"magnitude": 3, "unit": "PT"},         # Gray vertical bar
                "padding": {"magnitude": 12, "unit": "PT"},      # Space between bar and text
                "dashStyle": "SOLID"
            }
        },
        "fields": "indentStart,indentFirstLine,borderLeft"
    }
}
```

**Key Points:**
- `borderLeft` creates the visual "quote bar" effect
- `indentStart` + `indentFirstLine` must match for flush block indent
- For nesting: multiply indent by nesting level (e.g., 36 PT × level)
- Add `italic` text style for traditional quote appearance

See `specs/FIX_BLOCKQUOTES.md` for full implementation details.

### List Nesting via Leading Tabs

**Problem:** How to create nested bullet lists with proper indentation?

**Solution:** The Google Docs API determines nesting level by **counting leading TAB characters** in the text.

From API docs for `CreateParagraphBulletsRequest`:
> "The nesting level of each paragraph will be determined by counting leading tabs in front of each paragraph. These leading tabs are removed by this request."

```python
# Insert text with tabs for nesting
text = "Level 1\n\tLevel 2\n\t\tLevel 3\n"

requests = [
    {"insertText": {"location": {"index": 1}, "text": text}},
    {"createParagraphBullets": {
        "range": {"startIndex": 1, "endIndex": len(text) + 1},
        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
    }}
]
# Result: 3-level nested bullet list with automatic indentation
```

**Key Points:**
- Prepend `\t` characters based on nesting depth (0 tabs = level 1, 1 tab = level 2, etc.)
- The API automatically removes tabs and applies correct nesting
- Works for both `BULLET_*` and `NUMBERED_*` presets

See `specs/FIX_LIST_NESTING.md` for full implementation details.
