#!/usr/bin/env python3
"""
API Test: Bold Style Bleed

Tests different approaches to applying bold style and inspects results.
Run with: uv run python scripts/test_bold_api.py

You can use the MCP tool instead:
  create_doc(title="Bold Test V1", content="Normal **bold** normal", parse_markdown=True)

Then inspect with:
  get_doc_content(document_id="<doc_id>")
  inspect_doc_structure(document_id="<doc_id>", detailed=True)
"""

import json


def generate_approach_1_requests():
    """Current approach: Insert all text, then apply bold to range."""
    text = "Normal bold normal\n"
    return [
        {"insertText": {"text": text, "location": {"index": 1}}},
        {
            "updateTextStyle": {
                "range": {"startIndex": 8, "endIndex": 12},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        },
    ]


def generate_approach_2_requests():
    """Explicit reset before: Reset all to normal, then apply bold."""
    text = "Normal bold normal\n"
    end_index = 1 + len(text)
    return [
        {"insertText": {"text": text, "location": {"index": 1}}},
        {
            "updateTextStyle": {
                "range": {"startIndex": 1, "endIndex": end_index},
                "textStyle": {"bold": False},
                "fields": "bold",
            }
        },
        {
            "updateTextStyle": {
                "range": {"startIndex": 8, "endIndex": 12},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        },
    ]


def generate_approach_3_requests():
    """Explicit reset after: Apply bold, then reset text after."""
    text = "Normal bold normal\n"
    end_index = 1 + len(text)
    return [
        {"insertText": {"text": text, "location": {"index": 1}}},
        {
            "updateTextStyle": {
                "range": {"startIndex": 8, "endIndex": 12},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        },
        {
            "updateTextStyle": {
                "range": {"startIndex": 12, "endIndex": end_index},
                "textStyle": {"bold": False},
                "fields": "bold",
            }
        },
    ]


def generate_approach_4_requests():
    """Three-part styling: Before=normal, target=bold, after=normal."""
    text = "Normal bold normal\n"
    end_index = 1 + len(text)
    return [
        {"insertText": {"text": text, "location": {"index": 1}}},
        {
            "updateTextStyle": {
                "range": {"startIndex": 1, "endIndex": 8},
                "textStyle": {"bold": False},
                "fields": "bold",
            }
        },
        {
            "updateTextStyle": {
                "range": {"startIndex": 8, "endIndex": 12},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        },
        {
            "updateTextStyle": {
                "range": {"startIndex": 12, "endIndex": end_index},
                "textStyle": {"bold": False},
                "fields": "bold",
            }
        },
    ]


def print_requests(name: str, requests: list):
    """Print requests in a format suitable for API testing."""
    print(f"\n{'=' * 60}")
    print(f"APPROACH: {name}")
    print(f"{'=' * 60}")
    print(f"Total requests: {len(requests)}")
    for i, req in enumerate(requests):
        print(f"\n[{i}] {list(req.keys())[0]}:")
        print(json.dumps(req, indent=2))


def main():
    print("#" * 60)
    print("# BOLD STYLE API TEST APPROACHES")
    print("#" * 60)
    print("""
To test each approach:
1. Create a new Google Doc (empty)
2. Use batchUpdate with the requests below
3. Open the doc and check if bold is contained to "bold" only

Document ID placeholder: <YOUR_DOC_ID>
""")

    approaches = [
        ("1. Current (insert + bold range)", generate_approach_1_requests()),
        ("2. Reset All Before Bold", generate_approach_2_requests()),
        ("3. Reset Text After Bold", generate_approach_3_requests()),
        ("4. Three-Part Explicit Styling", generate_approach_4_requests()),
    ]

    for name, requests in approaches:
        print_requests(name, requests)

    print("\n" + "#" * 60)
    print("# TO TEST VIA MCP:")
    print("#" * 60)
    print("""
Use inspect_doc_structure after creating a doc to see style runs:

  1. create_doc(title="Bold Test", content="Normal **bold** normal", parse_markdown=True)
  2. Note the doc ID from the response
  3. inspect_doc_structure(document_id="<doc_id>", detailed=True)

The detailed output will show each textRun element with its style.
If bold is bleeding, you'll see fewer textRun elements than expected.
""")


if __name__ == "__main__":
    main()
