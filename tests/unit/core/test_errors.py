"""Tests for custom error classes."""

import pytest

from core.errors import (
    APIError,
    AuthenticationError,
    GDriveError,
    ValidationError,
    WorkspaceMCPError,
)


class TestErrorHierarchy:
    """Test error class inheritance."""

    def test_base_error_is_exception(self):
        assert issubclass(WorkspaceMCPError, Exception)

    def test_auth_error_inherits_base(self):
        assert issubclass(AuthenticationError, WorkspaceMCPError)

    def test_validation_error_inherits_base(self):
        assert issubclass(ValidationError, WorkspaceMCPError)

    def test_api_error_inherits_base(self):
        assert issubclass(APIError, WorkspaceMCPError)


class TestAPIError:
    """Test APIError class."""

    def test_api_error_with_status_code(self):
        error = APIError("Test error", status_code=500)
        assert error.status_code == 500
        assert str(error) == "Test error"

    def test_api_error_without_status_code(self):
        error = APIError("Test error")
        assert error.status_code is None

    def test_api_error_is_catchable_as_base(self):
        with pytest.raises(WorkspaceMCPError):
            raise APIError("Test")


class TestGDriveError:
    """Test GDriveError class."""

    def test_gdrive_error_message(self):
        error = GDriveError(message="File not found")
        assert str(error) == "File not found"

    def test_gdrive_error_with_details(self):
        error = GDriveError(message="Error", details={"file_id": "123"})
        assert error.details == {"file_id": "123"}
