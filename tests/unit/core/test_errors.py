"""Tests for custom error classes."""

import pytest

from core.errors import (
    APIError,
    AuthenticationError,
    CredentialsNotFoundError,
    GDriveError,
    ScopeMismatchError,
    SessionBindingError,
    TokenRefreshError,
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


class TestCredentialsNotFoundError:
    """Test CredentialsNotFoundError class."""

    def test_message_includes_email(self):
        error = CredentialsNotFoundError("user@example.com")
        assert "user@example.com" in str(error)
        assert "start_google_auth" in str(error)

    def test_stores_user_email(self):
        error = CredentialsNotFoundError("user@example.com")
        assert error.user_email == "user@example.com"

    def test_inherits_from_authentication_error(self):
        assert issubclass(CredentialsNotFoundError, AuthenticationError)


class TestSessionBindingError:
    """Test SessionBindingError class."""

    def test_message_includes_session_and_reason(self):
        error = SessionBindingError("session-123", "user already bound")
        assert "session-123" in str(error)
        assert "user already bound" in str(error)

    def test_stores_session_id_and_reason(self):
        error = SessionBindingError("session-123", "user already bound")
        assert error.session_id == "session-123"
        assert error.reason == "user already bound"

    def test_inherits_from_authentication_error(self):
        assert issubclass(SessionBindingError, AuthenticationError)


class TestTokenRefreshError:
    """Test TokenRefreshError class."""

    def test_message_includes_email_and_reason(self):
        error = TokenRefreshError("user@example.com", "token revoked")
        assert "user@example.com" in str(error)
        assert "token revoked" in str(error)
        assert "start_google_auth" in str(error)

    def test_stores_user_email_and_reason(self):
        error = TokenRefreshError("user@example.com", "token revoked")
        assert error.user_email == "user@example.com"
        assert error.reason == "token revoked"

    def test_inherits_from_authentication_error(self):
        assert issubclass(TokenRefreshError, AuthenticationError)


class TestScopeMismatchError:
    """Test ScopeMismatchError class."""

    def test_message_includes_missing_scopes(self):
        error = ScopeMismatchError(
            required=["scope1", "scope2", "scope3"],
            available=["scope1"],
        )
        assert "scope2" in str(error) or "scope3" in str(error)
        assert "re-authenticate" in str(error)

    def test_stores_scope_lists(self):
        error = ScopeMismatchError(
            required=["scope1", "scope2"],
            available=["scope1"],
        )
        assert error.required_scopes == ["scope1", "scope2"]
        assert error.available_scopes == ["scope1"]
        assert error.missing_scopes == ["scope2"]

    def test_computes_missing_scopes_correctly(self):
        error = ScopeMismatchError(
            required=["a", "b", "c"],
            available=["b", "d"],
        )
        assert set(error.missing_scopes) == {"a", "c"}

    def test_inherits_from_authentication_error(self):
        assert issubclass(ScopeMismatchError, AuthenticationError)
