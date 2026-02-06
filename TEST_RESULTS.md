# Test Results: Google Docs Markdown Formatting

**Date:** Feb 02, 2026
**Version:** v0.0.21 (First Integration Test)

## Summary
**Status:** 🔴 FAILED
**Blocker:** `HttpError 400` on Table Insertion.

## Issue 1: Table Index Miscalculation
**Error Message:**
> `Invalid requests[127].insertText: The insertion index must be inside the bounds of an existing paragraph.`

**Context:**
The error occurred at request #127, which corresponds to the table population logic in the "Kitchen Sink" test file.

**Root Cause Analysis (Hypothesis):**
The `MarkdownToDocsConverter._handle_table_close` method uses a "Best Effort" formula to calculate the index of each cell:
`base_cell_index = table_start + 4 + r * (2 * cols + 1) + c * 2 + text_offset`

This formula assumes a rigid, predictable structure for Google Docs tables (e.g., that every cell consumes exactly 2 indices plus content). The error suggests this assumption is incorrect, or we are trying to insert text into a location that doesn't "exist" yet as a valid paragraph cursor.

**Code Reference:**
`gdocs/markdown_parser.py`: `_handle_table_close` method.

## Issue 2: List Style Inheritance ("The Bleed")
**Status:** 🔴 CONFIRMED
**Observation:**
Once a list starts, subsequent non-list elements (Headings, Code Blocks, Paragraphs) effectively "inherit" the list style. They appear with bullets or indentation, as if they are part of the list.
**Visual Proof:** In the screenshot, "4. Code Blocks" and "5. Blockquotes" have bullets next to them.
**Root Cause:**
Google Docs paragraphs inherit the style of the previous paragraph when a newline is inserted. If we don't explicitly *remove* the bullet preset (using `deleteParagraphBullets`) for the new paragraph, it continues the list.

## Issue 3: Table Support Disabled
**Status:** 🔴 OPEN
**Context:** Tables are currently commented out in the test file to allow other features to be verified. Fix for Issue 1 is required to enable tables.

## Recommendation for Fix
1.  **Fix List Inheritance (High Priority):**
    *   Modify `gdocs/markdown_parser.py` to detect when we transition from a *List* block to a *Non-List* block.
    *   Generate a `deleteParagraphBullets` request for the range of the new non-list paragraph.
2.  **Fix Table Math (High Priority):**
    *   Adopt the `TableOperationManager` logic or refine the index formula.
