#!/usr/bin/env python3
"""
Diagnostic Script: Bold Style Bleed Investigation

Run with: uv run python scripts/diagnose_bold_bleed.py
"""

import importlib.util
import json
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "markdown_parser", os.path.join(project_root, "gdocs", "markdown_parser.py")
)
if spec is None or spec.loader is None:
    raise ImportError("Could not load markdown_parser module")
markdown_parser_module = importlib.util.module_from_spec(spec)
sys.modules["markdown_parser"] = markdown_parser_module
spec.loader.exec_module(markdown_parser_module)
MarkdownToDocsConverter = markdown_parser_module.MarkdownToDocsConverter


def test_parser_only():
    """Test 1: Parser output without hitting API."""
    print("=" * 60)
    print("TEST 1: Parser Output Analysis")
    print("=" * 60)

    # Minimal test case
    markdown = "Normal **bold** normal"
    print(f"\nInput Markdown: {markdown!r}")
    print("Expected: 'Normal ' (normal) + 'bold' (bold) + ' normal' (normal)")

    converter = MarkdownToDocsConverter()
    requests = converter.convert(markdown)

    print(f"\nGenerated {len(requests)} requests:")
    for i, req in enumerate(requests):
        req_type = list(req.keys())[0]
        print(f"\n[{i}] {req_type}:")
        print(json.dumps(req, indent=2))

    # Validate ranges
    print("\n" + "-" * 40)
    print("VALIDATION:")

    # Find the insertText request
    insert_req = next((r for r in requests if "insertText" in r), None)
    if insert_req:
        text = insert_req["insertText"]["text"]
        print(f"  Inserted text: {text!r}")
        print(f"  Text length: {len(text)}")

    # Find bold style request
    bold_req = next(
        (
            r
            for r in requests
            if "updateTextStyle" in r and r.get("updateTextStyle", {}).get("textStyle", {}).get("bold")
        ),
        None,
    )
    if bold_req:
        style_info = bold_req["updateTextStyle"]
        start = style_info["range"]["startIndex"]
        end = style_info["range"]["endIndex"]
        print(f"  Bold range: [{start}, {end})")

        # Calculate what text this covers
        if insert_req:
            # Adjust for start_index=1 (index in request is 1-based)
            text = insert_req["insertText"]["text"]
            loc = insert_req["insertText"]["location"]["index"]
            rel_start = start - loc
            rel_end = end - loc
            if 0 <= rel_start < len(text) and 0 <= rel_end <= len(text):
                styled_text = text[rel_start:rel_end]
                print(f"  Text styled as bold: {styled_text!r}")
            else:
                print(f"  ERROR: Range [{rel_start}, {rel_end}) outside text bounds!")
    else:
        print("  WARNING: No bold style request found!")

    return requests


def analyze_expected_vs_actual():
    """Test 2: Show expected vs actual behavior."""
    print("\n" + "=" * 60)
    print("TEST 2: Expected vs Actual Analysis")
    print("=" * 60)

    # What we expect
    print("\nEXPECTED DOCUMENT STATE:")
    print("  Char 0-6:   'Normal ' -> normal style")
    print("  Char 7-10:  'bold'    -> bold style")
    print("  Char 11-17: ' normal' -> normal style")

    # What probably happens
    print("\nPROBABLE ACTUAL STATE (based on user reports):")
    print("  Char 0-6:   'Normal ' -> normal style")
    print("  Char 7-17:  'bold normal' -> bold style (BLEEDING!)")

    print("\nHYPOTHESIS:")
    print("  Google Docs API may require explicit style=False to reset,")
    print("  rather than just applying style=True to a subset.")


def suggest_next_test():
    """Suggest what to test next with the API."""
    print("\n" + "=" * 60)
    print("RECOMMENDED NEXT STEP: API Test")
    print("=" * 60)

    print("""
To verify this, we need to:

1. Create a test document using the actual API
2. Retrieve it with documents.get()
3. Inspect the 'content' array for textRun elements with textStyle

The key question is: Does the API return multiple textRun elements
with different styles, or does the bold style extend beyond our range?

PROPOSED TEST (requires running MCP server):

```python
# Create minimal doc
create_doc(
    title="Bold Bleed Test",
    content="Normal **bold** normal",
    parse_markdown=True
)

# Then retrieve with documents.get() and inspect body.content
```

MANUAL API TEST (using curl/API Explorer):

1. Create doc with:
   - insertText("Normal bold normal", index=1)
   - updateTextStyle(range=[8,12], bold=True)

2. GET the document and examine:
   - content[].paragraph.elements[].textRun.content
   - content[].paragraph.elements[].textRun.textStyle
""")


def test_explicit_reset_approach():
    """Show what explicit reset requests would look like."""
    print("\n" + "=" * 60)
    print("TEST 3: Explicit Reset Approach (Hypothesis)")
    print("=" * 60)

    print("""
If the bleeding is caused by style inheritance, the fix might be:

CURRENT APPROACH:
  1. insertText("Normal bold normal\\n", index=1)
  2. updateTextStyle(range=[8,12], bold=True)

PROPOSED FIX - Explicit Reset:
  1. insertText("Normal bold normal\\n", index=1)
  2. updateTextStyle(range=[1,END], bold=False)  # Reset ALL text first
  3. updateTextStyle(range=[8,12], bold=True)    # Then apply desired style

Or maybe we need to reset AFTER applying bold:
  1. insertText("Normal bold normal\\n", index=1)
  2. updateTextStyle(range=[8,12], bold=True)
  3. updateTextStyle(range=[12,END], bold=False)  # Explicit reset after

Let's create a test document to verify which approach works.
""")


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# BOLD STYLE BLEED DIAGNOSTIC")
    print("#" * 60)

    test_parser_only()
    analyze_expected_vs_actual()
    test_explicit_reset_approach()
    suggest_next_test()

    print("\n" + "#" * 60)
    print("# END DIAGNOSTIC")
    print("#" * 60)
