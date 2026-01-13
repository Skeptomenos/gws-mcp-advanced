"""Tests for validation utilities."""

import pytest

from core.errors import ValidationError
from core.utils import validate_email, validate_file_id, validate_positive_int


class TestValidateFileId:
    """Test file ID validation."""

    def test_valid_file_id(self):
        assert validate_file_id("abc123") == "abc123"

    def test_valid_alias(self):
        assert validate_file_id("A") == "A"
        assert validate_file_id("z") == "z"

    def test_strips_whitespace(self):
        assert validate_file_id("  abc123  ") == "abc123"

    def test_empty_raises_error(self):
        with pytest.raises(ValidationError):
            validate_file_id("")

    def test_whitespace_only_raises_error(self):
        with pytest.raises(ValidationError):
            validate_file_id("   ")

    def test_invalid_chars_raises_error(self):
        with pytest.raises(ValidationError):
            validate_file_id("file/path")


class TestValidateEmail:
    """Test email validation."""

    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_normalizes_case(self):
        assert validate_email("User@Example.COM") == "user@example.com"

    def test_strips_whitespace(self):
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_invalid_email_raises_error(self):
        with pytest.raises(ValidationError):
            validate_email("not-an-email")

    def test_empty_raises_error(self):
        with pytest.raises(ValidationError):
            validate_email("")


class TestValidatePositiveInt:
    """Test positive integer validation."""

    def test_valid_positive_int(self):
        assert validate_positive_int(10, "count") == 10

    def test_one_is_valid(self):
        assert validate_positive_int(1, "count") == 1

    def test_zero_raises_error(self):
        with pytest.raises(ValidationError):
            validate_positive_int(0, "count")

    def test_negative_raises_error(self):
        with pytest.raises(ValidationError):
            validate_positive_int(-1, "count")

    def test_max_value_enforced(self):
        with pytest.raises(ValidationError):
            validate_positive_int(100, "count", max_value=50)

    def test_at_max_value_ok(self):
        assert validate_positive_int(50, "count", max_value=50) == 50
