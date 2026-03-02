# OP-70 Kitchen Sink Visual Inspection Evidence

## Mitigation Status
- `2026-03-02T08:10:58Z`: DEF-013 mitigation has been implemented in code (shared markdown path refactor in `gdocs/markdown_parser.py` and phased execution update in `gdocs/writing.py`) and fully validated locally (`ruff`, `pyright`, `pytest`: `609 passed`, `3 skipped`).
- OP-70 remains `FAIL` until OpenCode reruns the manual visual kitchen-sink inspection on the updated MCP subprocess.
- `2026-03-02T08:28:33Z`: OP-70 executed (Attempt 4). Result: **FAIL**. The API error was resolved and the document generated completely, however, the **exact same visual issues from Attempt 1 are still present**:
  - The table content has an incorrectly large font size (matches H2 instead of normal text).
  - Missing empty lines around the "Empty Lines Below" header and horizontal rule.
  - Strikethrough text is misaligned onto the wrong words.
  - Task lists and images are now CORRECT.
  - **Conclusion:** The post-table index calculation logic is still flawed for spacing and minor formatting boundaries. Handing over to implementation agent for a deeper fix.

- `2026-03-02T10:00:00Z`: OP-70 executed (Attempt 2). Result: **FAIL**. The `create_doc` tool threw an API error during `batchUpdate`: `Invalid requests[0].deleteContentRange: Index 1041 must be less than the end index of the referenced segment, 1038`. The document could not be formatted properly. DEF-013 remains In Progress.
- `2026-03-02T09:11:36Z`: Codex implemented the Attempt-4 residual fix set in code:
  - source-map blank-line preservation for top-level blocks,
  - explicit table block paragraph termination after placeholder insertion,
  - table-cell baseline style enforcement (`fontSize=11`, header-only bold) during population.
  Local verification is green (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q` -> `615 passed`, `3 skipped`). Awaiting fresh OP-70 rerun after OpenCode restart.

## Document Title
- H1 (`#`) correctly mapped to Google Docs `HEADING_1` (since Markdown doesn't have a distinct "Title" block type, this is correct/expected).

## 1. Typography
- PASS: All styles render perfectly. 
- Bold, italic, and bold+italic applied to correct words.
- Link is active.
- Inline code has monospace styling and background shading.
- *Crucial fix verified*: Formatting no longer leaks into subsequent characters/words.

## 2. Headings (Hierarchy)
- PASS: Google Docs default heading styles are correctly applied.
- H2 -> H6 hierarchy is visually distinct (decreasing font size, changing colors/italics for lower levels).

## 3. Lists
- PASS: Both Unordered and Ordered lists are rendered correctly.
- Unordered: Proper bullet progression (solid circle -> open circle -> square) and indentation for nested levels.
- Ordered: Proper numeral/letter progression (1, 2, 3 -> a, b) and indentation for nested levels.

## 4. Code Blocks
- PASS: Fenced code block is rendered correctly.
- Monospaced text is preserved with correct line breaks/indentation.
- Box styling (light gray background, thin border) is correctly applied.
- Language label ("python") is positioned at the top and styled nicely (bold).

## 5. Blockquotes
- PASS: Rendered with the correct blockquote styling.
- Includes the standard left-hand vertical bar, indentation, and italicized text.

## 6. Tables
- PARTIAL PASS: The 3x3 table is correctly generated, with emojis properly retained. The header row is correctly styled in bold.
- DEFECT (Minor): The text "Low" in the final cell is rendered in bold, despite not being bolded in the Markdown source (`| Lists | ✅ Stable | Low |`). This indicates a style bleeding or state-reset issue during table population.

## 7. Edge Cases
- FAIL: Severe formatting drift and block-level misalignment. As noted, the text index and formatting index have drifted apart significantly following the table section.
- Text "7. Edge Cases" should be an H2, but "7. Edge " is bold, and "Cases" is normal text.
- Text "Mixed Content" should be an H3, but "Mixed " is italicized, and "Content" is normal text.
- The line "**Bold Header** with *italic* text inside." is rendered inside a bulleted list item, but in the Markdown, it is a standalone paragraph.
- Inside that line, "Bold Header with ital" is normal text, and "ic text" is bolded (formatting boundaries are shifted).
- The line "- List item with **bold** text" renders as "List item `with` bold text", where "with" is styled as inline code (gray background/monospace), and the rest is normal text.
- The line "- List item with `code` inside" renders as a standalone paragraph (not a list item), with normal text, no code styling.
- The heading "### Empty Lines Below (Spacing Test)" renders as normal paragraph text.
- The text "(There should be spacing above this line)" renders much larger than normal text (taking on the H3 size that was supposed to apply to the heading above it).
- Root Cause Hypothesis: This indicates a major index/offset calculation bug in `gdocs/markdown_parser.py`. The text and formatting indices desync, highly likely triggered by the Table parsing logic preceding this section.

## 8. Horizontal Rules
- PARTIAL PASS: The horizontal rule itself is rendered correctly as a continuous line between the two paragraphs.
- DEFECT (Formatting Drift): The heading "8. Horizontal Rules" is rendered as normal text (or slightly enlarged, but not an H2), and the text "Below the line." is rendered as a large heading (likely an H2 that was supposed to be applied earlier). This confirms that the index drift issue from Section 7 continues to cascade through the rest of the document.

## 9. Strikethrough
- FAIL: Formatting drift is present here as well.
- The strikethrough styling (intended for the word "crossed out" in the paragraph below) is applied to "9. Strike" in the heading instead.
- The heading formatting (H2) intended for "9. Strikethrough" has shifted down into the paragraph, causing "This text is crossed out and this is normal." to render as an H2.

## 10. Task Lists
- FAIL: Formatting drift and structural issues.
- The H2 heading "10. Task Lists" has been incorrectly styled as a bullet point.
- The checkboxes (☐ and ☑) are correctly inserted as text, but they are rendered *inside* an unordered list, resulting in a double-bullet effect (a solid circle bullet followed by the checkbox).
- The intended behavior was for the checkboxes to replace the bullet points entirely (or just be normal text on a line, depending on how Google Docs handles task lists natively via API, but definitely not nested inside a standard bulleted list).

## 11. Images
- PARTIAL PASS: The image itself is correctly fetched via URL and inserted into the document inline.
- FAIL (Positioning Drift): The image is inserted in the middle of the task list, above the "11. Images" header, and seemingly interrupting the final list item. This is further confirmation of the underlying index offset bug: because `create_doc` relies on predicting absolute indices for element insertion (like images), if earlier complex elements (like tables) disrupt the text buffer length prediction, the image will be inserted at the wrong absolute index.
## Attempt 3 Observations


### Header & Sections 1 - 5
- PASS: Document Title, Typography, Headings (Hierarchy), Lists (Unordered/Ordered), Code Blocks, and Blockquotes all render perfectly, identically to Attempt 1.

### Section 6 (Tables)
- PARTIAL PASS: The "Low" bolding bug (style bleed inside the table) is FIXED. The heading "6. Tables" is correctly rendered as an H2. Emojis and structure remain correct.
- FAIL (Formatting Drift): The text *inside* the table cells is rendered with a larger font size (size 15, matching an H2 heading) instead of the standard normal text size (11).
### Section 7 (Edge Cases)
- PARTIAL PASS: The severe index drift observed in Attempt 1 is largely fixed! The H2 heading, H3 heading, mixed bold/italic text, and the nested inline code/bold within the list items all render perfectly now.
- FAIL (Spacing): The empty line in the markdown between `### Empty Lines Below (Spacing Test)` and `(There should be spacing above this line)` is missing in the output. The text immediately follows the heading without the intended vertical spacing.

### Sections 8 - 11
- PARTIAL PASS: Horizontal Rules, Task Lists, and Images all render perfectly now!
- Task lists no longer have double bullets (they just use the checkbox characters).
- The horizontal rule is placed perfectly.
- The inline image is placed precisely at the end below its heading without any weird drift.
- FAIL (Strikethrough Drift): The strikethrough is misaligned by a few characters. It crossed out "erossed ou", missing the "c" and hitting the "u", indicating a very slight index drift is still happening in this specific section.
- FAIL (Spacing): Similar to Edge Cases, the empty lines around the horizontal rule are swallowed.
---
**Conclusion**: The major index drift issue (DEF-013) that broke all formatting post-table in Attempt 1 has been solved. The remaining Attempt-4 items were narrowed to minor nuances:
1. Table cell content inherited H2-like sizing instead of normal text size.
2. Empty lines before/after horizontal rule and under "Empty Lines Below" were collapsed.
3. Strikethrough range appeared slightly offset (`erossed ou` vs `crossed out`).
4. The H3 headings in the "Edge Cases" section lost their formatting and rendered as normal text.


## Attempt 5 Observations

### Section 6 (Tables)
- PASS: Text *inside* the table cells is now standard font size 11. The incorrect H2 size inheritance bug is fixed.

### Section 7 (Edge Cases) & Section 8 (Horizontal Rules)
- PASS: The empty lines (vertical spacing) are now correctly present around the "Empty Lines Below" header and the horizontal rule. Swallowed newlines bug is fixed.

### Section 9 (Strikethrough)
- PASS: Strikethrough is perfectly aligned exactly on the words "crossed out".

### Headings (H3 fix validation)
- PASS: The "Mixed Content" and "Empty Lines Below (Spacing Test)" headings are now correctly styled as H3.

---
**Final Conclusion**: All issues (including major drift and minor formatting nuances) have been resolved. The document passes the Kitchen Sink test completely. `DEF-013` is closed.