# Spec: Fix Code Blocks

**Goal:** Make code blocks visually match standard rendering (background box, border, optional language label)
**Severity:** MEDIUM
**Status:** Open

## Current Behavior

Code blocks are rendered with:
- ✅ Monospace font (Consolas)
- ❌ No background color/box
- ❌ No border
- ❌ No language label

## Expected Behavior

Code blocks should have:
- Monospace font (Consolas)
- Light gray background (#f5f5f5)
- Rounded border
- Optional: Language label in top-left (e.g., "python", "javascript")

## Visual Reference

**Current:**
```
def hello_world():
    print("No background")
```

**Expected:**
```
┌─ python ──────────────────────┐
│ def hello_world():            │
│     print("With background")  │
└───────────────────────────────┘
```

## Implementation Options

### Option 1: Paragraph Style (Simpler)
Apply `updateParagraphStyle` with:
- `shading.backgroundColor` for background
- `borderLeft`, `borderRight`, `borderTop`, `borderBottom` for border

### Option 2: Table-based (More Control)
Insert a 1x1 table with:
- Cell background color
- Cell border styling
- Code text inside cell

### Option 3: Keep Current (Accept Limitation)
Google Docs doesn't support true code blocks. Current Consolas font may be acceptable.

## Decision Needed

Which approach should we implement?

## Files to Modify

- `gdocs/markdown_parser.py` - `_handle_code_block()` method
