# Spec: Fix List Nesting and Numbering

**Goal:** Fix nested list indentation and ordered list sub-numbering.
**Severity:** HIGH
**Status:** FIXED (2026-02-03)
**Context:** Visual testing revealed that nested lists do not indent correctly, and ordered sub-lists continue parent numbering instead of restarting.

---

## SOLUTION IMPLEMENTED (2026-02-03)

**The Google Docs API uses LEADING TAB CHARACTERS to determine nesting level.**

From the official API documentation for `CreateParagraphBulletsRequest`:

> "The nesting level of each paragraph will be determined by counting leading tabs in front of each paragraph. To avoid excess space between the bullet and the corresponding paragraph, these leading tabs are removed by this request. This may change the indices of parts of the text."

### Final Working Implementation

**Two bugs were identified and fixed:**

#### Bug 1: Split BatchUpdate Calls (FIXED)

**Problem:** `create_doc` in `gdocs/writing.py` was splitting requests into two separate `batchUpdate` calls - one for text insertion, another for styles. This broke TAB-based nesting because indices shifted between calls.

**Fix:** Modified `gdocs/writing.py` to send ALL requests in a SINGLE `batchUpdate` call.

#### Bug 2: Index Shifting Across Multiple Lists (FIXED)

**Problem:** When multiple lists exist in a document, each `createParagraphBullets` removes TABs, shifting all subsequent indices. Later bullet requests used stale indices.

**Example:**
```
Request [4]: createParagraphBullets [39, 150] - removes 4 TABs
Request [6]: createParagraphBullets [163, 216] - uses STALE indices!

After [4] removes 4 TABs, all indices > 150 shift by -4.
Request [6] should use [159, 212] not [163, 216].
```

**Fix:** Added `_adjust_bullet_indices_for_tab_removal()` method in `gdocs/markdown_parser.py` that:
1. Tracks cumulative TAB count removed by each `createParagraphBullets` request
2. Adjusts subsequent bullet request indices accordingly
3. Called in `convert()` before returning the final request list

### Verified Working Test Documents

| Document | Link | Result |
|----------|------|--------|
| Single List | `1CStN2o_bY2TrtNKEkL9v9B3sYcsxmumUjOa-ImrDh6s` | 3-level nesting works |
| Multi-List | `16WZh13RfNI6TI-mjHvGLoh1wvJxPosu3Ylj3L-RcVto` | Multiple lists with nesting |
| Final Test | `1q2BRjd6OgBFB_lVrbVD2Mpz8D8UbFYztMLMb5SBsxmY` | Unordered + Ordered nested |

### How TAB-Based Nesting Works

- 0 TABs = Level 1 (● or 1.)
- 1 TAB = Level 2 (○ or a.)
- 2 TABs = Level 3 (■ or i.)
- The API removes TABs after processing and applies correct `nestingLevel`

### Key Implementation Details

**In `markdown_parser.py`:**

1. `_insert_text()` prepends TABs based on `len(self._list_type_stack) - 1`
2. `_apply_top_level_list_bullets()` applies bullets to entire list range at once
3. `_adjust_bullet_indices_for_tab_removal()` corrects indices for multi-list documents

**In `writing.py`:**

1. `create_doc()` sends ALL requests (insertText + styles + bullets) in ONE `batchUpdate`

### Note on Indentation Spacing

Google Docs applies default indentation (~36pt per level) which appears wide. Attempts to narrow this via `updateParagraphStyle` with custom `indentStart` values broke the nesting hierarchy. The default spacing is acceptable and preserves correct nesting behavior.

---

## Original Issue Description

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

**Actual (Before Fix):**
- All items appeared at the same level

### Issue B: Ordered List Numbering
**Input:**
```markdown
1. Step One
2. Step Two
   1. Sub-step A
   2. Sub-step B
3. Step Three
```

**Expected:** 1, 2, (a, b), 3

**Actual (Before Fix):** 1, 2, 3, 4, 5 (flat numbering)

---

## Files Modified

| File | Change |
|------|--------|
| `gdocs/writing.py` | Single batchUpdate call for all requests |
| `gdocs/markdown_parser.py` | Added `_adjust_bullet_indices_for_tab_removal()` method |

## References

- Google Docs API: [CreateParagraphBullets](https://developers.google.com/docs/api/reference/rest/v1/documents/request#CreateParagraphBulletsRequest)
- Key quote: "The nesting level of each paragraph will be determined by counting leading tabs"
