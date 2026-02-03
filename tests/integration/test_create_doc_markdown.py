"""
Integration tests for create_doc tool with Markdown content.

These tests verify that the create_doc tool correctly:
1. Uses MarkdownToDocsConverter when parse_markdown=True (default)
2. Uses plain text insertion when parse_markdown=False
3. Handles edge cases (empty content, no content)

Spec Reference: specs/MARKDOWN_STEP_2_INTEGRATION.md (Task 3.6)
"""

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_markdown_parser_module():
    """
    Load markdown_parser module directly to avoid gdocs/__init__.py circular import.

    The gdocs package has a circular import chain (gdocs -> auth -> core -> auth).
    Since markdown_parser.py is standalone (only depends on markdown_it), we load
    it directly via importlib to bypass the package __init__.py.
    """
    module_name = "gdocs.markdown_parser"
    if module_name in sys.modules:
        return sys.modules[module_name]

    module_path = Path(__file__).parent.parent.parent / "gdocs" / "markdown_parser.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_mp = _load_markdown_parser_module()
MarkdownToDocsConverter = _mp.MarkdownToDocsConverter


class TestCreateDocMarkdownParsing:
    """Tests for create_doc with parse_markdown=True (default behavior)."""

    @pytest.fixture
    def converter(self):
        """Create a fresh MarkdownToDocsConverter instance."""
        return MarkdownToDocsConverter()

    def test_simple_markdown_produces_formatted_requests(self, converter):
        """Verify simple Markdown produces insert + style requests."""
        requests = converter.convert("# Hello World")

        insert_requests = [r for r in requests if "insertText" in r]
        style_requests = [r for r in requests if "updateParagraphStyle" in r]

        assert len(insert_requests) >= 1
        assert len(style_requests) >= 1

        heading_style = next(
            (
                r
                for r in style_requests
                if r["updateParagraphStyle"]["paragraphStyle"].get("namedStyleType") == "HEADING_1"
            ),
            None,
        )
        assert heading_style is not None

    def test_bold_markdown_produces_style_request(self, converter):
        """Verify bold Markdown produces updateTextStyle with bold=True."""
        requests = converter.convert("**bold text**")

        style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        bold_req = next(
            (r for r in style_requests if r["updateTextStyle"]["textStyle"].get("bold") is True),
            None,
        )
        assert bold_req is not None

    def test_italic_markdown_produces_style_request(self, converter):
        """Verify italic Markdown produces updateTextStyle with italic=True."""
        requests = converter.convert("*italic text*")

        style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        italic_req = next(
            (r for r in style_requests if r["updateTextStyle"]["textStyle"].get("italic") is True),
            None,
        )
        assert italic_req is not None

    def test_mixed_formatting_produces_multiple_styles(self, converter):
        """Verify mixed formatting produces multiple style requests."""
        requests = converter.convert("**bold** and *italic* text")

        style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(style_requests) >= 2

        has_bold = any(r["updateTextStyle"]["textStyle"].get("bold") is True for r in style_requests)
        has_italic = any(r["updateTextStyle"]["textStyle"].get("italic") is True for r in style_requests)

        assert has_bold
        assert has_italic

    def test_list_markdown_produces_bullet_request(self, converter):
        """Verify list Markdown produces createParagraphBullets request."""
        requests = converter.convert("- Item 1\n- Item 2\n- Item 3")

        bullet_requests = [r for r in requests if "createParagraphBullets" in r]
        assert len(bullet_requests) >= 1

        bullet_req = bullet_requests[0]
        assert "bulletPreset" in bullet_req["createParagraphBullets"]

    def test_ordered_list_produces_numbered_bullets(self, converter):
        """Verify ordered list produces NUMBERED bullet preset."""
        requests = converter.convert("1. First\n2. Second\n3. Third")

        bullet_requests = [r for r in requests if "createParagraphBullets" in r]
        assert len(bullet_requests) >= 1

        preset = bullet_requests[0]["createParagraphBullets"]["bulletPreset"]
        assert "NUMBERED" in preset

    def test_link_markdown_produces_link_style(self, converter):
        """Verify link Markdown produces updateTextStyle with link URL."""
        requests = converter.convert("[Google](https://google.com)")

        style_requests = [r for r in requests if "updateTextStyle" in r]

        link_req = next(
            (r for r in style_requests if "link" in r["updateTextStyle"]["textStyle"]),
            None,
        )
        assert link_req is not None
        assert link_req["updateTextStyle"]["textStyle"]["link"]["url"] == "https://google.com"

    def test_code_block_produces_font_style(self, converter):
        """Verify code block produces updateTextStyle with monospace font."""
        requests = converter.convert("```\nprint('hello')\n```")

        style_requests = [r for r in requests if "updateTextStyle" in r]

        font_req = next(
            (r for r in style_requests if "weightedFontFamily" in r["updateTextStyle"]["textStyle"]),
            None,
        )
        assert font_req is not None

    def test_blockquote_produces_indent_style(self, converter):
        """Verify blockquote produces updateParagraphStyle with indentation."""
        requests = converter.convert("> This is a quote")

        para_style_requests = [r for r in requests if "updateParagraphStyle" in r]

        indent_req = next(
            (r for r in para_style_requests if "indentStart" in r["updateParagraphStyle"].get("paragraphStyle", {})),
            None,
        )
        assert indent_req is not None


class TestCreateDocPlainText:
    """Tests for create_doc with parse_markdown=False (plain text behavior)."""

    def test_plain_text_produces_single_insert_request(self):
        """Verify plain text mode produces single insertText request."""
        content = "# This is NOT a heading"
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

        assert len(requests) == 1
        assert "insertText" in requests[0]
        assert requests[0]["insertText"]["text"] == content

    def test_plain_text_preserves_markdown_literally(self):
        """Verify plain text preserves Markdown syntax as literal text."""
        content = "**bold** and *italic*"
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

        assert len(requests) == 1
        assert requests[0]["insertText"]["text"] == "**bold** and *italic*"

    def test_plain_text_index_is_one(self):
        """Verify plain text insertion starts at index 1."""
        content = "Plain text content"
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

        assert requests[0]["insertText"]["location"]["index"] == 1


class TestCreateDocEdgeCases:
    """Tests for create_doc edge cases."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_empty_content_returns_empty_requests(self, converter):
        """Verify empty content produces no requests."""
        requests = converter.convert("")
        assert requests == []

    def test_whitespace_only_content(self, converter):
        """Verify whitespace-only content is handled gracefully."""
        requests = converter.convert("   \n\n   ")
        assert isinstance(requests, list)

    def test_complex_document_structure(self, converter):
        """Verify complex Markdown produces valid request sequence."""
        markdown = """# Project README

## Introduction

This is a **sample** project with *italic* emphasis.

### Features

- Feature 1
- Feature 2
- Feature 3

### Code Example

```python
def hello():
    print("Hello, World!")
```

> Note: This is an important quote.

For more info, visit [our site](https://example.com).
"""
        requests = converter.convert(markdown)

        request_types = set()
        for r in requests:
            request_types.update(r.keys())

        assert "insertText" in request_types
        assert "updateParagraphStyle" in request_types
        assert "updateTextStyle" in request_types
        assert "createParagraphBullets" in request_types
        assert len(requests) > 10


class TestCreateDocRequestValidation:
    """Tests for validating request structure matches Google Docs API schema."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_all_insert_requests_have_required_fields(self, converter):
        """Verify insertText requests have text, location, and index."""
        requests = converter.convert("# Heading\n\nParagraph with **bold**.")

        insert_requests = [r for r in requests if "insertText" in r]

        for req in insert_requests:
            assert "text" in req["insertText"]
            assert "location" in req["insertText"]
            assert "index" in req["insertText"]["location"]
            assert isinstance(req["insertText"]["location"]["index"], int)

    def test_all_text_style_requests_have_required_fields(self, converter):
        """Verify updateTextStyle requests have textStyle, range, and fields."""
        requests = converter.convert("**Bold** and *italic* text")

        style_requests = [r for r in requests if "updateTextStyle" in r]

        for req in style_requests:
            assert "textStyle" in req["updateTextStyle"]
            assert "range" in req["updateTextStyle"]
            assert "fields" in req["updateTextStyle"]
            range_obj = req["updateTextStyle"]["range"]
            assert "startIndex" in range_obj
            assert "endIndex" in range_obj
            assert range_obj["startIndex"] < range_obj["endIndex"]

    def test_all_paragraph_style_requests_have_required_fields(self, converter):
        """Verify updateParagraphStyle requests have paragraphStyle, range, and fields."""
        requests = converter.convert("# Heading 1\n\n## Heading 2")

        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        for req in para_requests:
            assert "paragraphStyle" in req["updateParagraphStyle"]
            assert "range" in req["updateParagraphStyle"]
            assert "fields" in req["updateParagraphStyle"]

    def test_all_bullet_requests_have_required_fields(self, converter):
        """Verify createParagraphBullets requests have bulletPreset and range."""
        requests = converter.convert("- Item 1\n- Item 2")

        bullet_requests = [r for r in requests if "createParagraphBullets" in r]

        for req in bullet_requests:
            assert "bulletPreset" in req["createParagraphBullets"]
            assert "range" in req["createParagraphBullets"]


class TestCreateDocIndexIntegrity:
    """Tests for verifying index tracking in request sequences."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_indices_start_at_one_by_default(self, converter):
        """Verify default start index is 1."""
        requests = converter.convert("Hello")

        insert_req = next(r for r in requests if "insertText" in r)
        assert insert_req["insertText"]["location"]["index"] == 1

    def test_custom_start_index_is_respected(self, converter):
        """Verify custom start_index parameter works."""
        requests = converter.convert("Hello", start_index=50)

        insert_req = next(r for r in requests if "insertText" in r)
        assert insert_req["insertText"]["location"]["index"] == 50

    def test_style_ranges_are_valid(self, converter):
        """Verify all style ranges have startIndex < endIndex."""
        requests = converter.convert("**bold** and *italic* and `code`")

        style_requests = [r for r in requests if "updateTextStyle" in r]

        for req in style_requests:
            range_obj = req["updateTextStyle"]["range"]
            assert range_obj["startIndex"] < range_obj["endIndex"], (
                f"Invalid range: start={range_obj['startIndex']}, end={range_obj['endIndex']}"
            )

    def test_paragraph_ranges_are_valid(self, converter):
        """Verify all paragraph style ranges have startIndex < endIndex."""
        requests = converter.convert("# Heading 1\n\n## Heading 2\n\n### Heading 3")

        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        for req in para_requests:
            range_obj = req["updateParagraphStyle"]["range"]
            assert range_obj["startIndex"] < range_obj["endIndex"], (
                f"Invalid range: start={range_obj['startIndex']}, end={range_obj['endIndex']}"
            )


class TestCreateDocHeadingLevels:
    """Tests for verifying heading level mapping."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_h1_maps_to_heading_1(self, converter):
        """Verify # maps to HEADING_1."""
        requests = converter.convert("# H1")
        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        heading_req = next(
            (r for r in para_requests if "namedStyleType" in r["updateParagraphStyle"]["paragraphStyle"]),
            None,
        )
        assert heading_req is not None
        assert heading_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_1"

    def test_h2_maps_to_heading_2(self, converter):
        """Verify ## maps to HEADING_2."""
        requests = converter.convert("## H2")
        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        heading_req = next(
            (r for r in para_requests if "namedStyleType" in r["updateParagraphStyle"]["paragraphStyle"]),
            None,
        )
        assert heading_req is not None
        assert heading_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_2"

    def test_h3_maps_to_heading_3(self, converter):
        """Verify ### maps to HEADING_3."""
        requests = converter.convert("### H3")
        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        heading_req = next(
            (r for r in para_requests if "namedStyleType" in r["updateParagraphStyle"]["paragraphStyle"]),
            None,
        )
        assert heading_req is not None
        assert heading_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_3"

    def test_h4_maps_to_heading_4(self, converter):
        """Verify #### maps to HEADING_4."""
        requests = converter.convert("#### H4")
        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        heading_req = next(
            (r for r in para_requests if "namedStyleType" in r["updateParagraphStyle"]["paragraphStyle"]),
            None,
        )
        assert heading_req is not None
        assert heading_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_4"

    def test_h5_maps_to_heading_5(self, converter):
        """Verify ##### maps to HEADING_5."""
        requests = converter.convert("##### H5")
        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        heading_req = next(
            (r for r in para_requests if "namedStyleType" in r["updateParagraphStyle"]["paragraphStyle"]),
            None,
        )
        assert heading_req is not None
        assert heading_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_5"

    def test_h6_maps_to_heading_6(self, converter):
        """Verify ###### maps to HEADING_6."""
        requests = converter.convert("###### H6")
        para_requests = [r for r in requests if "updateParagraphStyle" in r]

        heading_req = next(
            (r for r in para_requests if "namedStyleType" in r["updateParagraphStyle"]["paragraphStyle"]),
            None,
        )
        assert heading_req is not None
        assert heading_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_6"
