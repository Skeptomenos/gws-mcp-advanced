# Spec: Fix Blockquotes

**Goal:** Make blockquotes visually distinct with left border and proper indentation
**Severity:** MEDIUM
**Status:** Complete ✅ (Verified 2026-02-03)

---

## Key Insight: No Native Blockquotes in Google Docs

**Google Docs has no semantic "blockquote" element.** Unlike HTML's `<blockquote>` or Word's built-in quote style, Google Docs only provides styling primitives.

### Our Approach: Style-Based Simulation

We simulate blockquotes using a combination of paragraph styling:

| Property | Purpose | Value |
|----------|---------|-------|
| `indentStart` | Push text away from left margin | 36 PT × nesting level |
| `indentFirstLine` | Match indent (no hanging indent) | Same as `indentStart` |
| `borderLeft` | Visual indicator (the "quote bar") | 3 PT solid gray line |
| `borderLeft.padding` | Space between bar and text | 12 PT |
| `italic` | Text style convention for quotes | Applied to all text |

### Why This Works

1. **`borderLeft`** - The Google Docs API supports paragraph borders on any side. We use only the left border to create the classic blockquote "bar" effect.

2. **`indentStart` + `indentFirstLine`** - Both must match to create a flush block indent. If only `indentStart` is set, the first line hangs differently.

3. **Per-paragraph application** - Each paragraph inside a blockquote gets styled independently. This means multi-paragraph blockquotes work correctly, and nested blockquotes stack indentation.

4. **Nesting via multiplication** - `indentStart = 36 PT × nesting_level` means:
   - Level 1: 36 PT indent
   - Level 2: 72 PT indent (and its own border)
   - Level 3: 108 PT indent

### Limitations

- **No semantic meaning** - Screen readers won't identify these as quotes
- **Border per paragraph** - Each line gets its own border segment (visually fine, but not a continuous bar across line breaks within a paragraph)
- **Manual cleanup needed** - If you later want to "unquote", you must remove both the border AND the indent

---

## Implementation Summary

| Change | File | Description |
|--------|------|-------------|
| Add constants | `gdocs/markdown_parser.py:53-57` | `BLOCKQUOTE_BORDER_*` constants |
| Update method | `gdocs/markdown_parser.py:536-580` | Add `borderLeft` and `indentFirstLine` to `_apply_blockquote_style()` |
| Add test | `tests/unit/gdocs/test_markdown_parser.py` | `test_blockquote_has_left_border` |

## Previous Behavior

Blockquotes were rendered with:
- ❌ No visible indentation (only `indentEnd` was set, not visually distinct)
- ❌ No left border bar
- ✅ Italic text (already implemented)

## Current Behavior (Fixed)

Blockquotes now have:
- ✅ Left border bar (3 PT gray vertical line)
- ✅ Indented text from left margin (36 PT per nesting level)
- ✅ Flush indentation for first line (`indentFirstLine` matching `indentStart`)
- ✅ Italic text
- ✅ Padding between border and text (12 PT)

## Visual Reference

```
│ This is a blockquote.
│ It should be indented with a left border.
```

## Google Docs API Request

```python
{
    "updateParagraphStyle": {
        "range": {"startIndex": start, "endIndex": end},
        "paragraphStyle": {
            "indentStart": {"magnitude": 36, "unit": "PT"},
            "indentFirstLine": {"magnitude": 36, "unit": "PT"},
            "borderLeft": {
                "color": {"color": {"rgbColor": {"red": 0.7, "green": 0.7, "blue": 0.7}}},
                "width": {"magnitude": 3, "unit": "PT"},
                "padding": {"magnitude": 12, "unit": "PT"},
                "dashStyle": "SOLID"
            }
        },
        "fields": "indentStart,indentFirstLine,borderLeft"
    }
}
```

## Test Results

| Date | Test Type | Result | Doc ID |
|------|-----------|--------|--------|
| 2026-02-03 | Unit tests | 459 passing | - |
| 2026-02-03 | E2E blockquote test (Round 1) | ❌ FAIL (No border) | `1me14fG2DY_ZnEbTjjLjUJVG58LdUYy7EV-uLG3YteWI` |
| 2026-02-03 | E2E blockquote test (Round 2) | ✅ PENDING VERIFICATION | `1q77FLbYDWjmQkkMWnmdr9cszi59h_ENVBFuw7Iib2b4` |
| 2026-02-03 | E2E visual verification | ✅ **PASS** | `1zT9I4CtBILCv0CYwPDBVpqOD-hEpEiaBfInSduJ8UWc` |

### Verified Features (2026-02-03)
- ✅ Simple blockquote with gray left border
- ✅ Nested blockquotes (L1 and L2 indentation)
- ✅ Inline formatting preserved (bold/italic inside blockquote)
- ✅ Multi-paragraph blockquotes
- ✅ No style bleeding to subsequent paragraphs

## Files Modified

- `gdocs/markdown_parser.py` - Added `borderLeft` and `indentFirstLine` to `_apply_blockquote_style()` method
- `tests/unit/gdocs/test_markdown_parser.py` - Added `test_blockquote_has_left_border` test

## Notes

- Added `indentFirstLine` which is critical for consistent block indentation
- Adjusted gray color to 0.7 for better visibility
- Verified unit tests pass with the new structure
