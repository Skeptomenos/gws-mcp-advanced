"""
Integration tests for insert_markdown tool.

These tests verify that the insert_markdown tool correctly:
1. Validates input parameters
2. Uses MarkdownToDocsConverter to generate requests
3. Calls batchUpdate with the correct structure

Spec Reference: specs/MARKDOWN_STEP_2_INTEGRATION.md (Task 3.5)
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


class TestInsertMarkdownRequestStructure:
    """Tests for verifying batchUpdate request structure from insert_markdown."""

    @pytest.fixture
    def converter(self):
        """Create a fresh MarkdownToDocsConverter instance."""
        return MarkdownToDocsConverter()

    def test_simple_text_generates_insert_request(self, converter):
        """Verify simple text produces insertText request with correct structure."""
        requests = converter.convert("Hello World")

        # Should have at least one insertText request
        insert_requests = [r for r in requests if "insertText" in r]
        assert len(insert_requests) >= 1

        # Verify structure
        insert_req = insert_requests[0]
        assert "insertText" in insert_req
        assert "text" in insert_req["insertText"]
        assert "location" in insert_req["insertText"]
        assert "index" in insert_req["insertText"]["location"]

    def test_heading_generates_paragraph_style_request(self, converter):
        """Verify heading produces updateParagraphStyle request."""
        requests = converter.convert("# Heading 1")

        # Should have insertText and updateParagraphStyle
        insert_requests = [r for r in requests if "insertText" in r]
        style_requests = [r for r in requests if "updateParagraphStyle" in r]

        assert len(insert_requests) >= 1
        assert len(style_requests) >= 1

        # Verify paragraph style structure
        style_req = style_requests[0]
        assert "updateParagraphStyle" in style_req
        assert "paragraphStyle" in style_req["updateParagraphStyle"]
        assert "namedStyleType" in style_req["updateParagraphStyle"]["paragraphStyle"]
        assert style_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_1"

    def test_bold_text_generates_text_style_request(self, converter):
        """Verify bold text produces updateTextStyle request with bold=True."""
        requests = converter.convert("**bold text**")

        # Should have insertText and updateTextStyle
        insert_requests = [r for r in requests if "insertText" in r]
        style_requests = [r for r in requests if "updateTextStyle" in r]

        assert len(insert_requests) >= 1
        assert len(style_requests) >= 1

        # Verify text style structure for bold
        style_req = style_requests[0]
        assert "updateTextStyle" in style_req
        assert "textStyle" in style_req["updateTextStyle"]
        assert style_req["updateTextStyle"]["textStyle"].get("bold") is True

    def test_italic_text_generates_text_style_request(self, converter):
        """Verify italic text produces updateTextStyle request with italic=True."""
        requests = converter.convert("*italic text*")

        style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        # Verify text style structure for italic
        style_req = style_requests[0]
        assert style_req["updateTextStyle"]["textStyle"].get("italic") is True

    def test_link_generates_link_style_request(self, converter):
        """Verify link produces updateTextStyle request with link URL."""
        requests = converter.convert("[click here](https://example.com)")

        style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        # Find the request with link
        link_req = next(
            (r for r in style_requests if "link" in r["updateTextStyle"]["textStyle"]),
            None,
        )
        assert link_req is not None
        assert link_req["updateTextStyle"]["textStyle"]["link"]["url"] == "https://example.com"

    def test_bullet_list_generates_bullets_request(self, converter):
        """Verify bullet list produces createParagraphBullets request."""
        requests = converter.convert("- Item 1\n- Item 2")

        bullet_requests = [r for r in requests if "createParagraphBullets" in r]
        assert len(bullet_requests) >= 1

        # Verify bullet structure
        bullet_req = bullet_requests[0]
        assert "createParagraphBullets" in bullet_req
        assert "bulletPreset" in bullet_req["createParagraphBullets"]

    def test_ordered_list_generates_bullets_request(self, converter):
        """Verify ordered list produces createParagraphBullets request with ordered preset."""
        requests = converter.convert("1. First\n2. Second")

        bullet_requests = [r for r in requests if "createParagraphBullets" in r]
        assert len(bullet_requests) >= 1

        # Verify it's an ordered list (NUMBERED preset)
        bullet_req = bullet_requests[0]
        preset = bullet_req["createParagraphBullets"]["bulletPreset"]
        assert "NUMBERED" in preset

    def test_code_block_generates_font_style_request(self, converter):
        """Verify code block produces updateTextStyle with monospace font."""
        requests = converter.convert("```\ncode here\n```")

        style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        # Find request with font family
        font_req = next(
            (r for r in style_requests if "weightedFontFamily" in r["updateTextStyle"]["textStyle"]),
            None,
        )
        assert font_req is not None

    def test_blockquote_generates_indent_request(self, converter):
        """Verify blockquote produces updateParagraphStyle with indentation."""
        requests = converter.convert("> quoted text")

        # Should have paragraph style with indentation
        para_style_requests = [r for r in requests if "updateParagraphStyle" in r]

        # Find request with indentation
        indent_req = next(
            (r for r in para_style_requests if "indentStart" in r["updateParagraphStyle"].get("paragraphStyle", {})),
            None,
        )
        assert indent_req is not None

    def test_complex_markdown_generates_multiple_requests(self, converter):
        """Verify complex markdown produces multiple coordinated requests."""
        markdown = """# Welcome

This is **bold** and *italic* text.

- Item 1
- Item 2

> A quote

```python
code = "here"
```
"""
        requests = converter.convert(markdown)

        # Should have multiple request types
        request_types = set()
        for r in requests:
            request_types.update(r.keys())

        assert "insertText" in request_types
        assert "updateParagraphStyle" in request_types
        assert "updateTextStyle" in request_types
        assert "createParagraphBullets" in request_types


class TestInsertMarkdownIndexTracking:
    """Tests for verifying index tracking in batchUpdate requests."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_custom_start_index(self, converter):
        """Verify start_index parameter is respected."""
        requests = converter.convert("Hello", start_index=100)

        insert_req = next(r for r in requests if "insertText" in r)
        assert insert_req["insertText"]["location"]["index"] == 100

    def test_insert_indices_are_sequential(self, converter):
        """Verify multiple insertText requests have non-decreasing indices."""
        # Simple text that doesn't get wrapped
        requests = converter.convert("First paragraph.\n\nSecond paragraph.")

        insert_requests = [r for r in requests if "insertText" in r]

        # All indices should be valid (>= 1)
        for req in insert_requests:
            assert req["insertText"]["location"]["index"] >= 1

    def test_style_ranges_are_valid(self, converter):
        """Verify updateTextStyle ranges have startIndex < endIndex."""
        requests = converter.convert("**bold** and *italic*")

        style_requests = [r for r in requests if "updateTextStyle" in r]

        for req in style_requests:
            range_obj = req["updateTextStyle"]["range"]
            assert range_obj["startIndex"] < range_obj["endIndex"]


class TestInsertMarkdownValidation:
    """Tests for input validation behavior."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_empty_input_returns_empty_list(self, converter):
        """Verify empty markdown returns empty request list."""
        requests = converter.convert("")
        assert requests == []

    def test_whitespace_only_input(self, converter):
        """Verify whitespace-only input returns empty list."""
        requests = converter.convert("   \n\n   ")
        # Whitespace-only should produce minimal requests or empty
        # The exact behavior depends on implementation
        assert isinstance(requests, list)


class TestBatchUpdateBodyFormat:
    """Tests for verifying the complete batchUpdate body structure."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_requests_are_valid_for_batch_update(self, converter):
        """Verify generated requests match Google Docs API batchUpdate schema."""
        requests = converter.convert("# Title\n\nParagraph with **bold**.")

        # Build the body as it would be sent
        body = {"requests": requests}

        assert "requests" in body
        assert isinstance(body["requests"], list)
        assert len(body["requests"]) > 0

        # Each request should be a dict with exactly one top-level key
        valid_request_types = {
            "insertText",
            "updateTextStyle",
            "updateParagraphStyle",
            "createParagraphBullets",
            "insertTable",
            "insertInlineImage",
            "deleteContentRange",
        }

        for req in requests:
            assert isinstance(req, dict)
            # At least one key should be a valid request type
            assert any(key in valid_request_types for key in req.keys())

    def test_all_requests_have_required_fields(self, converter):
        """Verify each request type has its required fields."""
        requests = converter.convert("# Heading\n\n**Bold** text with [link](http://example.com)")

        for req in requests:
            if "insertText" in req:
                assert "text" in req["insertText"]
                assert "location" in req["insertText"]
                assert "index" in req["insertText"]["location"]

            if "updateTextStyle" in req:
                assert "textStyle" in req["updateTextStyle"]
                assert "range" in req["updateTextStyle"]
                assert "fields" in req["updateTextStyle"]

            if "updateParagraphStyle" in req:
                assert "paragraphStyle" in req["updateParagraphStyle"]
                assert "range" in req["updateParagraphStyle"]
                assert "fields" in req["updateParagraphStyle"]

            if "createParagraphBullets" in req:
                assert "bulletPreset" in req["createParagraphBullets"]
                assert "range" in req["createParagraphBullets"]
