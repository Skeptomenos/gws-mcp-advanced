# Testing Google Docs API Behavior with MCP Tools

This document describes how to test Google Docs API behavior directly using MCP tools, bypassing the markdown parser to isolate API-level issues.

## When to Use This Approach

Use direct MCP testing when:
- Debugging style/formatting issues that may be API-related
- Testing hypotheses about API behavior before implementing fixes
- Comparing different request patterns to find what works
- Verifying that generated requests produce expected results

## The Testing Pattern

### Step 1: Create an Empty Test Document

```
create_doc(
    title="Test - <Description>",
    content="",
    parse_markdown=false
)
```

This creates a blank document without any markdown processing.

### Step 2: Send Raw API Requests via batch_update_doc

Use `batch_update_doc` to send specific request patterns.

**Note:** For Vertex AI / Gemini compatibility, the `operations` parameter must be passed as a JSON string (e.g., `'[{"type": "insert_text", ...}]'`) rather than a Python list. See [docs/MCP_PATTERNS.md#parameter-type-constraints-vertex-ai--gemini-compatibility](MCP_PATTERNS.md#parameter-type-constraints-vertex-ai--gemini-compatibility) for details.

```
batch_update_doc(
    document_id="<doc_id>",
    operations='[
        {"type": "insert_text", "index": 1, "text": "Normal bold normal\\n"},
        {"type": "format_text", "start_index": 8, "end_index": 12, "bold": true}
    ]'
)
```

### Step 3: Visual Verification

Open the document link in a browser and visually verify the result.

### Step 4: Compare Approaches

Create multiple test documents with different approaches:

| Document | Approach | Purpose |
|----------|----------|---------|
| Control | Current implementation | Baseline behavior |
| Test A | Hypothesis A | Test first fix idea |
| Test B | Hypothesis B | Test alternative fix |

## Example: Style Bleed Investigation

### Control Document (Current Approach)
```
create_doc(title="Bold Test - Control", content="", parse_markdown=false)

batch_update_doc(
    document_id="<id>",
    operations=[
        {"type": "insert_text", "index": 1, "text": "Normal bold normal\n"},
        {"type": "format_text", "start_index": 8, "end_index": 12, "bold": true}
    ]
)
```

### Test Document (With Reset After)
```
create_doc(title="Bold Test - Reset After", content="", parse_markdown=false)

batch_update_doc(
    document_id="<id>",
    operations=[
        {"type": "insert_text", "index": 1, "text": "Normal bold normal\n"},
        {"type": "format_text", "start_index": 8, "end_index": 12, "bold": true},
        {"type": "format_text", "start_index": 12, "end_index": 20, "bold": false}
    ]
)
```

### Compare Results
Open both documents side-by-side:
- If Control shows bleeding but Test doesn't → the reset approach works
- If both show same behavior → issue is elsewhere

## Testing the Markdown Parser

After isolating API behavior, test the full parser:

```
create_doc(
    title="Parser Test - <Feature>",
    content="Normal **bold** normal",
    parse_markdown=true
)
```

Compare the visual output to what raw API requests produce.

## Inspecting Document Structure

Use `inspect_doc_structure` to see internal document state:

```
inspect_doc_structure(document_id="<id>", detailed=true)
```

Use `get_doc_content` to see text content:

```
get_doc_content(document_id="<id>")
```

## Available batch_update_doc Operations

| Operation | Parameters | Purpose |
|-----------|------------|---------|
| `insert_text` | `index`, `text` | Insert text at position |
| `format_text` | `start_index`, `end_index`, `bold`, `italic`, etc. | Apply text formatting |
| `delete_text` | `start_index`, `end_index` | Delete text range |
| `insert_table` | `index`, `rows`, `columns` | Insert table |
| `insert_markdown` | `index`, `markdown` | Insert parsed markdown |

## Best Practices

1. **Name documents clearly** - Include the approach being tested in the title
2. **Create control documents** - Always have a baseline to compare against
3. **Test one variable at a time** - Change only one thing between test documents
4. **Document results** - Record doc IDs and outcomes for future reference
5. **Visual verification is ground truth** - Unit tests can't catch all API quirks

## Example Test Session Log

| Doc ID | Approach | Result |
|--------|----------|--------|
| `1ABC...` | Control (no reset) | ✅ Pass |
| `1DEF...` | Reset after bold | ✅ Pass |
| `1GHI...` | Full parser | ✅ Pass |

Keep this log in the relevant spec file (e.g., `specs/FIX_STYLE_BLEED.md`).
