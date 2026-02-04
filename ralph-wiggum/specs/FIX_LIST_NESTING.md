# Spec: Fix List Nesting and Numbering

**Goal:** Fix nested list indentation and ordered list sub-numbering.
**Severity:** HIGH
**Context:** Visual testing revealed that nested lists do not indent correctly, and ordered sub-lists continue parent numbering instead of restarting.

## 1. Observed Issues

### Issue A: Nesting Indentation
**Input:**
```markdown
- Level 1 Item A
- Level 1 Item B
  - Level 2 Nested Item
  - Level 2 Nested Item
    - Level 3 Deep Nesting
- Level 1 Item C
```

**Expected:** 
- Level 1 items at root indentation
- Level 2 items indented one level
- Level 3 items indented two levels
- "Level 1 Item C" back at root

**Actual:**
- All nested items appear at inconsistent indentation
- "Level 1 Item C" appears nested instead of at root level

### Issue B: Ordered List Numbering
**Input:**
```markdown
1. Step One
2. Step Two
   1. Sub-step A
   2. Sub-step B
3. Step Three
```

**Expected:** 1, 2, (a, b or 1, 2), 3

**Actual:** 1, 2, 3, 4, 5 (flat numbering)

## 2. Root Cause Analysis

The `_apply_bullet_style()` method in `markdown_parser.py` calculates nesting level from `_list_type_stack` depth. However:

1. **Nesting Level Calculation:** The current formula may not account for markdown-it's token structure correctly.
2. **Google Docs Bullet Inheritance:** Each list item paragraph inherits the bullet preset, but nesting requires explicit `nestingLevel` in the bullet properties.
3. **Ordered Sub-lists:** Google Docs requires separate bullet presets or explicit nesting configuration for sub-numbered lists.

## 3. Proposed Fix

### 3.1 Update `_apply_bullet_style()` 

Instead of just setting `indentFirstLine`/`indentStart` for nested items, we need to use the `nestingLevel` property in `createParagraphBullets`:

```python
def _apply_bullet_style(self) -> None:
    nesting_level = len(self._list_type_stack) - 1
    list_type = self._list_type_stack[-1]
    
    bullet_preset = BULLET_PRESET_UNORDERED if list_type == "bullet" else BULLET_PRESET_ORDERED
    
    request = {
        "createParagraphBullets": {
            "range": {
                "startIndex": self._list_item_start_index,
                "endIndex": self.cursor_index,
            },
            "bulletPreset": bullet_preset,
        }
    }
    self.requests.append(request)
    
    # Apply nesting via updateParagraphStyle with bullet nesting
    if nesting_level > 0:
        nesting_request = {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": self._list_item_start_index,
                    "endIndex": self.cursor_index,
                },
                "paragraphStyle": {
                    "bulletAlignment": "START",  # May need adjustment
                },
                "fields": "bulletAlignment",
            }
        }
        # Note: Google Docs API nesting is complex - may need alternative approach
```

### 3.2 Alternative: Use List ID Tracking

Google Docs lists are identified by list IDs. To create proper nested lists:
1. Track the current list ID
2. Apply the same list ID to all items in the same logical list
3. Set `nestingLevel` for each item based on depth

This requires inspecting the document after list creation to get the list ID.

## 4. Verification

### Unit Tests
- `test_nested_unordered_list_indentation()`
- `test_nested_ordered_list_numbering()`
- `test_returning_to_root_level()`

### Visual Test
Re-run kitchen_sink.md and verify:
- Level 2 items are visually indented from Level 1
- Level 3 items are visually indented from Level 2  
- "Level 1 Item C" returns to root level
- Sub-step A/B show as sub-numbers (a, b) or restart at 1

## 5. References

- Google Docs API: [CreateParagraphBullets](https://developers.google.com/docs/api/reference/rest/v1/documents/request#CreateParagraphBulletsRequest)
- Google Docs API: [ParagraphStyle.bulletAlignment](https://developers.google.com/docs/api/reference/rest/v1/documents#ParagraphStyle)
