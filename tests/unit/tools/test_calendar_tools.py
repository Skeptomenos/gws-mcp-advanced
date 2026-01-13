"""
Unit tests for Google Calendar tools helper functions.

Tests cover:
- Reminder parsing and validation
- Transparency/visibility application
- Time format correction for API
- Attendee formatting and normalization
- Attachment formatting
- Tool registration
"""

from gcalendar.calendar_helpers import (
    _apply_transparency_if_valid,
    _apply_visibility_if_valid,
    _correct_time_format_for_api,
    _format_attachment_details,
    _format_attendee_details,
    _normalize_attendees,
    _parse_reminders_json,
    _preserve_existing_fields,
)


class TestParseRemindersJson:
    """Tests for _parse_reminders_json function."""

    def test_none_input_returns_empty_list(self):
        """None input should return empty list."""
        assert _parse_reminders_json(None, "test_func") == []

    def test_empty_string_returns_empty_list(self):
        """Empty string should return empty list."""
        assert _parse_reminders_json("", "test_func") == []

    def test_valid_json_string_single_reminder(self):
        """Valid JSON string with single reminder should parse correctly."""
        result = _parse_reminders_json('[{"method": "popup", "minutes": 15}]', "test_func")
        assert result == [{"method": "popup", "minutes": 15}]

    def test_valid_json_string_multiple_reminders(self):
        """Valid JSON string with multiple reminders should parse correctly."""
        result = _parse_reminders_json(
            '[{"method": "popup", "minutes": 15}, {"method": "email", "minutes": 60}]', "test_func"
        )
        assert result == [{"method": "popup", "minutes": 15}, {"method": "email", "minutes": 60}]

    def test_valid_list_input(self):
        """List input should be processed directly."""
        result = _parse_reminders_json([{"method": "popup", "minutes": 30}], "test_func")
        assert result == [{"method": "popup", "minutes": 30}]

    def test_truncates_to_five_reminders(self):
        """More than 5 reminders should be truncated."""
        reminders = [{"method": "popup", "minutes": i * 10} for i in range(1, 8)]
        result = _parse_reminders_json(reminders, "test_func")
        assert len(result) == 5

    def test_invalid_json_returns_empty_list(self):
        """Invalid JSON should return empty list."""
        result = _parse_reminders_json("not valid json", "test_func")
        assert result == []

    def test_json_not_array_returns_empty_list(self):
        """JSON that's not an array should return empty list."""
        result = _parse_reminders_json('{"method": "popup", "minutes": 15}', "test_func")
        assert result == []

    def test_invalid_method_skipped(self):
        """Reminders with invalid method should be skipped."""
        result = _parse_reminders_json([{"method": "sms", "minutes": 15}], "test_func")
        assert result == []

    def test_missing_method_skipped(self):
        """Reminders missing method should be skipped."""
        result = _parse_reminders_json([{"minutes": 15}], "test_func")
        assert result == []

    def test_missing_minutes_skipped(self):
        """Reminders missing minutes should be skipped."""
        result = _parse_reminders_json([{"method": "popup"}], "test_func")
        assert result == []

    def test_invalid_minutes_negative_skipped(self):
        """Reminders with negative minutes should be skipped."""
        result = _parse_reminders_json([{"method": "popup", "minutes": -5}], "test_func")
        assert result == []

    def test_invalid_minutes_too_large_skipped(self):
        """Reminders with minutes > 40320 should be skipped."""
        result = _parse_reminders_json([{"method": "popup", "minutes": 50000}], "test_func")
        assert result == []

    def test_method_normalized_to_lowercase(self):
        """Method should be normalized to lowercase."""
        result = _parse_reminders_json([{"method": "POPUP", "minutes": 15}], "test_func")
        assert result == [{"method": "popup", "minutes": 15}]

    def test_mixed_valid_invalid_reminders(self):
        """Valid reminders should be kept, invalid ones skipped."""
        reminders = [
            {"method": "popup", "minutes": 15},  # valid
            {"method": "sms", "minutes": 30},  # invalid method
            {"method": "email", "minutes": 60},  # valid
        ]
        result = _parse_reminders_json(reminders, "test_func")
        assert result == [{"method": "popup", "minutes": 15}, {"method": "email", "minutes": 60}]

    def test_non_dict_reminder_skipped(self):
        """Non-dict items in reminders list should be skipped."""
        result = _parse_reminders_json(["not a dict", {"method": "popup", "minutes": 15}], "test_func")
        assert result == [{"method": "popup", "minutes": 15}]

    def test_invalid_type_returns_empty_list(self):
        """Invalid input type (not str or list) should return empty list."""
        result = _parse_reminders_json(12345, "test_func")
        assert result == []


class TestApplyTransparencyIfValid:
    """Tests for _apply_transparency_if_valid function."""

    def test_none_transparency_no_change(self):
        """None transparency should not modify event body."""
        event_body = {"summary": "Test"}
        _apply_transparency_if_valid(event_body, None, "test_func")
        assert "transparency" not in event_body

    def test_opaque_transparency_applied(self):
        """Valid 'opaque' transparency should be applied."""
        event_body = {}
        _apply_transparency_if_valid(event_body, "opaque", "test_func")
        assert event_body["transparency"] == "opaque"

    def test_transparent_transparency_applied(self):
        """Valid 'transparent' transparency should be applied."""
        event_body = {}
        _apply_transparency_if_valid(event_body, "transparent", "test_func")
        assert event_body["transparency"] == "transparent"

    def test_invalid_transparency_not_applied(self):
        """Invalid transparency value should not be applied."""
        event_body = {}
        _apply_transparency_if_valid(event_body, "invalid", "test_func")
        assert "transparency" not in event_body


class TestApplyVisibilityIfValid:
    """Tests for _apply_visibility_if_valid function."""

    def test_none_visibility_no_change(self):
        """None visibility should not modify event body."""
        event_body = {"summary": "Test"}
        _apply_visibility_if_valid(event_body, None, "test_func")
        assert "visibility" not in event_body

    def test_default_visibility_applied(self):
        """Valid 'default' visibility should be applied."""
        event_body = {}
        _apply_visibility_if_valid(event_body, "default", "test_func")
        assert event_body["visibility"] == "default"

    def test_public_visibility_applied(self):
        """Valid 'public' visibility should be applied."""
        event_body = {}
        _apply_visibility_if_valid(event_body, "public", "test_func")
        assert event_body["visibility"] == "public"

    def test_private_visibility_applied(self):
        """Valid 'private' visibility should be applied."""
        event_body = {}
        _apply_visibility_if_valid(event_body, "private", "test_func")
        assert event_body["visibility"] == "private"

    def test_confidential_visibility_applied(self):
        """Valid 'confidential' visibility should be applied."""
        event_body = {}
        _apply_visibility_if_valid(event_body, "confidential", "test_func")
        assert event_body["visibility"] == "confidential"

    def test_invalid_visibility_not_applied(self):
        """Invalid visibility value should not be applied."""
        event_body = {}
        _apply_visibility_if_valid(event_body, "secret", "test_func")
        assert "visibility" not in event_body


class TestPreserveExistingFields:
    """Tests for _preserve_existing_fields function."""

    def test_preserves_existing_when_new_is_none(self):
        """Should preserve existing field when new value is None."""
        event_body = {}
        existing_event = {"summary": "Existing Title", "location": "Office"}
        field_mappings = {"summary": None, "location": None}
        _preserve_existing_fields(event_body, existing_event, field_mappings)
        assert event_body["summary"] == "Existing Title"
        assert event_body["location"] == "Office"

    def test_uses_new_value_when_provided(self):
        """Should use new value when provided (not None)."""
        event_body = {}
        existing_event = {"summary": "Old Title"}
        field_mappings = {"summary": "New Title"}
        _preserve_existing_fields(event_body, existing_event, field_mappings)
        assert event_body["summary"] == "New Title"

    def test_does_not_add_missing_existing_field(self):
        """Should not add field if it doesn't exist in existing event."""
        event_body = {}
        existing_event = {}
        field_mappings = {"description": None}
        _preserve_existing_fields(event_body, existing_event, field_mappings)
        assert "description" not in event_body


class TestFormatAttendeeDetails:
    """Tests for _format_attendee_details function."""

    def test_empty_attendees_returns_none(self):
        """Empty attendees list should return 'None'."""
        assert _format_attendee_details([]) == "None"

    def test_single_attendee_basic(self):
        """Single attendee with basic info."""
        attendees = [{"email": "user@example.com", "responseStatus": "accepted"}]
        result = _format_attendee_details(attendees)
        assert result == "user@example.com: accepted"

    def test_attendee_with_organizer_flag(self):
        """Attendee with organizer flag should show (organizer)."""
        attendees = [{"email": "org@example.com", "responseStatus": "accepted", "organizer": True}]
        result = _format_attendee_details(attendees)
        assert "(organizer)" in result

    def test_attendee_with_optional_flag(self):
        """Attendee with optional flag should show (optional)."""
        attendees = [{"email": "opt@example.com", "responseStatus": "tentative", "optional": True}]
        result = _format_attendee_details(attendees)
        assert "(optional)" in result

    def test_multiple_attendees_newline_separated(self):
        """Multiple attendees should be newline separated."""
        attendees = [
            {"email": "a@example.com", "responseStatus": "accepted"},
            {"email": "b@example.com", "responseStatus": "declined"},
        ]
        result = _format_attendee_details(attendees)
        assert "a@example.com: accepted" in result
        assert "b@example.com: declined" in result

    def test_custom_indent(self):
        """Custom indent should be used in output."""
        attendees = [
            {"email": "a@example.com", "responseStatus": "accepted"},
            {"email": "b@example.com", "responseStatus": "declined"},
        ]
        result = _format_attendee_details(attendees, indent="    ")
        assert "\n    " in result


class TestFormatAttachmentDetails:
    """Tests for _format_attachment_details function."""

    def test_empty_attachments_returns_none(self):
        """Empty attachments list should return 'None'."""
        assert _format_attachment_details([]) == "None"

    def test_single_attachment(self):
        """Single attachment should be formatted correctly."""
        attachments = [
            {
                "title": "Document.pdf",
                "fileUrl": "https://drive.google.com/open?id=123",
                "fileId": "123",
                "mimeType": "application/pdf",
            }
        ]
        result = _format_attachment_details(attachments)
        assert "Document.pdf" in result
        assert "https://drive.google.com/open?id=123" in result
        assert "123" in result
        assert "application/pdf" in result

    def test_attachment_with_missing_fields(self):
        """Attachment with missing fields should use defaults."""
        attachments = [{}]
        result = _format_attachment_details(attachments)
        assert "Untitled" in result
        assert "No URL" in result
        assert "No ID" in result
        assert "Unknown" in result


class TestCorrectTimeFormatForApi:
    """Tests for _correct_time_format_for_api function."""

    def test_none_input_returns_none(self):
        """None input should return None."""
        assert _correct_time_format_for_api(None, "time_min") is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        assert _correct_time_format_for_api("", "time_min") is None

    def test_date_only_format_appends_time(self):
        """Date-only format should append T00:00:00Z."""
        result = _correct_time_format_for_api("2024-05-12", "time_min")
        assert result == "2024-05-12T00:00:00Z"

    def test_datetime_without_timezone_appends_z(self):
        """Datetime without timezone should append Z."""
        result = _correct_time_format_for_api("2024-05-12T10:00:00", "time_min")
        assert result == "2024-05-12T10:00:00Z"

    def test_datetime_with_z_unchanged(self):
        """Datetime already with Z should be unchanged."""
        result = _correct_time_format_for_api("2024-05-12T10:00:00Z", "time_min")
        assert result == "2024-05-12T10:00:00Z"

    def test_datetime_with_offset_unchanged(self):
        """Datetime with timezone offset should be unchanged."""
        result = _correct_time_format_for_api("2024-05-12T10:00:00-07:00", "time_min")
        assert result == "2024-05-12T10:00:00-07:00"

    def test_datetime_with_plus_offset_unchanged(self):
        """Datetime with positive timezone offset should be unchanged."""
        result = _correct_time_format_for_api("2024-05-12T10:00:00+02:00", "time_min")
        assert result == "2024-05-12T10:00:00+02:00"

    def test_invalid_date_format_returns_as_is(self):
        """Invalid date format should be returned as-is."""
        result = _correct_time_format_for_api("not-a-date", "time_min")
        assert result == "not-a-date"

    def test_invalid_date_looking_like_date_returns_as_is(self):
        """Invalid date that looks like a date should be returned as-is."""
        result = _correct_time_format_for_api("2024-13-45", "time_min")
        assert result == "2024-13-45"


class TestNormalizeAttendees:
    """Tests for _normalize_attendees function."""

    def test_none_returns_none(self):
        """None input should return None."""
        assert _normalize_attendees(None) is None

    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        assert _normalize_attendees([]) is None

    def test_email_strings_normalized(self):
        """Email strings should be converted to dicts."""
        result = _normalize_attendees(["user@example.com", "other@example.com"])
        assert result == [{"email": "user@example.com"}, {"email": "other@example.com"}]

    def test_dict_with_email_preserved(self):
        """Dict with email key should be preserved."""
        attendees = [{"email": "user@example.com", "responseStatus": "accepted"}]
        result = _normalize_attendees(attendees)
        assert result == [{"email": "user@example.com", "responseStatus": "accepted"}]

    def test_mixed_strings_and_dicts(self):
        """Mixed strings and dicts should be normalized."""
        attendees = ["user@example.com", {"email": "other@example.com", "optional": True}]
        result = _normalize_attendees(attendees)
        assert result == [{"email": "user@example.com"}, {"email": "other@example.com", "optional": True}]

    def test_invalid_dict_without_email_skipped(self):
        """Dict without email key should be skipped."""
        attendees = [{"name": "John"}, {"email": "valid@example.com"}]
        result = _normalize_attendees(attendees)
        assert result == [{"email": "valid@example.com"}]

    def test_all_invalid_returns_none(self):
        """All invalid attendees should return None."""
        attendees = [{"name": "John"}, 12345]
        result = _normalize_attendees(attendees)
        assert result is None
