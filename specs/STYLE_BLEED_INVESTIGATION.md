# Style Bleeding Investigation - RESOLVED

**Status**: ✅ RESOLVED  
**Last Updated**: 2026-02-03  
**Resolution**: Single-Insert Architecture (Approach 6) works correctly.
**Purpose**: Document all attempted fixes to prevent repeating the same mistakes.

---

## The Problem

When converting Markdown to Google Docs, bold/italic styles "bleed" into subsequent text instead of stopping at the closing markers.

**Example Input**:
```markdown
Here is **bold** text
```

**Expected Output**:
- "Here is " = normal
- "bold" = bold
- " text" = normal

**Actual Output**:
- "Here is " = normal
- "bold text" (and everything after) = bold

---

## Root Cause Analysis

The Google Docs API documentation states:

> "Text styles for inserted text will be determined automatically, generally preserving the styling of neighboring text. In most cases, the text style for the inserted text will match the text immediately before the insertion index."

This means:
1. When text is inserted, it inherits styles from adjacent text
2. Applying `updateTextStyle` to a range should set styles, but something causes bleeding
3. The API behavior is not fully understood

---

## Failed Approaches

### Approach 1: Single-Character Reset
**Hypothesis**: Apply `bold=False` to the character immediately after the bold text ends.

**Implementation**:
```python
# After popping bold style at index 13:
{
    "updateTextStyle": {
        "range": {"startIndex": 13, "endIndex": 14},
        "textStyle": {"bold": False},
        "fields": "bold"
    }
}
```

**Result**: FAILED - Style still bled into subsequent text.

**Test Doc**: `1r0QjunzMnDuuls-BI1f5wx-HWdpc6El3hEC1E96eA6g`

---

### Approach 2: Full-Range Reset (End of Style to End of Document)
**Hypothesis**: Reset styles from where bold ends to the end of the document.

**Implementation**:
```python
# After popping bold style at index 13, reset to end (index 19):
{
    "updateTextStyle": {
        "range": {"startIndex": 13, "endIndex": 19},
        "textStyle": {"bold": False},
        "fields": "bold"
    }
}
```

**Result**: FAILED - Style still bled.

**Test Doc**: `1IzJ1SLigJsG6cW3XZG_xiGCo8EWktPcqOSlii8r7CJI`

---

### Approach 3: Two Separate batchUpdate Calls
**Hypothesis**: Insert all text first, then apply styles in a separate API call.

**Implementation**:
```python
# First batchUpdate: all insertText requests
await service.documents().batchUpdate(
    documentId=doc_id, 
    body={"requests": insert_requests}
).execute()

# Second batchUpdate: all updateTextStyle requests
await service.documents().batchUpdate(
    documentId=doc_id, 
    body={"requests": style_requests}
).execute()
```

**Result**: FAILED - Style still bled.

**Test Doc**: `1WsIszafEwE688Bf-SfyPzzAY0zq1cIo7ay_33ORihGQ`

---

### Approach 4: Reset Before Style Application
**Hypothesis**: Apply reset requests before applying the actual style.

**Implementation**:
```python
return (
    insert_requests
    + reset_requests      # Resets come first
    + style_requests      # Then actual styles
    + para_requests
    ...
)
```

**Result**: FAILED - Style still bled.

**Test Doc**: `1MzuDSrbrKKSm2PX5G88OsJeLNMPxtXfz7o3eWxivG_M`

---

### Approach 5: Reverse Order Style Application
**Hypothesis**: Apply styles from the end of the document backward to prevent interference.

**Implementation**:
```python
style_requests.reverse()  # Apply end-of-doc styles first
```

**Result**: FAILED - Style still bled.

---

### Approach 6: Single-Insert Architecture (Current Implementation)
**Hypothesis**: Insert ALL text as one `insertText` operation, then apply styles to ranges. This avoids style inheritance during sequential inserts.

**Implementation**:
1. Buffer all text during parsing (`_text_buffer`)
2. Track style ranges as `(start, end, style)` tuples (`_deferred_styles`)
3. Generate ONE `insertText` with complete plain text
4. Generate `updateTextStyle` for each tracked range

**Code Changes**:
- `_insert_text()` now buffers text instead of generating requests
- `_push_style()` records buffer position when style starts
- `_pop_style()` records completed range for deferred application
- `_merge_deferred_styles()` combines overlapping ranges
- `convert()` generates single insert + style requests at the end

**Generated Requests for "Here is **bold** text"**:
```python
[
    {"insertText": {"text": "Here is bold text\n", "location": {"index": 1}}},
    {"updateTextStyle": {"range": {"startIndex": 9, "endIndex": 13}, "textStyle": {"bold": True}, "fields": "bold"}}
]
```

**Result**: ✅ WORKS - Verified 2026-02-03 with multiple visual tests.

**Unit Tests**: 458/458 passing
**Visual Tests**: All passed (simple bold, multiple styles, adjacent styles, kitchen sink)

---

## Current State of the Code

### Key Files
- `gdocs/markdown_parser.py` - Markdown to Google Docs request converter
- `gdocs/writing.py` - `create_doc` and `insert_markdown` tools
- `tests/unit/gdocs/test_markdown_parser.py` - Unit tests

### Data Structures
```python
self._text_buffer: str = ""  # Accumulated plain text
self._deferred_styles: list[tuple[int, int, dict]] = []  # (start, end, style)
self._style_start_positions: list[tuple[int, dict]] = []  # Track open styles
```

### Request Order in convert()
```python
return (
    insert_requests           # Single insertText with all content
    + table_text_requests     # Table cell content
    + deferred_style_requests # Inline styles (bold, italic, links)
    + other_style_requests    # Code block, blockquote styles
    + para_requests           # Paragraph formatting
    + bullet_requests         # List bullets
    + table_requests          # Table structure
    + image_requests          # Inline images
)
```

---

## Resolution

**The Single-Insert Architecture (Approach 6) WORKS.**

### Why It Works

The root cause of style bleeding was **sequential text insertion with interleaved styling**:

```
❌ OLD APPROACH (caused bleeding):
1. insertText("Normal ")
2. insertText("bold")
3. updateTextStyle([8,12], bold=True)  ← Style applied immediately
4. insertText(" normal")               ← New text inherits bold from adjacent text!
```

The Google Docs API inherits styles from adjacent text when inserting. By inserting text piece by piece and applying styles in between, subsequent text fragments inherited the style of previously styled text.

```
✅ NEW APPROACH (works correctly):
1. insertText("Normal bold normal\n")  ← ALL text inserted first as plain
2. updateTextStyle([8,12], bold=True)  ← Style applied to existing range only
```

By inserting ALL text in a single operation, then applying styles to specific ranges within that already-inserted text, there's no opportunity for style inheritance between fragments.

### Key Implementation Details

1. **Buffer all text** during Markdown parsing into `_text_buffer`
2. **Track style ranges** as `(start, end, style)` tuples in `_deferred_styles`
3. **Generate ONE `insertText`** request with the complete buffer
4. **Generate `updateTextStyle`** requests for each tracked range

### Visual Testing Confirmation (2026-02-03)

- Simple bold: ✅
- Multiple styles (bold + italic): ✅
- Adjacent styles: ✅
- Kitchen sink typography: ✅

The issue was previously marked as unresolved based on incomplete testing. 
Full visual verification confirms the fix is working correctly.

### Test Documents Created (2026-02-03 Verification)

| Test | Doc ID | Result |
|------|--------|--------|
| Raw API (No Reset) | `1IZYYorVz0uOWND2PK9DSS8ayBzWgxPO5eET54Orgsks` | ✅ Pass |
| Raw API (Approach 3) | `1MZbL2eJ9rqhArpuetcMvV-l2r-VrQ7x-LM_Dsbww2oY` | ✅ Pass |
| Markdown Parser Simple | `1vjpOPLhxM0bvKELpi0aQcdf3CrEXMLv7vUwh6g07u04` | ✅ Pass |
| Markdown Parser Multiple | `1uexQJpDvHzM0a6nc7ZfzupVGlPy8Lo0pyAyhYNKZH0o` | ✅ Pass |
| Markdown Parser Adjacent | `11zymORDlIP8dMsFlbiu1wDoX6mWVzvN5ee45mR1p_zo` | ✅ Pass |
| Kitchen Sink Typography | `16SAH0P3BZ7HEGTTeGtSIEkMD-BBLFYXO5VUdrqPe_1M` | ✅ Pass |

---

## Test Documents Created

| Version | Doc ID | Approach |
|---------|--------|----------|
| V1 | `1r0QjunzMnDuuls-BI1f5wx-HWdpc6El3hEC1E96eA6g` | Single-char reset |
| V2 | `1IzJ1SLigJsG6cW3XZG_xiGCo8EWktPcqOSlii8r7CJI` | Full range reset |
| V3 | `1WsIszafEwE688Bf-SfyPzzAY0zq1cIo7ay_33ORihGQ` | Two batch approach |
| V4 | `1MzuDSrbrKKSm2PX5G88OsJeLNMPxtXfz7o3eWxivG_M` | Reset before style |

---

## Recommended Next Steps

1. **Use Google Docs API Explorer** to manually test requests and observe behavior
   - https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate

2. **Read the full Google Docs API documentation** for `updateTextStyle`
   - Pay attention to "fields" mask behavior
   - Check if there are style inheritance rules we're missing

3. **Examine actual document structure** after creation
   - Use `documents.get()` to retrieve the document and inspect its internal structure
   - Look for unexpected style runs or paragraph styles

4. **Test minimal reproduction case**
   - Create the simplest possible batchUpdate that should work
   - One insertText + one updateTextStyle for a substring

5. **Check if the issue is with the "fields" parameter**
   - Maybe we need to explicitly set more fields (e.g., `bold,italic,underline,strikethrough`)

6. **Investigate paragraph vs character styles**
   - Google Docs has both paragraph styles and character (text) styles
   - Maybe we need to reset at the paragraph level too

---

## Key Files to Read

1. `gdocs/markdown_parser.py` - Current converter implementation
2. `gdocs/writing.py` - How requests are sent to API
3. `tests/unit/gdocs/test_markdown_parser.py` - What the tests verify
4. This file - All failed approaches

---

## Contact

This investigation was conducted across multiple sessions. The style bleeding issue remains unresolved after 6 distinct approaches.
