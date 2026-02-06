# Testing Plan: Google Docs Markdown Formatting (E2E)

This plan verifies that the MCP server correctly translates Markdown into native Google Docs formatting.

## Implementation Status

**Last Updated:** 2026-02-03

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0-4 | Core parser, tests, tool integration, tables | **Complete** |
| Phase 5 | Bug fixes (table +3 offset, list bleed) | **Complete** |
| Phase 6 | Enhancements (HR, strikethrough, images, task lists) | **Complete** |
| Phase 5.5 | Style bleed fix (two-phase ordering) | **Complete** |
| Phase 5.6 | List nesting fix (TAB-based + index adjustment) | **Complete** |
| **Unit Tests** | 442 tests passing | **All Pass** |

### Bug Fixes Applied
- [x] **FIX_TABLE_MATH.md**: Changed table cell offset from +4 to +3
- [x] **FIX_LIST_BLEED.md**: Added `deleteParagraphBullets` emission after list exit
- [x] **FIX_STYLE_BLEED.md**: Two-phase request ordering (inserts first, styles in reverse)
- [x] **FIX_LIST_NESTING.md**: Single batchUpdate + TAB index adjustment for multi-list docs

---

## Prerequisites
1.  **OpenCode** running with the latest `gws-mcp-advanced` server.
2.  **Kitchen Sink File:** `tests/manual/kitchen_sink.md` (Already created).

---

## Test Procedure

### Step 1: Create the Document
Use the MCP tool directly in OpenCode:

```
create_doc(
    title="Kitchen Sink Test - Native Markdown",
    content=<contents of tests/manual/kitchen_sink.md>,
    parse_markdown=True
)
```

**Expected Output:**
> Created Google Doc 'Kitchen Sink Test - Native Markdown' (ID: ...) with Markdown formatting. Link: https://...

### Step 2: Visual Verification Checklist

Open the link provided in the output.

#### Core Features

| Section | Feature | Expected Visual Result | Status |
| :--- | :--- | :--- | :--- |
| **1. Typography** | Bold | Text **bold** is visually heavier. | ✅ **PASS** |
| | Italic | Text *italic* is slanted. | ✅ **PASS** |
| | Mixed | Text ***bold and italic*** is both. | ✅ **PASS** |
| | Style Isolation | Each style ends at closing marker. | ✅ **PASS** (Verified 2026-02-03) |
| | Link | "link to Google" is blue, underlined, and clickable. | ✅ **PASS** |
| | Inline Code | `inline code` has Consolas font. | ✅ **PASS** (font only, no box) |
| **2. Headings** | Hierarchy | H2 > H3 > H4 > H5 > H6 (decreasing size). | ✅ **PASS** |
| | Outline | Headings appear in Google Docs "Outline" sidebar. | ✅ **PASS** |
| **3. Lists** | Unordered | Bullets indented correctly (Level 1 → 2 → 3). | ✅ **PASS** (Fixed 2026-02-03) |
| | Ordered | Numbers with proper sub-numbering (1, 2, a, b, i). | ✅ **PASS** (Fixed 2026-02-03) |
| | **List Bleed** | Heading after list has NO bullet. | ✅ **PASS** |
| **4. Code Blocks** | Font | Monospace font (Consolas). | ✅ **PASS** |
| | Background | Gray background box with border. | ❌ **FAIL** - No background/border |
| | Language Label | Shows language name (e.g., "Java"). | ❌ **FAIL** - Not implemented |
| | Syntax Highlighting | Color-coded keywords. | ❌ **FAIL** - Not implemented |
| **5. Blockquotes** | Style | Indented with left border bar. | ✅ **PASS** |
| **6. Tables** | Structure | 3×4 table exists (3 columns, 4 rows including header). | ❌ **FAIL** - API index error |
| | Headers | First row text is **bold**. | ❌ Not Tested |
| | Cell Content | All cells populated correctly. | ❌ Not Tested |

#### Phase 6 Features (Optional Enhancements)

| Feature | Syntax | Expected Result | Status |
| :--- | :--- | :--- | :--- |
| **Horizontal Rule** | `---` | Gray bottom border separator line. | ✅ **PASS** |
| **Strikethrough** | `~~text~~` | Text with line through it. | ✅ **PASS** |
| **Images** | `![alt](url)` | Image displayed inline. | ❌ Not Tested |
| **Task Lists** | `- [ ]`, `- [x]` | ☐ unchecked, ☑ checked checkboxes. | ✅ **PASS** |

### Known Issues (Updated 2026-02-03)

| Issue | Severity | Spec | Status |
| :--- | :--- | :--- | :--- |
| **Style bleed** - Bold extends past marker | **CRITICAL** | `specs/FIX_STYLE_BLEED.md` | ✅ **FIXED** |
| Nested list indentation broken | HIGH | `specs/FIX_LIST_NESTING.md` | ✅ **FIXED** |
| Ordered sub-list numbering continues parent | HIGH | `specs/FIX_LIST_NESTING.md` | ✅ **FIXED** |
| Code blocks missing background/border | MEDIUM | `specs/FIX_CODE_BLOCKS.md` | ❌ Open |
| Code blocks missing language label | LOW | `specs/FIX_CODE_BLOCKS.md` | ❌ Open |
| Blockquotes not indented with border | MEDIUM | `specs/FIX_BLOCKQUOTES.md` | ✅ **FIXED** |
| Table cell index calculation fails | HIGH | `specs/FIX_TABLE_MATH.md` | ❌ Open |
| Extra empty bullet after task lists | LOW | - | ❌ Open |

### Step 3: Debugging (If Visuals Fail)

1.  **Run the Trace Script:**
    ```python
    from gdocs.markdown_parser import MarkdownToDocsConverter
    import json

    with open("tests/manual/kitchen_sink.md", "r") as f:
        md = f.read()

    converter = MarkdownToDocsConverter()
    requests = converter.convert(md)
    
    print(json.dumps(requests, indent=2))
    ```

2.  **Common Issues:**
    - Index out of bounds → Check table math offset
    - List bullets on headings → Check `deleteParagraphBullets` requests
    - Missing styles → Verify range includes trailing newline

---

## Extended Kitchen Sink (Phase 6 Features)

To test Phase 6 features, append to `kitchen_sink.md`:

```markdown
## 8. Horizontal Rules

Above the line.

---

Below the line.

## 9. Strikethrough

This text is ~~crossed out~~ strikethrough.

## 10. Task Lists

- [ ] Unchecked task
- [x] Completed task
- [ ] Another pending task

## 11. Images

![Sample Image](https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png)
```

---

## Test Execution Log

| Date | Test | Result | Notes |
|------|------|--------|-------|
| 2026-02-03 | Unit Tests | **442 Pass** | `uv run pytest` |
| 2026-02-03 | Style Bleed - Simple Bold | ✅ **PASS** | `1vjpOPLhxM0bvKELpi0aQcdf3CrEXMLv7vUwh6g07u04` |
| 2026-02-03 | Style Bleed - Multiple Styles | ✅ **PASS** | `1uexQJpDvHzM0a6nc7ZfzupVGlPy8Lo0pyAyhYNKZH0o` |
| 2026-02-03 | Style Bleed - Adjacent Styles | ✅ **PASS** | `11zymORDlIP8dMsFlbiu1wDoX6mWVzvN5ee45mR1p_zo` |
| 2026-02-03 | Kitchen Sink Typography | ✅ **PASS** | `16SAH0P3BZ7HEGTTeGtSIEkMD-BBLFYXO5VUdrqPe_1M` |
| 2026-02-03 | Full Kitchen Sink (No Tables) | **Partial** | `1lwPPBVNg0tw_Wf8P8gcOGvmeFzJ2nZ58U-aiOO-Hmhw` |
| | - Typography & Headings | ✅ **PASS** | All styles work correctly |
| | - Lists | ✅ **PASS** | Nesting fixed |
| | - Code Blocks | ❌ **FAIL** | Missing background/border |
| | - Blockquotes | ✅ **PASS** | Gray left border, indentation, italic |
| 2026-02-03 | Blockquote Visual Verification | ✅ **PASS** | `1zT9I4CtBILCv0CYwPDBVpqOD-hEpEiaBfInSduJ8UWc` |
| 2026-02-03 | Multi-List Nesting Test | ✅ **PASS** | `16WZh13RfNI6TI-mjHvGLoh1wvJxPosu3Ylj3L-RcVto` |
| 2026-02-03 | Final Nesting Verification | ✅ **PASS** | `1q2BRjd6OgBFB_lVrbVD2Mpz8D8UbFYztMLMb5SBsxmY` |

---

## Next Steps

1. ~~Run E2E test with `create_doc` tool~~ Done
2. ~~Visually verify checklist items~~ Done  
3. ~~Update status in checklist above~~ Done
4. ~~**Fix list nesting bug**~~ **DONE** - See `specs/FIX_LIST_NESTING.md`
5. **Fix code blocks** - Add background box, border, language label - See `specs/FIX_CODE_BLOCKS.md`
6. ~~**Fix blockquotes** - Add left border bar and proper indentation~~ **DONE** - See `specs/FIX_BLOCKQUOTES.md`
7. **Fix table index calculation** - Revisit `specs/FIX_TABLE_MATH.md`
8. Re-test after fixes

---

## Roadmap

| Feature | Priority | Description |
|---------|----------|-------------|
| Header customization config | LOW | Allow users to define font size, font family, and style for H1-H6 |
| Syntax highlighting | LOW | Color-coded keywords in code blocks |
