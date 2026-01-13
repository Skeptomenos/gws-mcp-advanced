"""Unit tests for OAuth21SessionStore."""

from datetime import datetime, timedelta, timezone

import pytest

from auth.oauth21_session_store import OAuth21SessionStore


class TestOAuth21SessionStore:
    """Tests for OAuth21SessionStore session management."""

    @pytest.fixture
    def store(self, tmp_path, monkeypatch):
        """Create a fresh store with temp directory for state persistence."""
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(tmp_path))
        return OAuth21SessionStore()

    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing."""
        return {
            "user_email": "test@example.com",
            "access_token": "ya29.test_access_token",
            "refresh_token": "1//test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "session_id": "google_test@example.com",
            "mcp_session_id": "mcp_session_123",
            "issuer": "https://accounts.google.com",
        }

    def test_store_and_retrieve_session(self, store, sample_session_data):
        """Session can be stored and credentials retrieved."""
        store.store_session(**sample_session_data)

        credentials = store.get_credentials(sample_session_data["user_email"])
        assert credentials is not None
        assert credentials.token == sample_session_data["access_token"]
        assert credentials.refresh_token == sample_session_data["refresh_token"]

    def test_get_credentials_nonexistent_user(self, store):
        """Getting credentials for unknown user returns None."""
        credentials = store.get_credentials("nonexistent@example.com")
        assert credentials is None

    def test_mcp_session_mapping(self, store, sample_session_data):
        """MCP session ID maps to user email."""
        store.store_session(**sample_session_data)

        user_email = store.get_user_by_mcp_session(sample_session_data["mcp_session_id"])
        assert user_email == sample_session_data["user_email"]

    def test_get_credentials_by_mcp_session(self, store, sample_session_data):
        """Credentials can be retrieved via MCP session ID."""
        store.store_session(**sample_session_data)

        credentials = store.get_credentials_by_mcp_session(sample_session_data["mcp_session_id"])
        assert credentials is not None
        assert credentials.token == sample_session_data["access_token"]

    def test_session_auth_binding_immutable(self, store, sample_session_data):
        """Session binding cannot be changed to different user."""
        store.store_session(**sample_session_data)

        different_user_data = sample_session_data.copy()
        different_user_data["user_email"] = "different@example.com"

        with pytest.raises(ValueError, match="already bound"):
            store.store_session(**different_user_data)

    def test_session_auth_binding_same_user_ok(self, store, sample_session_data):
        """Re-storing session for same user is allowed."""
        store.store_session(**sample_session_data)

        updated_data = sample_session_data.copy()
        updated_data["access_token"] = "new_access_token"

        store.store_session(**updated_data)

        credentials = store.get_credentials(sample_session_data["user_email"])
        assert credentials.token == "new_access_token"

    def test_remove_session(self, store, sample_session_data):
        """Session can be removed."""
        store.store_session(**sample_session_data)
        store.remove_session(sample_session_data["user_email"])

        credentials = store.get_credentials(sample_session_data["user_email"])
        assert credentials is None

        user = store.get_user_by_mcp_session(sample_session_data["mcp_session_id"])
        assert user is None

    def test_has_session(self, store, sample_session_data):
        """has_session returns correct status."""
        assert store.has_session(sample_session_data["user_email"]) is False

        store.store_session(**sample_session_data)
        assert store.has_session(sample_session_data["user_email"]) is True

    def test_has_mcp_session(self, store, sample_session_data):
        """has_mcp_session returns correct status."""
        assert store.has_mcp_session(sample_session_data["mcp_session_id"]) is False

        store.store_session(**sample_session_data)
        assert store.has_mcp_session(sample_session_data["mcp_session_id"]) is True

    def test_get_single_user_email_one_session(self, store, sample_session_data):
        """get_single_user_email returns email when exactly one session exists."""
        store.store_session(**sample_session_data)

        single_user = store.get_single_user_email()
        assert single_user == sample_session_data["user_email"]

    def test_get_single_user_email_no_sessions(self, store):
        """get_single_user_email returns None when no sessions exist."""
        assert store.get_single_user_email() is None

    def test_get_single_user_email_multiple_sessions(self, store, sample_session_data):
        """get_single_user_email returns None when multiple sessions exist."""
        store.store_session(**sample_session_data)

        second_session = sample_session_data.copy()
        second_session["user_email"] = "second@example.com"
        second_session["mcp_session_id"] = "mcp_session_456"
        store.store_session(**second_session)

        assert store.get_single_user_email() is None

    def test_get_stats(self, store, sample_session_data):
        """get_stats returns correct statistics."""
        stats = store.get_stats()
        assert stats["total_sessions"] == 0
        assert stats["mcp_session_mappings"] == 0

        store.store_session(**sample_session_data)

        stats = store.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["mcp_session_mappings"] == 1
        assert sample_session_data["user_email"] in stats["users"]

    def test_get_session_info(self, store, sample_session_data):
        """get_session_info returns complete session data."""
        store.store_session(**sample_session_data)

        info = store.get_session_info(sample_session_data["user_email"])
        assert info is not None
        assert info["access_token"] == sample_session_data["access_token"]
        assert info["issuer"] == sample_session_data["issuer"]
        assert info["scopes"] == sample_session_data["scopes"]


class TestOAuth21SessionStoreOAuthStates:
    """Tests for OAuth state management."""

    @pytest.fixture
    def store(self, tmp_path, monkeypatch):
        """Create a fresh store with temp directory."""
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(tmp_path))
        return OAuth21SessionStore()

    def test_store_and_validate_oauth_state(self, store):
        """OAuth state can be stored and validated."""
        state = "test_state_12345"
        session_id = "mcp_session_123"

        store.store_oauth_state(state, session_id=session_id)

        result = store.validate_and_consume_oauth_state(state, session_id=session_id)
        assert result["session_id"] == session_id

    def test_oauth_state_consumed_on_validation(self, store):
        """OAuth state is consumed (deleted) after validation."""
        state = "test_state_12345"
        store.store_oauth_state(state)

        store.validate_and_consume_oauth_state(state)

        with pytest.raises(ValueError, match="Invalid or expired"):
            store.validate_and_consume_oauth_state(state)

    def test_oauth_state_session_mismatch_rejected(self, store):
        """OAuth state with wrong session ID is rejected."""
        state = "test_state_12345"
        store.store_oauth_state(state, session_id="original_session")

        with pytest.raises(ValueError, match="does not match"):
            store.validate_and_consume_oauth_state(state, session_id="different_session")

    def test_oauth_state_empty_raises_error(self, store):
        """Empty OAuth state raises ValueError."""
        with pytest.raises(ValueError, match="must be provided"):
            store.store_oauth_state("")

    def test_oauth_state_validation_empty_raises_error(self, store):
        """Validating empty state raises ValueError."""
        with pytest.raises(ValueError, match="Missing"):
            store.validate_and_consume_oauth_state("")


class TestOAuth21SessionStoreCredentialsValidation:
    """Tests for credential access validation."""

    @pytest.fixture
    def store(self, tmp_path, monkeypatch):
        """Create a fresh store with temp directory."""
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(tmp_path))
        return OAuth21SessionStore()

    @pytest.fixture
    def stored_session(self, store):
        """Store a session and return the data."""
        data = {
            "user_email": "test@example.com",
            "access_token": "test_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "mcp_session_id": "mcp_123",
        }
        store.store_session(**data)
        return data

    def test_get_credentials_with_validation_auth_token_match(self, store, stored_session):
        """Credentials returned when auth token email matches."""
        credentials = store.get_credentials_with_validation(
            requested_user_email=stored_session["user_email"],
            auth_token_email=stored_session["user_email"],
        )
        assert credentials is not None
        assert credentials.token == stored_session["access_token"]

    def test_get_credentials_with_validation_auth_token_mismatch(self, store, stored_session):
        """Credentials denied when auth token email doesn't match."""
        credentials = store.get_credentials_with_validation(
            requested_user_email=stored_session["user_email"],
            auth_token_email="different@example.com",
        )
        assert credentials is None

    def test_get_credentials_with_validation_session_binding_match(self, store, stored_session):
        """Credentials returned when session binding matches."""
        credentials = store.get_credentials_with_validation(
            requested_user_email=stored_session["user_email"],
            session_id=stored_session["mcp_session_id"],
        )
        assert credentials is not None

    def test_get_credentials_with_validation_session_binding_mismatch(self, store, stored_session):
        """Credentials denied when session is bound to different user."""
        credentials = store.get_credentials_with_validation(
            requested_user_email="different@example.com",
            session_id=stored_session["mcp_session_id"],
        )
        assert credentials is None

    def test_get_credentials_with_validation_no_session_no_token(self, store, stored_session):
        """Credentials denied when no session or token provided."""
        credentials = store.get_credentials_with_validation(
            requested_user_email=stored_session["user_email"],
        )
        assert credentials is None
