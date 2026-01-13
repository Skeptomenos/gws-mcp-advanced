"""
Unit tests for Google Docs helper functions and tool registration.

Tests cover:
- Color normalization
- Text style building
- Request builders (insert, delete, format, table, image)
- Operation validation
- Tool registration verification
"""

import pytest


class TestNormalizeColor:
    """Tests for hex color normalization."""

    def test_valid_hex_color(self):
        """Valid hex color is normalized."""
        from gdocs.docs_helpers import _normalize_color

        result = _normalize_color("#FF0000", "test_color")
        assert result["red"] == pytest.approx(1.0)
        assert result["green"] == pytest.approx(0.0)
        assert result["blue"] == pytest.approx(0.0)

    def test_valid_hex_color_lowercase(self):
        """Lowercase hex color is normalized."""
        from gdocs.docs_helpers import _normalize_color

        result = _normalize_color("#00ff00", "test_color")
        assert result["green"] == pytest.approx(1.0)

    def test_none_returns_none(self):
        """None input returns None."""
        from gdocs.docs_helpers import _normalize_color

        assert _normalize_color(None, "test_color") is None

    def test_invalid_format_no_hash(self):
        """Color without hash raises ValueError."""
        from gdocs.docs_helpers import _normalize_color

        with pytest.raises(ValueError, match="hex string"):
            _normalize_color("FF0000", "test_color")

    def test_invalid_format_wrong_length(self):
        """Color with wrong length raises ValueError."""
        from gdocs.docs_helpers import _normalize_color

        with pytest.raises(ValueError, match="hex string"):
            _normalize_color("#FFF", "test_color")

    def test_invalid_hex_characters(self):
        """Color with invalid hex characters raises ValueError."""
        from gdocs.docs_helpers import _normalize_color

        with pytest.raises(ValueError, match="hex string"):
            _normalize_color("#GGGGGG", "test_color")


class TestBuildTextStyle:
    """Tests for text style building."""

    def test_bold_only(self):
        """Build style with bold only."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(bold=True)
        assert style["bold"] is True
        assert "bold" in fields

    def test_italic_only(self):
        """Build style with italic only."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(italic=True)
        assert style["italic"] is True
        assert "italic" in fields

    def test_underline_only(self):
        """Build style with underline only."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(underline=True)
        assert style["underline"] is True
        assert "underline" in fields

    def test_font_size(self):
        """Build style with font size."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(font_size=14)
        assert style["fontSize"]["magnitude"] == 14
        assert style["fontSize"]["unit"] == "PT"
        assert "fontSize" in fields

    def test_font_family(self):
        """Build style with font family."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(font_family="Arial")
        assert style["weightedFontFamily"]["fontFamily"] == "Arial"
        assert "weightedFontFamily" in fields

    def test_text_color(self):
        """Build style with text color."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(text_color="#FF0000")
        assert "foregroundColor" in style
        assert "foregroundColor" in fields

    def test_background_color(self):
        """Build style with background color."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(background_color="#FFFF00")
        assert "backgroundColor" in style
        assert "backgroundColor" in fields

    def test_multiple_styles(self):
        """Build style with multiple properties."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style(bold=True, italic=True, font_size=12)
        assert style["bold"] is True
        assert style["italic"] is True
        assert style["fontSize"]["magnitude"] == 12
        assert len(fields) == 3

    def test_empty_style(self):
        """Build style with no properties."""
        from gdocs.docs_helpers import build_text_style

        style, fields = build_text_style()
        assert style == {}
        assert fields == []


class TestCreateInsertTextRequest:
    """Tests for insert text request creation."""

    def test_basic_insert(self):
        """Create basic insert text request."""
        from gdocs.docs_helpers import create_insert_text_request

        result = create_insert_text_request(10, "Hello")
        assert result["insertText"]["location"]["index"] == 10
        assert result["insertText"]["text"] == "Hello"


class TestCreateInsertTextSegmentRequest:
    """Tests for insert text segment request creation."""

    def test_insert_with_segment_id(self):
        """Create insert text request with segment ID."""
        from gdocs.docs_helpers import create_insert_text_segment_request

        result = create_insert_text_segment_request(0, "Header Text", "kix.header123")
        assert result["insertText"]["location"]["segmentId"] == "kix.header123"
        assert result["insertText"]["location"]["index"] == 0
        assert result["insertText"]["text"] == "Header Text"


class TestCreateDeleteRangeRequest:
    """Tests for delete range request creation."""

    def test_basic_delete(self):
        """Create basic delete range request."""
        from gdocs.docs_helpers import create_delete_range_request

        result = create_delete_range_request(5, 15)
        assert result["deleteContentRange"]["range"]["startIndex"] == 5
        assert result["deleteContentRange"]["range"]["endIndex"] == 15


class TestCreateFormatTextRequest:
    """Tests for format text request creation."""

    def test_format_with_bold(self):
        """Create format request with bold."""
        from gdocs.docs_helpers import create_format_text_request

        result = create_format_text_request(0, 10, bold=True)
        assert result["updateTextStyle"]["range"]["startIndex"] == 0
        assert result["updateTextStyle"]["range"]["endIndex"] == 10
        assert result["updateTextStyle"]["textStyle"]["bold"] is True
        assert "bold" in result["updateTextStyle"]["fields"]

    def test_format_with_multiple_styles(self):
        """Create format request with multiple styles."""
        from gdocs.docs_helpers import create_format_text_request

        result = create_format_text_request(0, 10, bold=True, italic=True, font_size=14)
        assert result["updateTextStyle"]["textStyle"]["bold"] is True
        assert result["updateTextStyle"]["textStyle"]["italic"] is True
        assert result["updateTextStyle"]["textStyle"]["fontSize"]["magnitude"] == 14

    def test_format_with_no_styles_returns_none(self):
        """Create format request with no styles returns None."""
        from gdocs.docs_helpers import create_format_text_request

        result = create_format_text_request(0, 10)
        assert result is None


class TestCreateFindReplaceRequest:
    """Tests for find/replace request creation."""

    def test_basic_find_replace(self):
        """Create basic find/replace request."""
        from gdocs.docs_helpers import create_find_replace_request

        result = create_find_replace_request("old", "new")
        assert result["replaceAllText"]["containsText"]["text"] == "old"
        assert result["replaceAllText"]["replaceText"] == "new"
        assert result["replaceAllText"]["containsText"]["matchCase"] is False

    def test_find_replace_case_sensitive(self):
        """Create case-sensitive find/replace request."""
        from gdocs.docs_helpers import create_find_replace_request

        result = create_find_replace_request("Old", "New", match_case=True)
        assert result["replaceAllText"]["containsText"]["matchCase"] is True


class TestCreateInsertTableRequest:
    """Tests for insert table request creation."""

    def test_basic_table(self):
        """Create basic table insert request."""
        from gdocs.docs_helpers import create_insert_table_request

        result = create_insert_table_request(1, 3, 4)
        assert result["insertTable"]["location"]["index"] == 1
        assert result["insertTable"]["rows"] == 3
        assert result["insertTable"]["columns"] == 4


class TestCreateInsertPageBreakRequest:
    """Tests for insert page break request creation."""

    def test_page_break(self):
        """Create page break insert request."""
        from gdocs.docs_helpers import create_insert_page_break_request

        result = create_insert_page_break_request(50)
        assert result["insertPageBreak"]["location"]["index"] == 50


class TestCreateInsertImageRequest:
    """Tests for insert image request creation."""

    def test_basic_image(self):
        """Create basic image insert request."""
        from gdocs.docs_helpers import create_insert_image_request

        result = create_insert_image_request(1, "https://example.com/image.png")
        assert result["insertInlineImage"]["location"]["index"] == 1
        assert result["insertInlineImage"]["uri"] == "https://example.com/image.png"
        assert "objectSize" not in result["insertInlineImage"]

    def test_image_with_dimensions(self):
        """Create image insert request with dimensions."""
        from gdocs.docs_helpers import create_insert_image_request

        result = create_insert_image_request(1, "https://example.com/image.png", width=200, height=150)
        assert result["insertInlineImage"]["objectSize"]["width"]["magnitude"] == 200
        assert result["insertInlineImage"]["objectSize"]["height"]["magnitude"] == 150

    def test_image_with_width_only(self):
        """Create image insert request with width only."""
        from gdocs.docs_helpers import create_insert_image_request

        result = create_insert_image_request(1, "https://example.com/image.png", width=200)
        assert result["insertInlineImage"]["objectSize"]["width"]["magnitude"] == 200
        assert "height" not in result["insertInlineImage"]["objectSize"]


class TestCreateBulletListRequest:
    """Tests for bullet list request creation."""

    def test_unordered_list(self):
        """Create unordered list request."""
        from gdocs.docs_helpers import create_bullet_list_request

        result = create_bullet_list_request(1, 50, "UNORDERED")
        assert result["createParagraphBullets"]["range"]["startIndex"] == 1
        assert result["createParagraphBullets"]["range"]["endIndex"] == 50
        assert result["createParagraphBullets"]["bulletPreset"] == "BULLET_DISC_CIRCLE_SQUARE"

    def test_ordered_list(self):
        """Create ordered list request."""
        from gdocs.docs_helpers import create_bullet_list_request

        result = create_bullet_list_request(1, 50, "ORDERED")
        assert result["createParagraphBullets"]["bulletPreset"] == "NUMBERED_DECIMAL_ALPHA_ROMAN"


class TestValidateOperation:
    """Tests for operation validation."""

    def test_valid_insert_text(self):
        """Validate valid insert_text operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "insert_text", "index": 1, "text": "Hello"}
        is_valid, error = validate_operation(op)
        assert is_valid is True
        assert error == ""

    def test_valid_delete_text(self):
        """Validate valid delete_text operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "delete_text", "start_index": 1, "end_index": 10}
        is_valid, error = validate_operation(op)
        assert is_valid is True

    def test_valid_replace_text(self):
        """Validate valid replace_text operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "replace_text", "start_index": 1, "end_index": 10, "text": "new"}
        is_valid, error = validate_operation(op)
        assert is_valid is True

    def test_valid_format_text(self):
        """Validate valid format_text operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "format_text", "start_index": 1, "end_index": 10, "bold": True}
        is_valid, error = validate_operation(op)
        assert is_valid is True

    def test_valid_insert_table(self):
        """Validate valid insert_table operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "insert_table", "index": 1, "rows": 3, "columns": 4}
        is_valid, error = validate_operation(op)
        assert is_valid is True

    def test_valid_insert_page_break(self):
        """Validate valid insert_page_break operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "insert_page_break", "index": 50}
        is_valid, error = validate_operation(op)
        assert is_valid is True

    def test_valid_find_replace(self):
        """Validate valid find_replace operation."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "find_replace", "find_text": "old", "replace_text": "new"}
        is_valid, error = validate_operation(op)
        assert is_valid is True

    def test_missing_type(self):
        """Validate operation with missing type."""
        from gdocs.docs_helpers import validate_operation

        op = {"index": 1, "text": "Hello"}
        is_valid, error = validate_operation(op)
        assert is_valid is False
        assert "type" in error

    def test_unsupported_type(self):
        """Validate operation with unsupported type."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "unknown_operation"}
        is_valid, error = validate_operation(op)
        assert is_valid is False
        assert "Unsupported" in error

    def test_missing_required_field(self):
        """Validate operation with missing required field."""
        from gdocs.docs_helpers import validate_operation

        op = {"type": "insert_text", "index": 1}  # missing 'text'
        is_valid, error = validate_operation(op)
        assert is_valid is False
        assert "text" in error


class TestToolRegistration:
    """Tests for MCP tool registration."""

    def test_reading_tools_are_registered(self):
        """Verify reading tools have correct names."""
        from gdocs import get_doc_content, inspect_doc_structure, list_docs_in_folder, search_docs

        assert hasattr(search_docs, "name")
        assert search_docs.name == "search_docs"

        assert hasattr(get_doc_content, "name")
        assert get_doc_content.name == "get_doc_content"

        assert hasattr(list_docs_in_folder, "name")
        assert list_docs_in_folder.name == "list_docs_in_folder"

        assert hasattr(inspect_doc_structure, "name")
        assert inspect_doc_structure.name == "inspect_doc_structure"

    def test_writing_tools_are_registered(self):
        """Verify writing tools have correct names."""
        from gdocs import (
            batch_update_doc,
            create_doc,
            find_and_replace_doc,
            modify_doc_text,
            update_doc_headers_footers,
        )

        assert hasattr(create_doc, "name")
        assert create_doc.name == "create_doc"

        assert hasattr(modify_doc_text, "name")
        assert modify_doc_text.name == "modify_doc_text"

        assert hasattr(find_and_replace_doc, "name")
        assert find_and_replace_doc.name == "find_and_replace_doc"

        assert hasattr(batch_update_doc, "name")
        assert batch_update_doc.name == "batch_update_doc"

        assert hasattr(update_doc_headers_footers, "name")
        assert update_doc_headers_footers.name == "update_doc_headers_footers"

    def test_element_tools_are_registered(self):
        """Verify element tools have correct names."""
        from gdocs import insert_doc_elements, insert_doc_image

        assert hasattr(insert_doc_elements, "name")
        assert insert_doc_elements.name == "insert_doc_elements"

        assert hasattr(insert_doc_image, "name")
        assert insert_doc_image.name == "insert_doc_image"

    def test_table_tools_are_registered(self):
        """Verify table tools have correct names."""
        from gdocs import create_table_with_data, debug_table_structure

        assert hasattr(create_table_with_data, "name")
        assert create_table_with_data.name == "create_table_with_data"

        assert hasattr(debug_table_structure, "name")
        assert debug_table_structure.name == "debug_table_structure"

    def test_export_tools_are_registered(self):
        """Verify export tools have correct names."""
        from gdocs import export_doc_to_pdf

        assert hasattr(export_doc_to_pdf, "name")
        assert export_doc_to_pdf.name == "export_doc_to_pdf"

    def test_comment_tools_are_exported(self):
        """Verify comment tools are exported and callable."""
        from gdocs import (
            create_document_comment,
            read_document_comments,
            reply_to_document_comment,
            resolve_document_comment,
        )

        assert callable(read_document_comments)
        assert callable(create_document_comment)
        assert callable(reply_to_document_comment)
        assert callable(resolve_document_comment)
