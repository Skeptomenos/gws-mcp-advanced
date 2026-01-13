"""
Unit tests for Google Sheets helper functions and tool registration.

Tests cover:
- A1 notation parsing and conversion
- Color parsing and conversion
- Error token detection
- Conditional formatting helpers
- Tool registration verification
"""

import pytest

from core.utils import UserInputError


class TestColumnConversion:
    """Tests for column letter <-> index conversion."""

    def test_column_to_index_single_letter(self):
        """A=0, B=1, Z=25."""
        from gsheets.sheets_helpers import _column_to_index

        assert _column_to_index("A") == 0
        assert _column_to_index("B") == 1
        assert _column_to_index("Z") == 25

    def test_column_to_index_double_letter(self):
        """AA=26, AB=27, AZ=51, BA=52."""
        from gsheets.sheets_helpers import _column_to_index

        assert _column_to_index("AA") == 26
        assert _column_to_index("AB") == 27
        assert _column_to_index("AZ") == 51
        assert _column_to_index("BA") == 52

    def test_column_to_index_case_insensitive(self):
        """Lowercase letters should work."""
        from gsheets.sheets_helpers import _column_to_index

        assert _column_to_index("a") == 0
        assert _column_to_index("aa") == 26

    def test_column_to_index_empty_returns_none(self):
        """Empty string returns None."""
        from gsheets.sheets_helpers import _column_to_index

        assert _column_to_index("") is None

    def test_index_to_column_single_letter(self):
        """0=A, 1=B, 25=Z."""
        from gsheets.sheets_helpers import _index_to_column

        assert _index_to_column(0) == "A"
        assert _index_to_column(1) == "B"
        assert _index_to_column(25) == "Z"

    def test_index_to_column_double_letter(self):
        """26=AA, 27=AB, 51=AZ, 52=BA."""
        from gsheets.sheets_helpers import _index_to_column

        assert _index_to_column(26) == "AA"
        assert _index_to_column(27) == "AB"
        assert _index_to_column(51) == "AZ"
        assert _index_to_column(52) == "BA"

    def test_index_to_column_negative_raises(self):
        """Negative index should raise UserInputError."""
        from gsheets.sheets_helpers import _index_to_column

        with pytest.raises(UserInputError, match="non-negative"):
            _index_to_column(-1)


class TestA1Parsing:
    """Tests for A1 notation parsing."""

    def test_parse_a1_part_cell_reference(self):
        """Parse 'B2' -> (1, 1)."""
        from gsheets.sheets_helpers import _parse_a1_part

        col, row = _parse_a1_part("B2")
        assert col == 1
        assert row == 1

    def test_parse_a1_part_with_anchors(self):
        """Parse '$A$1' -> (0, 0)."""
        from gsheets.sheets_helpers import _parse_a1_part

        col, row = _parse_a1_part("$A$1")
        assert col == 0
        assert row == 0

    def test_parse_a1_part_column_only(self):
        """Parse 'C' -> (2, None)."""
        from gsheets.sheets_helpers import _parse_a1_part

        col, row = _parse_a1_part("C")
        assert col == 2
        assert row is None

    def test_parse_a1_part_row_only(self):
        """Parse '5' -> (None, 4)."""
        from gsheets.sheets_helpers import _parse_a1_part

        col, row = _parse_a1_part("5")
        assert col is None
        assert row == 4

    def test_parse_a1_part_invalid_raises(self):
        """Invalid A1 part should raise UserInputError."""
        from gsheets.sheets_helpers import _parse_a1_part

        with pytest.raises(UserInputError, match="Invalid A1 range part"):
            _parse_a1_part("!@#")

    def test_split_sheet_and_range_with_sheet(self):
        """'Sheet1!A1:B2' -> ('Sheet1', 'A1:B2')."""
        from gsheets.sheets_helpers import _split_sheet_and_range

        sheet, range_part = _split_sheet_and_range("Sheet1!A1:B2")
        assert sheet == "Sheet1"
        assert range_part == "A1:B2"

    def test_split_sheet_and_range_quoted_sheet(self):
        """\"'My Sheet'!$A$1:$B$10\" -> ('My Sheet', '$A$1:$B$10')."""
        from gsheets.sheets_helpers import _split_sheet_and_range

        sheet, range_part = _split_sheet_and_range("'My Sheet'!$A$1:$B$10")
        assert sheet == "My Sheet"
        assert range_part == "$A$1:$B$10"

    def test_split_sheet_and_range_no_sheet(self):
        """'A1:B2' -> (None, 'A1:B2')."""
        from gsheets.sheets_helpers import _split_sheet_and_range

        sheet, range_part = _split_sheet_and_range("A1:B2")
        assert sheet is None
        assert range_part == "A1:B2"

    def test_split_sheet_and_range_escaped_quotes(self):
        """Sheet name with escaped quotes."""
        from gsheets.sheets_helpers import _split_sheet_and_range

        sheet, range_part = _split_sheet_and_range("'It''s a sheet'!A1")
        assert sheet == "It's a sheet"
        assert range_part == "A1"


class TestParseA1Range:
    """Tests for full A1 range to GridRange conversion."""

    @pytest.fixture
    def sample_sheets(self):
        """Sample sheets list for testing."""
        return [
            {"properties": {"sheetId": 0, "title": "Sheet1"}},
            {"properties": {"sheetId": 123, "title": "Data"}},
        ]

    def test_parse_a1_range_simple(self, sample_sheets):
        """Parse 'A1:B2' with default sheet."""
        from gsheets.sheets_helpers import _parse_a1_range

        result = _parse_a1_range("A1:B2", sample_sheets)
        assert result["sheetId"] == 0
        assert result["startRowIndex"] == 0
        assert result["startColumnIndex"] == 0
        assert result["endRowIndex"] == 2
        assert result["endColumnIndex"] == 2

    def test_parse_a1_range_with_sheet_name(self, sample_sheets):
        """Parse 'Data!C3:D4' with named sheet."""
        from gsheets.sheets_helpers import _parse_a1_range

        result = _parse_a1_range("Data!C3:D4", sample_sheets)
        assert result["sheetId"] == 123
        assert result["startRowIndex"] == 2
        assert result["startColumnIndex"] == 2
        assert result["endRowIndex"] == 4
        assert result["endColumnIndex"] == 4

    def test_parse_a1_range_single_cell(self, sample_sheets):
        """Parse 'B2' as single cell range."""
        from gsheets.sheets_helpers import _parse_a1_range

        result = _parse_a1_range("B2", sample_sheets)
        assert result["startRowIndex"] == 1
        assert result["startColumnIndex"] == 1
        assert result["endRowIndex"] == 2
        assert result["endColumnIndex"] == 2

    def test_parse_a1_range_unknown_sheet_raises(self, sample_sheets):
        """Unknown sheet name should raise UserInputError."""
        from gsheets.sheets_helpers import _parse_a1_range

        with pytest.raises(UserInputError, match="not found"):
            _parse_a1_range("Unknown!A1", sample_sheets)

    def test_parse_a1_range_empty_sheets_raises(self):
        """Empty sheets list should raise UserInputError."""
        from gsheets.sheets_helpers import _parse_a1_range

        with pytest.raises(UserInputError, match="no sheets"):
            _parse_a1_range("A1", [])


class TestColorParsing:
    """Tests for hex color parsing and conversion."""

    def test_parse_hex_color_with_hash(self):
        """Parse '#FF0000' -> red."""
        from gsheets.sheets_helpers import _parse_hex_color

        result = _parse_hex_color("#FF0000")
        assert result["red"] == pytest.approx(1.0)
        assert result["green"] == pytest.approx(0.0)
        assert result["blue"] == pytest.approx(0.0)

    def test_parse_hex_color_without_hash(self):
        """Parse '00FF00' -> green."""
        from gsheets.sheets_helpers import _parse_hex_color

        result = _parse_hex_color("00FF00")
        assert result["red"] == pytest.approx(0.0)
        assert result["green"] == pytest.approx(1.0)
        assert result["blue"] == pytest.approx(0.0)

    def test_parse_hex_color_mixed_case(self):
        """Parse 'aAbBcC' -> mixed."""
        from gsheets.sheets_helpers import _parse_hex_color

        result = _parse_hex_color("aAbBcC")
        assert result["red"] == pytest.approx(170 / 255)
        assert result["green"] == pytest.approx(187 / 255)
        assert result["blue"] == pytest.approx(204 / 255)

    def test_parse_hex_color_none_returns_none(self):
        """None input returns None."""
        from gsheets.sheets_helpers import _parse_hex_color

        assert _parse_hex_color(None) is None

    def test_parse_hex_color_empty_returns_none(self):
        """Empty string returns None."""
        from gsheets.sheets_helpers import _parse_hex_color

        assert _parse_hex_color("") is None

    def test_parse_hex_color_invalid_length_raises(self):
        """Invalid length should raise UserInputError."""
        from gsheets.sheets_helpers import _parse_hex_color

        with pytest.raises(UserInputError, match="RRGGBB"):
            _parse_hex_color("#FFF")

    def test_parse_hex_color_invalid_hex_raises(self):
        """Invalid hex characters should raise UserInputError."""
        from gsheets.sheets_helpers import _parse_hex_color

        with pytest.raises(UserInputError, match="not valid hex"):
            _parse_hex_color("#GGGGGG")

    def test_color_to_hex_full_colors(self):
        """Convert color dict back to hex."""
        from gsheets.sheets_helpers import _color_to_hex

        assert _color_to_hex({"red": 1.0, "green": 0.0, "blue": 0.0}) == "#FF0000"
        assert _color_to_hex({"red": 0.0, "green": 1.0, "blue": 0.0}) == "#00FF00"
        assert _color_to_hex({"red": 0.0, "green": 0.0, "blue": 1.0}) == "#0000FF"

    def test_color_to_hex_none_returns_none(self):
        """None input returns None."""
        from gsheets.sheets_helpers import _color_to_hex

        assert _color_to_hex(None) is None

    def test_color_to_hex_partial_values(self):
        """Missing color components default to 0."""
        from gsheets.sheets_helpers import _color_to_hex

        assert _color_to_hex({"red": 0.5}) == "#800000"


class TestErrorDetection:
    """Tests for Sheets error token detection."""

    def test_is_sheets_error_token_error(self):
        """#ERROR! is an error token."""
        from gsheets.sheets_helpers import _is_sheets_error_token

        assert _is_sheets_error_token("#ERROR!") is True

    def test_is_sheets_error_token_na(self):
        """#N/A is an error token."""
        from gsheets.sheets_helpers import _is_sheets_error_token

        assert _is_sheets_error_token("#N/A") is True

    def test_is_sheets_error_token_ref(self):
        """#REF! is an error token."""
        from gsheets.sheets_helpers import _is_sheets_error_token

        assert _is_sheets_error_token("#REF!") is True

    def test_is_sheets_error_token_name(self):
        """#NAME? is an error token."""
        from gsheets.sheets_helpers import _is_sheets_error_token

        assert _is_sheets_error_token("#NAME?") is True

    def test_is_sheets_error_token_normal_value(self):
        """Normal values are not error tokens."""
        from gsheets.sheets_helpers import _is_sheets_error_token

        assert _is_sheets_error_token("Hello") is False
        assert _is_sheets_error_token("123") is False
        assert _is_sheets_error_token("#hashtag") is False

    def test_is_sheets_error_token_non_string(self):
        """Non-string values are not error tokens."""
        from gsheets.sheets_helpers import _is_sheets_error_token

        assert _is_sheets_error_token(123) is False
        assert _is_sheets_error_token(None) is False
        assert _is_sheets_error_token([]) is False

    def test_values_contain_sheets_errors_with_error(self):
        """2D array with error returns True."""
        from gsheets.sheets_helpers import _values_contain_sheets_errors

        values = [["A", "B"], ["C", "#ERROR!"]]
        assert _values_contain_sheets_errors(values) is True

    def test_values_contain_sheets_errors_no_error(self):
        """2D array without error returns False."""
        from gsheets.sheets_helpers import _values_contain_sheets_errors

        values = [["A", "B"], ["C", "D"]]
        assert _values_contain_sheets_errors(values) is False

    def test_values_contain_sheets_errors_empty(self):
        """Empty 2D array returns False."""
        from gsheets.sheets_helpers import _values_contain_sheets_errors

        assert _values_contain_sheets_errors([]) is False
        assert _values_contain_sheets_errors([[]]) is False


class TestConditionValuesParsing:
    """Tests for conditional formatting value parsing."""

    def test_parse_condition_values_list(self):
        """List input passes through."""
        from gsheets.sheets_helpers import _parse_condition_values

        result = _parse_condition_values(["100", "200"])
        assert result == ["100", "200"]

    def test_parse_condition_values_json_string(self):
        """JSON string is parsed."""
        from gsheets.sheets_helpers import _parse_condition_values

        result = _parse_condition_values('["100", "200"]')
        assert result == ["100", "200"]

    def test_parse_condition_values_single_value(self):
        """Single non-list value is wrapped in list."""
        from gsheets.sheets_helpers import _parse_condition_values

        result = _parse_condition_values(100)
        assert result == [100]

    def test_parse_condition_values_none(self):
        """None returns None."""
        from gsheets.sheets_helpers import _parse_condition_values

        assert _parse_condition_values(None) is None

    def test_parse_condition_values_invalid_json_raises(self):
        """Invalid JSON raises UserInputError."""
        from gsheets.sheets_helpers import _parse_condition_values

        with pytest.raises(UserInputError, match="JSON-encoded list"):
            _parse_condition_values("not json")

    def test_parse_condition_values_invalid_type_raises(self):
        """Invalid value type raises UserInputError."""
        from gsheets.sheets_helpers import _parse_condition_values

        with pytest.raises(UserInputError, match="string or number"):
            _parse_condition_values([{"invalid": "dict"}])


class TestGradientPointsParsing:
    """Tests for gradient point parsing."""

    def test_parse_gradient_points_valid_two_points(self):
        """Two valid points are parsed."""
        from gsheets.sheets_helpers import _parse_gradient_points

        points = [
            {"type": "MIN", "color": "#FFFFFF"},
            {"type": "MAX", "color": "#FF0000"},
        ]
        result = _parse_gradient_points(points)
        assert len(result) == 2
        assert result[0]["type"] == "MIN"
        assert result[1]["type"] == "MAX"

    def test_parse_gradient_points_json_string(self):
        """JSON string is parsed."""
        from gsheets.sheets_helpers import _parse_gradient_points

        json_str = '[{"type":"MIN","color":"#FFFFFF"},{"type":"MAX","color":"#FF0000"}]'
        result = _parse_gradient_points(json_str)
        assert len(result) == 2

    def test_parse_gradient_points_none(self):
        """None returns None."""
        from gsheets.sheets_helpers import _parse_gradient_points

        assert _parse_gradient_points(None) is None

    def test_parse_gradient_points_invalid_count_raises(self):
        """Wrong number of points raises UserInputError."""
        from gsheets.sheets_helpers import _parse_gradient_points

        with pytest.raises(UserInputError, match="2 or 3"):
            _parse_gradient_points([{"type": "MIN", "color": "#FFF"}])

    def test_parse_gradient_points_invalid_type_raises(self):
        """Invalid point type raises UserInputError."""
        from gsheets.sheets_helpers import _parse_gradient_points

        with pytest.raises(UserInputError, match="type must be one of"):
            _parse_gradient_points(
                [
                    {"type": "INVALID", "color": "#FFFFFF"},
                    {"type": "MAX", "color": "#FF0000"},
                ]
            )

    def test_parse_gradient_points_missing_color_raises(self):
        """Missing color raises UserInputError."""
        from gsheets.sheets_helpers import _parse_gradient_points

        with pytest.raises(UserInputError, match="color is required"):
            _parse_gradient_points(
                [
                    {"type": "MIN"},
                    {"type": "MAX", "color": "#FF0000"},
                ]
            )


class TestBooleanRuleBuilding:
    """Tests for boolean conditional formatting rule building."""

    def test_build_boolean_rule_with_background(self):
        """Build rule with background color."""
        from gsheets.sheets_helpers import _build_boolean_rule

        ranges = [{"sheetId": 0}]
        rule, cond_type = _build_boolean_rule(
            ranges=ranges,
            condition_type="NUMBER_GREATER",
            condition_values=[100],
            background_color="#FF0000",
            text_color=None,
        )
        assert cond_type == "NUMBER_GREATER"
        assert rule["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"
        assert "backgroundColor" in rule["booleanRule"]["format"]

    def test_build_boolean_rule_with_text_color(self):
        """Build rule with text color."""
        from gsheets.sheets_helpers import _build_boolean_rule

        ranges = [{"sheetId": 0}]
        rule, _ = _build_boolean_rule(
            ranges=ranges,
            condition_type="TEXT_CONTAINS",
            condition_values=["error"],
            background_color=None,
            text_color="#FF0000",
        )
        assert "textFormat" in rule["booleanRule"]["format"]

    def test_build_boolean_rule_no_colors_raises(self):
        """No colors raises UserInputError."""
        from gsheets.sheets_helpers import _build_boolean_rule

        with pytest.raises(UserInputError, match="background_color or text_color"):
            _build_boolean_rule(
                ranges=[{"sheetId": 0}],
                condition_type="NUMBER_GREATER",
                condition_values=[100],
                background_color=None,
                text_color=None,
            )

    def test_build_boolean_rule_invalid_condition_type_raises(self):
        """Invalid condition type raises UserInputError."""
        from gsheets.sheets_helpers import _build_boolean_rule

        with pytest.raises(UserInputError, match="condition_type must be one of"):
            _build_boolean_rule(
                ranges=[{"sheetId": 0}],
                condition_type="INVALID_TYPE",
                condition_values=None,
                background_color="#FF0000",
                text_color=None,
            )


class TestGradientRuleBuilding:
    """Tests for gradient conditional formatting rule building."""

    def test_build_gradient_rule_two_points(self):
        """Build gradient rule with min/max points."""
        from gsheets.sheets_helpers import _build_gradient_rule

        ranges = [{"sheetId": 0}]
        points = [
            {"type": "MIN", "color": {"red": 1, "green": 1, "blue": 1}},
            {"type": "MAX", "color": {"red": 1, "green": 0, "blue": 0}},
        ]
        rule = _build_gradient_rule(ranges, points)
        assert "gradientRule" in rule
        assert "minpoint" in rule["gradientRule"]
        assert "maxpoint" in rule["gradientRule"]
        assert "midpoint" not in rule["gradientRule"]

    def test_build_gradient_rule_three_points(self):
        """Build gradient rule with min/mid/max points."""
        from gsheets.sheets_helpers import _build_gradient_rule

        ranges = [{"sheetId": 0}]
        points = [
            {"type": "MIN", "color": {"red": 1, "green": 1, "blue": 1}},
            {"type": "PERCENT", "value": "50", "color": {"red": 1, "green": 1, "blue": 0}},
            {"type": "MAX", "color": {"red": 1, "green": 0, "blue": 0}},
        ]
        rule = _build_gradient_rule(ranges, points)
        assert "midpoint" in rule["gradientRule"]


class TestUtilityFunctions:
    """Tests for miscellaneous utility functions."""

    def test_coerce_int_from_int(self):
        """Integer input returns same value."""
        from gsheets.sheets_helpers import _coerce_int

        assert _coerce_int(42) == 42

    def test_coerce_int_from_float(self):
        """Float input is truncated."""
        from gsheets.sheets_helpers import _coerce_int

        assert _coerce_int(3.7) == 3

    def test_coerce_int_from_string(self):
        """Numeric string is parsed."""
        from gsheets.sheets_helpers import _coerce_int

        assert _coerce_int("123") == 123

    def test_coerce_int_none_returns_default(self):
        """None returns default."""
        from gsheets.sheets_helpers import _coerce_int

        assert _coerce_int(None) == 0
        assert _coerce_int(None, default=5) == 5

    def test_coerce_int_invalid_returns_default(self):
        """Invalid input returns default."""
        from gsheets.sheets_helpers import _coerce_int

        assert _coerce_int("not a number") == 0

    def test_quote_sheet_title_safe(self):
        """Safe titles are not quoted."""
        from gsheets.sheets_helpers import _quote_sheet_title_for_a1

        assert _quote_sheet_title_for_a1("Sheet1") == "Sheet1"
        assert _quote_sheet_title_for_a1("Data_2024") == "Data_2024"

    def test_quote_sheet_title_with_spaces(self):
        """Titles with spaces are quoted."""
        from gsheets.sheets_helpers import _quote_sheet_title_for_a1

        assert _quote_sheet_title_for_a1("My Sheet") == "'My Sheet'"

    def test_quote_sheet_title_with_quotes(self):
        """Titles with quotes are escaped."""
        from gsheets.sheets_helpers import _quote_sheet_title_for_a1

        assert _quote_sheet_title_for_a1("It's data") == "'It''s data'"

    def test_format_a1_cell(self):
        """Format cell reference."""
        from gsheets.sheets_helpers import _format_a1_cell

        assert _format_a1_cell("Sheet1", 0, 0) == "Sheet1!A1"
        assert _format_a1_cell("Sheet1", 1, 1) == "Sheet1!B2"
        assert _format_a1_cell("My Sheet", 0, 0) == "'My Sheet'!A1"


class TestToolRegistration:
    """Tests for MCP tool registration."""

    def test_exported_sheets_tools_are_registered(self):
        """Verify exported sheets tools have correct names."""
        from gsheets import (
            create_sheet,
            create_spreadsheet,
            get_spreadsheet_info,
            list_spreadsheets,
            modify_sheet_values,
            read_sheet_values,
        )

        assert hasattr(list_spreadsheets, "name")
        assert list_spreadsheets.name == "list_spreadsheets"

        assert hasattr(get_spreadsheet_info, "name")
        assert get_spreadsheet_info.name == "get_spreadsheet_info"

        assert hasattr(read_sheet_values, "name")
        assert read_sheet_values.name == "read_sheet_values"

        assert hasattr(modify_sheet_values, "name")
        assert modify_sheet_values.name == "modify_sheet_values"

        assert hasattr(create_spreadsheet, "name")
        assert create_spreadsheet.name == "create_spreadsheet"

        assert hasattr(create_sheet, "name")
        assert create_sheet.name == "create_sheet"

    def test_all_sheets_tools_are_registered(self):
        """Verify all sheets tools (including non-exported) have correct names."""
        from gsheets.sheets_tools import (
            add_conditional_formatting,
            delete_conditional_formatting,
            format_sheet_range,
            update_conditional_formatting,
        )

        assert hasattr(format_sheet_range, "name")
        assert format_sheet_range.name == "format_sheet_range"

        assert hasattr(add_conditional_formatting, "name")
        assert add_conditional_formatting.name == "add_conditional_formatting"

        assert hasattr(update_conditional_formatting, "name")
        assert update_conditional_formatting.name == "update_conditional_formatting"

        assert hasattr(delete_conditional_formatting, "name")
        assert delete_conditional_formatting.name == "delete_conditional_formatting"
