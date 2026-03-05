"""
Unit tests for MarkdownToDocsConverter.

Tests the Markdown-to-Google-Docs-API-request conversion logic without mocking
the Google API. These tests verify the request generation structure is correct.

Spec Reference: specs/MARKDOWN_STEP_1_CORE.md,
agent-docs/archive/legacy-root/IMPLEMENTATION_PLAN_MARKDOWN.md:L106-115
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

    module_path = Path(__file__).parent.parent.parent.parent / "gdocs" / "markdown_parser.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_mp = _load_markdown_parser_module()
MarkdownToDocsConverter = _mp.MarkdownToDocsConverter
HEADING_STYLE_MAP = _mp.HEADING_STYLE_MAP
BULLET_PRESET_UNORDERED = _mp.BULLET_PRESET_UNORDERED
BULLET_PRESET_ORDERED = _mp.BULLET_PRESET_ORDERED
BULLET_PRESET_CHECKBOX = _mp.BULLET_PRESET_CHECKBOX
CODE_FONT_FAMILY = _mp.CODE_FONT_FAMILY
CODE_BACKGROUND_COLOR = _mp.CODE_BACKGROUND_COLOR
CODE_BORDER_COLOR = _mp.CODE_BORDER_COLOR
CODE_BORDER_WIDTH_PT = _mp.CODE_BORDER_WIDTH_PT
CODE_BORDER_PADDING_PT = _mp.CODE_BORDER_PADDING_PT
CODE_LABEL_COLOR = _mp.CODE_LABEL_COLOR
BLOCKQUOTE_INDENT_PT = _mp.BLOCKQUOTE_INDENT_PT
HR_BORDER_WIDTH_PT = _mp.HR_BORDER_WIDTH_PT
HR_BORDER_COLOR = _mp.HR_BORDER_COLOR
HR_PADDING_BELOW_PT = _mp.HR_PADDING_BELOW_PT
CHECKBOX_UNCHECKED = _mp.CHECKBOX_UNCHECKED
CHECKBOX_CHECKED = _mp.CHECKBOX_CHECKED
IMAGE_PLACEHOLDER_CHAR = _mp.IMAGE_PLACEHOLDER_CHAR
TABLE_PLACEHOLDER_CHAR = _mp.TABLE_PLACEHOLDER_CHAR


@pytest.fixture
def converter():
    return MarkdownToDocsConverter()


class TestConverterBasics:
    def test_empty_input_returns_empty_list(self, converter):
        result = converter.convert("")
        assert result == []

    def test_convert_resets_state(self, converter):
        converter.convert("# First")
        first_count = len(converter.requests)

        converter.convert("Second")
        assert len(converter.requests) < first_count

    def test_start_index_is_customizable(self, converter):
        result = converter.convert("Hello", start_index=100)
        insert_request = result[0]
        assert insert_request["insertText"]["location"]["index"] == 100


class TestSimpleText:
    def test_simple_text_generates_insert_request(self, converter):
        result = converter.convert("Hello World")

        insert_requests = [r for r in result if "insertText" in r]
        assert len(insert_requests) >= 1

        text_request = next(r for r in insert_requests if "Hello World" in r["insertText"]["text"])
        assert text_request["insertText"]["location"]["index"] == 1

    def test_cursor_advances_by_text_length(self, converter):
        converter.convert("12345")
        assert converter.cursor_index == 7

    def test_softbreak_becomes_space(self, converter):
        result = converter.convert("Line1\nLine2")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert "Line1 Line2" in combined

    def test_hardbreak_becomes_newline(self, converter):
        result = converter.convert("Line1  \nLine2")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        assert any("\n" in text for text in insert_texts)


class TestHeadings:
    def test_h1_generates_heading_style(self, converter):
        result = converter.convert("# Title")

        style_requests = [r for r in result if "updateParagraphStyle" in r]
        assert len(style_requests) == 1

        style = style_requests[0]["updateParagraphStyle"]
        assert style["paragraphStyle"]["namedStyleType"] == "HEADING_1"

    def test_heading_levels_map_correctly(self, converter):
        for level in range(1, 7):
            converter = MarkdownToDocsConverter()
            markdown = f"{'#' * level} Heading {level}"
            result = converter.convert(markdown)

            style_requests = [r for r in result if "updateParagraphStyle" in r]
            assert len(style_requests) == 1

            expected_style = f"HEADING_{level}"
            actual_style = style_requests[0]["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"]
            assert actual_style == expected_style, f"h{level} should map to {expected_style}"

    def test_heading_style_range_covers_text(self, converter):
        result = converter.convert("# Hello")

        style_request = next(r for r in result if "updateParagraphStyle" in r)
        range_info = style_request["updateParagraphStyle"]["range"]

        assert range_info["startIndex"] == 1
        assert range_info["endIndex"] == 6

    def test_heading_style_map_constant(self):
        for level in range(1, 7):
            assert f"h{level}" in HEADING_STYLE_MAP
            assert HEADING_STYLE_MAP[f"h{level}"] == f"HEADING_{level}"


class TestBoldItalic:
    def test_bold_text_generates_style_request(self, converter):
        result = converter.convert("**bold**")

        style_requests = [r for r in result if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        bold_style = next(r for r in style_requests if r["updateTextStyle"]["textStyle"].get("bold"))
        assert bold_style["updateTextStyle"]["textStyle"]["bold"] is True

    def test_italic_text_generates_style_request(self, converter):
        result = converter.convert("*italic*")

        style_requests = [r for r in result if "updateTextStyle" in r]
        italic_style = next(r for r in style_requests if r["updateTextStyle"]["textStyle"].get("italic"))
        assert italic_style["updateTextStyle"]["textStyle"]["italic"] is True

    def test_bold_style_range_is_correct(self, converter):
        result = converter.convert("**bold**")

        style_requests = [r for r in result if "updateTextStyle" in r]
        bold_style = next(r for r in style_requests if r["updateTextStyle"]["textStyle"].get("bold"))
        range_info = bold_style["updateTextStyle"]["range"]

        assert range_info["startIndex"] == 1
        assert range_info["endIndex"] == 5

    def test_nested_bold_italic(self, converter):
        result = converter.convert("***both***")

        style_requests = [r for r in result if "updateTextStyle" in r]
        combined_style = next(
            (
                r
                for r in style_requests
                if r["updateTextStyle"]["textStyle"].get("bold") and r["updateTextStyle"]["textStyle"].get("italic")
            ),
            None,
        )
        assert combined_style is not None

    def test_mixed_bold_and_plain(self, converter):
        result = converter.convert("Normal **bold** normal")

        insert_requests = [r for r in result if "insertText" in r]
        style_requests = [r for r in result if "updateTextStyle" in r]

        all_text = "".join(r["insertText"]["text"] for r in insert_requests)
        assert "Normal" in all_text
        assert "bold" in all_text

        bold_styles = [r for r in style_requests if r["updateTextStyle"]["textStyle"].get("bold")]
        assert len(bold_styles) == 1


class TestStrikethrough:
    def test_strikethrough_text_generates_style_request(self, converter):
        result = converter.convert("~~deleted~~")

        style_requests = [r for r in result if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        strikethrough_style = next(r for r in style_requests if r["updateTextStyle"]["textStyle"].get("strikethrough"))
        assert strikethrough_style["updateTextStyle"]["textStyle"]["strikethrough"] is True

    def test_strikethrough_style_range_is_correct(self, converter):
        result = converter.convert("~~deleted~~")

        style_requests = [r for r in result if "updateTextStyle" in r]
        strikethrough_style = next(r for r in style_requests if r["updateTextStyle"]["textStyle"].get("strikethrough"))
        range_info = strikethrough_style["updateTextStyle"]["range"]

        assert range_info["startIndex"] == 1
        assert range_info["endIndex"] == 8

    def test_strikethrough_with_other_formatting(self, converter):
        result = converter.convert("**~~bold and deleted~~**")

        style_requests = [r for r in result if "updateTextStyle" in r]
        combined_style = next(
            (
                r
                for r in style_requests
                if r["updateTextStyle"]["textStyle"].get("bold")
                and r["updateTextStyle"]["textStyle"].get("strikethrough")
            ),
            None,
        )
        assert combined_style is not None

    def test_mixed_strikethrough_and_plain(self, converter):
        result = converter.convert("Normal ~~deleted~~ normal")

        insert_requests = [r for r in result if "insertText" in r]
        style_requests = [r for r in result if "updateTextStyle" in r]

        all_text = "".join(r["insertText"]["text"] for r in insert_requests)
        assert "Normal" in all_text
        assert "deleted" in all_text

        strikethrough_styles = [r for r in style_requests if r["updateTextStyle"]["textStyle"].get("strikethrough")]
        assert len(strikethrough_styles) == 1


class TestLinks:
    def test_link_generates_style_with_url(self, converter):
        result = converter.convert("[Click here](https://example.com)")

        style_requests = [r for r in result if "updateTextStyle" in r]
        link_style = next((r for r in style_requests if "link" in r["updateTextStyle"]["textStyle"]), None)
        assert link_style is not None
        assert link_style["updateTextStyle"]["textStyle"]["link"]["url"] == "https://example.com"

    def test_link_style_covers_link_text(self, converter):
        result = converter.convert("[Click](https://example.com)")

        style_requests = [r for r in result if "updateTextStyle" in r]
        link_style = next(r for r in style_requests if "link" in r["updateTextStyle"]["textStyle"])
        range_info = link_style["updateTextStyle"]["range"]

        assert range_info["startIndex"] == 1
        assert range_info["endIndex"] == 6


class TestLists:
    def test_bullet_list_generates_bullets_request(self, converter):
        """Verify entire list gets ONE createParagraphBullets request (FIX_LIST_NESTING.md)."""
        result = converter.convert("* Item 1\n* Item 2")

        bullet_requests = [r for r in result if "createParagraphBullets" in r]
        # New architecture: one bullet request covers the entire list
        # The API interprets TAB characters to determine nesting
        assert len(bullet_requests) == 1
        # Range should cover both items
        range_info = bullet_requests[0]["createParagraphBullets"]["range"]
        assert range_info["startIndex"] == 1
        # Excludes the trailing list-closing newline to avoid empty bullet paragraph.
        assert range_info["endIndex"] == 14  # "Item 1\nItem 2" = 13 chars, range [1,14)

    def test_bullet_list_uses_unordered_preset(self, converter):
        result = converter.convert("* Item")

        bullet_request = next(r for r in result if "createParagraphBullets" in r)
        assert bullet_request["createParagraphBullets"]["bulletPreset"] == BULLET_PRESET_UNORDERED

    def test_ordered_list_uses_ordered_preset(self, converter):
        """Verify ordered list gets ONE createParagraphBullets with ORDERED preset."""
        result = converter.convert("1. First\n2. Second")

        bullet_requests = [r for r in result if "createParagraphBullets" in r]
        assert len(bullet_requests) == 1
        assert bullet_requests[0]["createParagraphBullets"]["bulletPreset"] == BULLET_PRESET_ORDERED

    def test_nested_list_uses_tabs_for_nesting(self, converter):
        """Verify nested lists prepend TAB characters for nesting (FIX_LIST_NESTING.md)."""
        markdown = """* Level 0
  * Level 1
    * Level 2"""
        result = converter.convert(markdown)

        insert_request = next((r for r in result if "insertText" in r), None)
        assert insert_request is not None
        inserted_text = insert_request["insertText"]["text"]

        assert "\tLevel 1" in inserted_text
        assert "\t\tLevel 2" in inserted_text
        assert inserted_text.startswith("Level 0")

    def test_list_bullet_range_covers_item(self, converter):
        """Range covers list text and excludes trailing list-closing newline."""
        result = converter.convert("* Item")

        bullet_request = next(r for r in result if "createParagraphBullets" in r)
        range_info = bullet_request["createParagraphBullets"]["range"]

        assert range_info["startIndex"] == 1
        assert range_info["endIndex"] == 5  # "Item" = 4 chars, range [1,5)


class TestCodeBlocks:
    def test_fenced_code_block_generates_requests(self, converter):
        result = converter.convert("```\ncode\n```")

        insert_requests = [r for r in result if "insertText" in r]
        style_requests = [r for r in result if "updateTextStyle" in r]
        paragraph_requests = [r for r in result if "updateParagraphStyle" in r]

        assert len(insert_requests) >= 1
        assert len(style_requests) >= 1
        assert len(paragraph_requests) >= 1

    def test_code_block_uses_monospace_font(self, converter):
        result = converter.convert("```\ncode\n```")

        style_request = next(
            r
            for r in result
            if "updateTextStyle" in r
            and r["updateTextStyle"]["textStyle"].get("weightedFontFamily", {}).get("fontFamily") == CODE_FONT_FAMILY
        )
        text_style = style_request["updateTextStyle"]["textStyle"]

        assert text_style["weightedFontFamily"]["fontFamily"] == CODE_FONT_FAMILY

    def test_code_block_has_background_color(self, converter):
        result = converter.convert("```\ncode\n```")

        style_request = next(
            r
            for r in result
            if "updateTextStyle" in r
            and r["updateTextStyle"]["textStyle"].get("weightedFontFamily", {}).get("fontFamily") == CODE_FONT_FAMILY
        )
        text_style = style_request["updateTextStyle"]["textStyle"]

        assert "backgroundColor" in text_style
        bg_color = text_style["backgroundColor"]["color"]["rgbColor"]
        assert bg_color == CODE_BACKGROUND_COLOR

    def test_code_block_has_paragraph_shading_and_borders(self, converter):
        result = converter.convert("```\ncode\n```")

        paragraph_style_request = next(r for r in result if "updateParagraphStyle" in r)
        paragraph_style = paragraph_style_request["updateParagraphStyle"]["paragraphStyle"]

        assert paragraph_style["shading"]["backgroundColor"]["color"]["rgbColor"] == CODE_BACKGROUND_COLOR
        for side in ("borderTop", "borderRight", "borderBottom", "borderLeft"):
            border = paragraph_style[side]
            assert border["color"]["color"]["rgbColor"] == CODE_BORDER_COLOR
            assert border["width"]["magnitude"] == CODE_BORDER_WIDTH_PT
            assert border["padding"]["magnitude"] == CODE_BORDER_PADDING_PT
            assert border["dashStyle"] == "SOLID"

        fields = paragraph_style_request["updateParagraphStyle"]["fields"]
        for field in ("shading", "borderTop", "borderRight", "borderBottom", "borderLeft"):
            assert field in fields

    def test_fenced_code_block_language_label_is_inserted_and_styled(self, converter):
        result = converter.convert("```python\nprint('x')\n```")

        insert_request = next(r for r in result if "insertText" in r)
        inserted_text = insert_request["insertText"]["text"]
        assert "python\nprint('x')" in inserted_text

        label_style = next(
            r
            for r in result
            if "updateTextStyle" in r
            and r["updateTextStyle"]["textStyle"].get("bold") is True
            and r["updateTextStyle"]["textStyle"].get("foregroundColor", {}).get("color", {}).get("rgbColor")
            == CODE_LABEL_COLOR
        )
        assert label_style["updateTextStyle"]["range"]["startIndex"] == 1
        assert label_style["updateTextStyle"]["range"]["endIndex"] == 7  # "python"

        code_style = next(
            r
            for r in result
            if "updateTextStyle" in r
            and r["updateTextStyle"]["textStyle"].get("weightedFontFamily", {}).get("fontFamily") == CODE_FONT_FAMILY
        )
        assert (
            code_style["updateTextStyle"]["range"]["startIndex"] > label_style["updateTextStyle"]["range"]["endIndex"]
        )

    def test_inline_code_generates_style(self, converter):
        result = converter.convert("This is `code` here")

        style_requests = [r for r in result if "updateTextStyle" in r]
        code_style = next(
            (r for r in style_requests if "weightedFontFamily" in r["updateTextStyle"]["textStyle"]), None
        )
        assert code_style is not None
        assert code_style["updateTextStyle"]["textStyle"]["weightedFontFamily"]["fontFamily"] == CODE_FONT_FAMILY


class TestBlockquotes:
    def test_blockquote_generates_indent_style(self, converter):
        result = converter.convert("> Quote text")

        paragraph_styles = [
            r
            for r in result
            if "updateParagraphStyle" in r and "indentStart" in r["updateParagraphStyle"].get("paragraphStyle", {})
        ]
        assert len(paragraph_styles) >= 1

        style = paragraph_styles[0]["updateParagraphStyle"]["paragraphStyle"]
        assert style["indentStart"]["magnitude"] == BLOCKQUOTE_INDENT_PT

    def test_blockquote_applies_italic_style(self, converter):
        result = converter.convert("> Quote text")

        text_styles = [r for r in result if "updateTextStyle" in r]
        italic_style = next((r for r in text_styles if r["updateTextStyle"]["textStyle"].get("italic")), None)
        assert italic_style is not None

    def test_nested_blockquote_increases_indent(self, converter):
        result = converter.convert("> Level 1\n>> Level 2")

        paragraph_styles = [
            r
            for r in result
            if "updateParagraphStyle" in r and "indentStart" in r["updateParagraphStyle"].get("paragraphStyle", {})
        ]

        indents = [s["updateParagraphStyle"]["paragraphStyle"]["indentStart"]["magnitude"] for s in paragraph_styles]
        assert max(indents) == BLOCKQUOTE_INDENT_PT * 2

    def test_blockquote_has_left_border(self, converter):
        """Verify blockquote has borderLeft for visual bar. Spec: specs/FIX_BLOCKQUOTES.md"""
        result = converter.convert("> Quote text")

        paragraph_styles = [
            r
            for r in result
            if "updateParagraphStyle" in r and "borderLeft" in r["updateParagraphStyle"].get("paragraphStyle", {})
        ]
        assert len(paragraph_styles) >= 1, "Expected updateParagraphStyle with borderLeft for blockquote"

        border_left = paragraph_styles[0]["updateParagraphStyle"]["paragraphStyle"]["borderLeft"]
        assert "color" in border_left, "borderLeft should have color"
        assert "width" in border_left, "borderLeft should have width"
        assert "padding" in border_left, "borderLeft should have padding"
        assert border_left["dashStyle"] == "SOLID", "borderLeft should be SOLID"

        fields = paragraph_styles[0]["updateParagraphStyle"]["fields"]
        assert "borderLeft" in fields, "fields mask should include borderLeft"
        assert "indentFirstLine" in fields, "fields mask should include indentFirstLine"


class TestIndexTracking:
    def test_cursor_starts_at_start_index(self, converter):
        converter.convert("", start_index=50)
        assert converter.cursor_index == 50

    def test_insert_text_buffers_content(self, converter):
        converter.cursor_index = 100
        converter._insert_text("test")

        assert converter._text_buffer == "test"
        assert converter.cursor_index == 104

    def test_cursor_advances_after_insert(self, converter):
        converter.cursor_index = 1
        converter._insert_text("hello")

        assert converter.cursor_index == 6


class TestStyleStack:
    def test_push_style_adds_to_stack(self, converter):
        converter._push_style({"bold": True})

        assert len(converter.active_styles) == 1
        assert converter.active_styles[0] == {"bold": True}

    def test_pop_style_removes_from_stack(self, converter):
        converter._push_style({"bold": True})
        converter._pop_style({"bold": True})

        assert len(converter.active_styles) == 0

    def test_get_merged_style_combines_all(self, converter):
        converter._push_style({"bold": True})
        converter._push_style({"italic": True})

        merged = converter._get_merged_style()

        assert merged["bold"] is True
        assert merged["italic"] is True

    def test_pop_link_style_finds_link(self, converter):
        converter._push_style({"bold": True})
        converter._push_style({"link": {"url": "https://test.com"}})
        converter._push_style({"italic": True})

        converter._pop_link_style()

        assert len(converter.active_styles) == 2
        assert not any("link" in s for s in converter.active_styles)


class TestListBleedPrevention:
    """
    Tests for list bullet style inheritance prevention.

    Google Docs paragraphs inherit the style of the previous paragraph on newline.
    When exiting a list, subsequent blocks (headings, paragraphs, code, blockquotes)
    may inherit bullet formatting. The converter emits deleteParagraphBullets to reset this.

    Spec Reference: specs/FIX_LIST_BLEED.md
    """

    def test_list_exit_clears_bullets(self, converter):
        """
        Verify that a heading immediately after a list clears bullet inheritance.

        Input: `* Item\n# Heading`
        Expect:
            - createParagraphBullets for "Item" (list formatting)
            - deleteParagraphBullets for "Heading" (clears inherited bullets)

        Spec Reference: specs/FIX_LIST_BLEED.md
        """
        result = converter.convert("* Item\n# Heading")

        # Find createParagraphBullets requests (for list items)
        create_bullet_requests = [r for r in result if "createParagraphBullets" in r]
        assert len(create_bullet_requests) >= 1, "Expected createParagraphBullets for list item"

        # Find deleteParagraphBullets requests (for heading after list)
        delete_bullet_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullet_requests) >= 1, "Expected deleteParagraphBullets for heading after list"

        # Verify the deleteParagraphBullets covers the heading range
        # The heading "Heading" should be protected from bullet inheritance
        delete_request = delete_bullet_requests[0]
        range_info = delete_request["deleteParagraphBullets"]["range"]
        assert range_info["startIndex"] < range_info["endIndex"]

    def test_paragraph_after_list_clears_bullets(self, converter):
        """Verify paragraph after list also gets bullet clearing."""
        result = converter.convert("* Item\n\nParagraph text")

        delete_bullet_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullet_requests) >= 1, "Expected deleteParagraphBullets for paragraph after list"

    def test_code_block_after_list_clears_bullets(self, converter):
        """Verify code block after list gets bullet clearing."""
        result = converter.convert("* Item\n\n```\ncode\n```")

        delete_bullet_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullet_requests) >= 1, "Expected deleteParagraphBullets for code block after list"

    def test_blockquote_after_list_clears_bullets(self, converter):
        """Verify blockquote after list gets bullet clearing."""
        result = converter.convert("* Item\n\n> Quote")

        delete_bullet_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullet_requests) >= 1, "Expected deleteParagraphBullets for blockquote after list"

    def test_nested_list_exit_clears_bullets(self, converter):
        """Verify exiting nested list clears bullets for subsequent content."""
        result = converter.convert("* Outer\n  * Inner\n\n# Heading")

        delete_bullet_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullet_requests) >= 1, "Expected deleteParagraphBullets after nested list"

    def test_no_bullet_clearing_within_list(self, converter):
        """Verify deleteParagraphBullets is NOT emitted for content within a list."""
        result = converter.convert("* Item 1\n* Item 2\n* Item 3")

        # All three items are in the list, so no deleteParagraphBullets should be emitted
        delete_bullet_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullet_requests) == 0, "Should not emit deleteParagraphBullets within list"


class TestTables:
    def test_simple_table_generates_insert_table_request(self, converter):
        result = converter.convert("| A | B |\n|---|---|\n| 1 | 2 |")

        insert_table_requests = [r for r in result if "insertTable" in r]
        assert len(insert_table_requests) == 1

    def test_table_dimensions_are_correct(self, converter):
        result = converter.convert("| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |")

        insert_table = next(r for r in result if "insertTable" in r)
        assert insert_table["insertTable"]["rows"] == 3
        assert insert_table["insertTable"]["columns"] == 3

    def test_table_uses_current_cursor_index(self, converter):
        result = converter.convert("| A |\n|---|\n| B |", start_index=50)

        insert_table = next(r for r in result if "insertTable" in r)
        assert insert_table["insertTable"]["location"]["index"] == 50

    def test_table_advances_cursor(self, converter):
        initial_cursor = converter.cursor_index
        converter.convert("| A | B |\n|---|---|\n| 1 | 2 |")

        assert converter.cursor_index > initial_cursor

    def test_table_cells_are_populated_with_content(self, converter):
        converter.convert("| Header1 | Header2 |\n|---|---|\n| Data1 | Data2 |")

        # Cell content is now in pending_tables for post-processing
        assert len(converter.pending_tables) == 1
        table_data, bold = converter.pending_tables[0]
        all_cells = [cell for row in table_data for cell in row]
        assert "Header1" in all_cells
        assert "Header2" in all_cells
        assert "Data1" in all_cells
        assert "Data2" in all_cells

    def test_table_header_row_gets_bold_style(self, converter):
        converter.convert("| H1 | H2 |\n|---|---|\n| D1 | D2 |")

        # Bold headers flag is stored in pending_tables
        assert len(converter.pending_tables) == 1
        table_data, bold_headers = converter.pending_tables[0]
        assert bold_headers is True
        assert table_data[0] == ["H1", "H2"]

    def test_table_cell_indices_are_calculated_correctly(self, converter):
        """
        Verify table data is captured correctly for post-processing.

        Cell population now happens in a separate API call after table creation,
        since cell indices cannot be predicted within a single batchUpdate.
        """
        result = converter.convert("| A | B |\n|---|---|\n| C | D |", start_index=1)

        insert_table = next(r for r in result if "insertTable" in r)
        assert insert_table["insertTable"]["location"]["index"] == 1

        # Verify table data is stored for post-processing
        assert len(converter.pending_tables) == 1
        table_data, _ = converter.pending_tables[0]
        assert table_data == [["A", "B"], ["C", "D"]]

    def test_empty_cells_are_skipped(self, converter):
        converter.convert("| A |  |\n|---|---|\n| C | D |")

        assert len(converter.pending_tables) == 1
        table_data, _ = converter.pending_tables[0]
        assert table_data[0][0] == "A"
        assert table_data[0][1] == ""  # empty cell preserved
        assert table_data[1][0] == "C"
        assert table_data[1][1] == "D"

    def test_multiple_tables_preserve_pending_table_order(self, converter):
        markdown = "| H1 |\n|---|\n| A |\n\n| H2 |\n|---|\n| B |"
        converter.convert(markdown)

        assert len(converter.pending_tables) == 2
        first_table, _ = converter.pending_tables[0]
        second_table, _ = converter.pending_tables[1]
        assert first_table == [["H1"], ["A"]]
        assert second_table == [["H2"], ["B"]]

    def test_multiple_table_replacements_are_emitted_in_descending_index_order(self, converter):
        markdown = "| H1 |\n|---|\n| A |\n\n| H2 |\n|---|\n| B |"
        result = converter.convert(markdown)

        table_indices = [r["insertTable"]["location"]["index"] for r in result if "insertTable" in r]
        assert table_indices == sorted(table_indices, reverse=True)


class TestHorizontalRules:
    """Test horizontal rule (---) handling."""

    def test_horizontal_rule_generates_paragraph_with_border(self, converter):
        result = converter.convert("---")

        paragraph_style = next((r for r in result if "updateParagraphStyle" in r), None)
        assert paragraph_style is not None

        ps = paragraph_style["updateParagraphStyle"]
        assert "borderBottom" in ps["paragraphStyle"]
        assert ps["fields"] == "borderBottom"

    def test_horizontal_rule_border_has_correct_styling(self, converter):
        result = converter.convert("---")

        paragraph_style = next(r for r in result if "updateParagraphStyle" in r)
        border = paragraph_style["updateParagraphStyle"]["paragraphStyle"]["borderBottom"]

        assert border["width"]["magnitude"] == HR_BORDER_WIDTH_PT
        assert border["width"]["unit"] == "PT"
        assert border["dashStyle"] == "SOLID"
        assert border["color"]["color"]["rgbColor"] == HR_BORDER_COLOR
        assert border["padding"]["magnitude"] == HR_PADDING_BELOW_PT

    def test_horizontal_rule_inserts_newline(self, converter):
        result = converter.convert("---")

        insert_requests = [r for r in result if "insertText" in r]
        assert len(insert_requests) >= 1
        assert any(r["insertText"]["text"] == "\n" for r in insert_requests)

    def test_horizontal_rule_advances_cursor(self, converter):
        converter.convert("---")
        assert converter.cursor_index == 2

    def test_horizontal_rule_between_content(self, converter):
        result = converter.convert("Above\n\n---\n\nBelow")

        paragraph_styles = [r for r in result if "updateParagraphStyle" in r]
        hr_styles = [p for p in paragraph_styles if "borderBottom" in p["updateParagraphStyle"]["paragraphStyle"]]
        assert len(hr_styles) == 1

    def test_multiple_horizontal_rules(self, converter):
        result = converter.convert("---\n\n---\n\n---")

        paragraph_styles = [r for r in result if "updateParagraphStyle" in r]
        hr_styles = [p for p in paragraph_styles if "borderBottom" in p["updateParagraphStyle"]["paragraphStyle"]]
        assert len(hr_styles) == 3

    def test_horizontal_rule_after_list_clears_bullets(self, converter):
        result = converter.convert("* Item\n\n---")

        delete_bullets = [r for r in result if "deleteParagraphBullets" in r]
        assert len(delete_bullets) >= 1


class TestImages:
    """Test image ![alt](src) handling."""

    def test_image_generates_insert_inline_image_request(self, converter):
        result = converter.convert("![alt text](https://example.com/image.png)")

        inline_image_requests = [r for r in result if "insertInlineImage" in r]
        assert len(inline_image_requests) == 1

        delete_requests = [r for r in result if "deleteContentRange" in r]
        assert len(delete_requests) == 1

    def test_image_placeholder_is_replaced_by_delete_and_inline_image(self, converter):
        result = converter.convert("Before ![alt](https://example.com/img.png) After")

        insert_request = next(r for r in result if "insertText" in r)
        assert IMAGE_PLACEHOLDER_CHAR in insert_request["insertText"]["text"]

        delete_request = next(r for r in result if "deleteContentRange" in r)
        image_request = next(r for r in result if "insertInlineImage" in r)

        delete_range = delete_request["deleteContentRange"]["range"]
        image_index = image_request["insertInlineImage"]["location"]["index"]
        assert delete_range["endIndex"] - delete_range["startIndex"] == 1
        assert image_index == delete_range["startIndex"]

    def test_image_uses_correct_uri(self, converter):
        result = converter.convert("![](https://example.com/photo.jpg)")

        inline_image = next(r for r in result if "insertInlineImage" in r)
        assert inline_image["insertInlineImage"]["uri"] == "https://example.com/photo.jpg"

    def test_image_uses_current_cursor_index(self, converter):
        result = converter.convert("![](https://example.com/img.png)", start_index=50)

        inline_image = next(r for r in result if "insertInlineImage" in r)
        assert inline_image["insertInlineImage"]["location"]["index"] == 50

    def test_image_advances_cursor_by_one(self, converter):
        converter.convert("![](https://example.com/img.png)")
        # Image consumes 1 index + trailing paragraph newline = 2
        assert converter.cursor_index == 3

    def test_image_with_text_before(self, converter):
        result = converter.convert("Text before ![](https://example.com/img.png)")

        insert_texts = [r for r in result if "insertText" in r]
        inline_images = [r for r in result if "insertInlineImage" in r]

        assert len(inline_images) == 1
        assert any("Text before" in r["insertText"]["text"] for r in insert_texts)

    def test_image_with_text_after(self, converter):
        result = converter.convert("![](https://example.com/img.png) text after")

        insert_texts = [r for r in result if "insertText" in r]
        inline_images = [r for r in result if "insertInlineImage" in r]

        assert len(inline_images) == 1
        assert any("text after" in r["insertText"]["text"] for r in insert_texts)

    def test_multiple_images_in_paragraph(self, converter):
        result = converter.convert("![](https://a.com/1.png) and ![](https://b.com/2.png)")

        inline_images = [r for r in result if "insertInlineImage" in r]
        assert len(inline_images) == 2

        delete_requests = [r for r in result if "deleteContentRange" in r]
        assert len(delete_requests) == 2

        uris = [r["insertInlineImage"]["uri"] for r in inline_images]
        assert "https://a.com/1.png" in uris
        assert "https://b.com/2.png" in uris

    def test_image_without_src_is_skipped(self, converter):
        # markdown-it-py won't produce an image token without src, but test
        # the handler's defensive behavior by calling it directly
        from markdown_it.token import Token

        empty_token = Token(type="image", tag="img", nesting=0, attrs={}, children=[])
        converter._handle_image(empty_token)

        inline_images = [r for r in converter.requests if "insertInlineImage" in r]
        assert len(inline_images) == 0


class TestTaskLists:
    """Tests for GitHub Flavored Markdown task list support (Task 6.4)."""

    def test_unchecked_task_item_inserts_ballot_box(self, converter):
        result = converter.convert("- [ ] unchecked task")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert CHECKBOX_UNCHECKED in combined
        assert "unchecked task" in combined

    def test_checked_task_item_inserts_checked_ballot_box(self, converter):
        result = converter.convert("- [x] checked task")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert CHECKBOX_CHECKED in combined
        assert "checked task" in combined

    def test_mixed_task_items(self, converter):
        result = converter.convert("- [ ] todo\n- [x] done\n- [ ] also todo")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert combined.count(CHECKBOX_UNCHECKED) == 2
        assert combined.count(CHECKBOX_CHECKED) == 1

    def test_task_list_items_do_not_get_bullet_style(self, converter):
        result = converter.convert("- [ ] task item")

        bullet_requests = [r for r in result if "createParagraphBullets" in r]
        assert len(bullet_requests) == 0

    def test_uppercase_x_is_also_checked(self, converter):
        result = converter.convert("- [X] uppercase check")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert CHECKBOX_CHECKED in combined

    def test_regular_list_item_has_no_checkbox(self, converter):
        result = converter.convert("- regular item")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert CHECKBOX_UNCHECKED not in combined
        assert CHECKBOX_CHECKED not in combined
        assert "regular item" in combined

    def test_task_list_with_formatting(self, converter):
        result = converter.convert("- [ ] **bold** task")

        insert_texts = [r["insertText"]["text"] for r in result if "insertText" in r]
        combined = "".join(insert_texts)
        assert CHECKBOX_UNCHECKED in combined
        assert "bold" in combined

        style_requests = [r for r in result if "updateTextStyle" in r and r["updateTextStyle"]["textStyle"].get("bold")]
        assert len(style_requests) >= 1

    def test_task_list_does_not_emit_bullet_ranges(self, converter):
        result = converter.convert("- [ ] one\n- [x] two")

        bullet_requests = [r for r in result if "createParagraphBullets" in r]
        assert len(bullet_requests) == 0

    def test_task_list_then_paragraph_emits_no_bullet_cleanup(self, converter):
        result = converter.convert("- [ ] one\n- [x] two\n\nafter")

        bullet_requests = [r for r in result if "createParagraphBullets" in r]
        delete_requests = [r for r in result if "deleteParagraphBullets" in r]
        assert len(bullet_requests) == 0
        assert len(delete_requests) == 0

    def test_native_task_list_mode_emits_checkbox_bullets(self):
        converter = MarkdownToDocsConverter(checklist_mode="native")
        result = converter.convert("- [ ] one\n- [x] two")

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        bullet_requests = [r for r in result if "createParagraphBullets" in r]

        assert CHECKBOX_UNCHECKED not in insert_text
        assert CHECKBOX_CHECKED not in insert_text
        assert len(bullet_requests) == 1
        assert bullet_requests[0]["createParagraphBullets"]["bulletPreset"] == BULLET_PRESET_CHECKBOX


class TestPersonMentions:
    def test_text_mode_keeps_mentions_as_plain_text(self):
        converter = MarkdownToDocsConverter()
        result = converter.convert("Hello @user@example.com")

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        assert "@user@example.com" in insert_text
        assert not any("insertPerson" in request for request in result)

    def test_person_chip_mode_emits_insert_person_requests(self):
        converter = MarkdownToDocsConverter(mention_mode="person_chip")
        result = converter.convert("Hello @user@example.com")

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        assert "@user@example.com" in insert_text

        person_requests = [request for request in result if "insertPerson" in request]
        delete_requests = [request for request in result if "deleteContentRange" in request]
        assert len(person_requests) == 1
        assert len(delete_requests) == 1
        assert person_requests[0]["insertPerson"]["personProperties"]["email"] == "user@example.com"

    def test_person_chip_mode_ignores_inline_code_mentions(self):
        converter = MarkdownToDocsConverter(mention_mode="person_chip")
        result = converter.convert("`@code@example.com` and @user@example.com")

        person_requests = [request for request in result if "insertPerson" in request]
        assert len(person_requests) == 1
        assert person_requests[0]["insertPerson"]["personProperties"]["email"] == "user@example.com"

    def test_person_chip_requests_are_descending_by_index(self):
        converter = MarkdownToDocsConverter(mention_mode="person_chip")
        result = converter.convert("@first@example.com then @second@example.com")

        delete_ranges = [
            request["deleteContentRange"]["range"] for request in result if "deleteContentRange" in request
        ]
        starts = [item["startIndex"] for item in delete_ranges]
        assert starts == sorted(starts, reverse=True)


class TestKitchenSinkRegression:
    def test_kitchen_sink_ranges_stay_within_inserted_text(self, converter):
        markdown = Path(__file__).resolve().parents[2] / "manual" / "kitchen_sink.md"
        content = markdown.read_text(encoding="utf-8")

        result = converter.convert(content, start_index=1)
        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        max_allowed_end = 1 + len(insert_text)

        for req in result:
            if "updateTextStyle" in req:
                assert req["updateTextStyle"]["range"]["endIndex"] <= max_allowed_end
            elif "updateParagraphStyle" in req:
                assert req["updateParagraphStyle"]["range"]["endIndex"] <= max_allowed_end
            elif "createParagraphBullets" in req:
                assert req["createParagraphBullets"]["range"]["endIndex"] <= max_allowed_end
            elif "deleteParagraphBullets" in req:
                assert req["deleteParagraphBullets"]["range"]["endIndex"] <= max_allowed_end

    def test_tables_use_placeholder_replacement_pairs(self, converter):
        result = converter.convert("| A | B |\n|---|---|\n| C | D |")

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        assert TABLE_PLACEHOLDER_CHAR in insert_text

        table_requests = [r for r in result if "insertTable" in r]
        delete_requests = [r for r in result if "deleteContentRange" in r]
        assert len(table_requests) == 1
        assert len(delete_requests) == 1

    def test_image_placeholder_indices_account_for_tab_removal(self, converter):
        markdown = "- root\n  - nested\n    - deep\n\n![logo](https://example.com/logo.png)"
        result = converter.convert(markdown, start_index=1)

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        placeholder_pos = insert_text.index(IMAGE_PLACEHOLDER_CHAR)
        tabs_before_placeholder = insert_text[:placeholder_pos].count("\t")
        expected_index = 1 + placeholder_pos - tabs_before_placeholder

        delete_request = next(
            r
            for r in result
            if "deleteContentRange" in r
            and r["deleteContentRange"]["range"]["endIndex"] - r["deleteContentRange"]["range"]["startIndex"] == 1
        )
        image_request = next(r for r in result if "insertInlineImage" in r)

        assert delete_request["deleteContentRange"]["range"]["startIndex"] == expected_index
        assert image_request["insertInlineImage"]["location"]["index"] == expected_index

    def test_table_placeholder_indices_account_for_tab_removal(self, converter):
        markdown = "- root\n  - nested\n\n| A | B |\n|---|---|\n| C | D |"
        result = converter.convert(markdown, start_index=1)

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        table_placeholder_pos = insert_text.index(TABLE_PLACEHOLDER_CHAR)
        tabs_before_placeholder = insert_text[:table_placeholder_pos].count("\t")
        expected_index = 1 + table_placeholder_pos - tabs_before_placeholder

        table_request = next(r for r in result if "insertTable" in r)
        table_delete = next(
            r
            for r in result
            if "deleteContentRange" in r
            and r["deleteContentRange"]["range"]["startIndex"] == table_request["insertTable"]["location"]["index"]
        )

        assert table_delete["deleteContentRange"]["range"]["startIndex"] == expected_index
        assert table_request["insertTable"]["location"]["index"] == expected_index

    def test_preserves_blank_line_between_heading_and_paragraph(self, converter):
        result = converter.convert("### Heading\n\nParagraph")

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        assert "Heading\n\nParagraph" in insert_text

    def test_preserves_blank_lines_around_horizontal_rule(self, converter):
        result = converter.convert("Above\n\n---\n\nBelow")

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        assert "Above\n\n\n\nBelow" in insert_text

    def test_table_placeholder_is_separated_from_following_block(self, converter):
        markdown = "| A |\n|---|\n| B |\n\nAfter"
        result = converter.convert(markdown)

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        assert f"{TABLE_PLACEHOLDER_CHAR}\n\nAfter" in insert_text

    def test_strikethrough_range_remains_exact_after_table_block(self, converter):
        markdown = "| A |\n|---|\n| B |\n\nThis text is ~~crossed out~~ and this is normal."
        result = converter.convert(markdown, start_index=1)

        insert_text = next(r for r in result if "insertText" in r)["insertText"]["text"]
        strikethrough_request = next(
            r for r in result if "updateTextStyle" in r and r["updateTextStyle"]["textStyle"].get("strikethrough")
        )
        range_info = strikethrough_request["updateTextStyle"]["range"]

        assert insert_text[range_info["startIndex"] - 1 : range_info["endIndex"] - 1] == "crossed out"


class TestTwoPhaseRequestOrdering:
    """Tests for FIX_STYLE_BLEED.md two-phase request ordering fix."""

    @pytest.fixture
    def converter(self):
        return MarkdownToDocsConverter()

    def test_insert_requests_precede_style_requests(self, converter):
        """All insertText requests must come before all updateTextStyle requests."""
        result = converter.convert("normal **bold** normal")

        insert_indices = [i for i, r in enumerate(result) if "insertText" in r]
        style_indices = [i for i, r in enumerate(result) if "updateTextStyle" in r]

        assert insert_indices, "Expected insertText requests"
        assert style_indices, "Expected updateTextStyle requests"
        assert max(insert_indices) < min(style_indices), "insertText must precede updateTextStyle"

    def test_multiple_styles_are_all_present(self, converter):
        """Multiple styled sections should each have their own style request."""
        result = converter.convert("**bold** and *italic*")

        style_requests = [
            r
            for r in result
            if "updateTextStyle" in r
            and (
                r["updateTextStyle"]["textStyle"].get("bold") is True
                or r["updateTextStyle"]["textStyle"].get("italic") is True
            )
        ]
        assert len(style_requests) >= 2

        bold_styles = [r for r in style_requests if r["updateTextStyle"]["textStyle"].get("bold")]
        italic_styles = [r for r in style_requests if r["updateTextStyle"]["textStyle"].get("italic")]
        assert len(bold_styles) >= 1, "Expected at least one bold style"
        assert len(italic_styles) >= 1, "Expected at least one italic style"

    def test_bold_range_is_exact(self, converter):
        """Bold style range must match exactly the bold text, not bleed."""
        result = converter.convert("normal **bold** normal")

        bold_req = next(r for r in result if "updateTextStyle" in r and r["updateTextStyle"]["textStyle"].get("bold"))

        assert bold_req["updateTextStyle"]["range"]["startIndex"] == 8
        assert bold_req["updateTextStyle"]["range"]["endIndex"] == 12

    def test_nested_bold_italic_ranges_correct(self, converter):
        """Nested ***bold italic*** should have correct overlapping ranges."""
        result = converter.convert("text ***bold italic*** text")

        style_requests = [r for r in result if "updateTextStyle" in r]
        assert len(style_requests) >= 1

        for req in style_requests:
            style = req["updateTextStyle"]["textStyle"]
            if style.get("bold") and style.get("italic"):
                assert req["updateTextStyle"]["range"]["startIndex"] == 6
                assert req["updateTextStyle"]["range"]["endIndex"] == 17
                break
        else:
            pytest.fail("Expected combined bold+italic style request")

    def test_paragraph_requests_after_styles(self, converter):
        """Paragraph style requests should come after text style requests."""
        result = converter.convert("# Heading with **bold**")

        style_indices = [i for i, r in enumerate(result) if "updateTextStyle" in r]
        para_indices = [i for i, r in enumerate(result) if "updateParagraphStyle" in r]

        if style_indices and para_indices:
            assert max(style_indices) < min(para_indices), "Styles should precede paragraph formatting"

    def test_single_insert_architecture_no_boundary_resets(self, converter):
        """Single-insert architecture doesn't need boundary resets - styles don't bleed."""
        result = converter.convert("normal **bold** rest")

        insert_requests = [r for r in result if "insertText" in r]
        assert len(insert_requests) == 1, "Single-insert: all text in one request"

        bold_requests = [
            r for r in result if "updateTextStyle" in r and r["updateTextStyle"]["textStyle"].get("bold") is True
        ]
        assert len(bold_requests) == 1, "Bold style applied to correct range"
        assert bold_requests[0]["updateTextStyle"]["range"]["startIndex"] == 8
        assert bold_requests[0]["updateTextStyle"]["range"]["endIndex"] == 12

    def test_single_insert_all_text_combined(self, converter):
        """All text fragments are combined into a single insertText request."""
        result = converter.convert("normal *italic* normal")

        insert_requests = [r for r in result if "insertText" in r]
        assert len(insert_requests) == 1, "All text in one request"
        assert insert_requests[0]["insertText"]["text"] == "normal italic normal\n"
