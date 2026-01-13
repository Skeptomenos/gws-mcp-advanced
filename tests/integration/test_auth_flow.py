"""Integration tests for authentication flow.

These tests verify the complete auth flow works correctly,
including credential persistence across "restarts".
"""

from datetime import datetime, timedelta

import pytest
from google.oauth2.credentials import Credentials

from auth.credential_store import LocalDirectoryCredentialStore
from auth.oauth21_session_store import OAuth21SessionStore


class TestCredentialPersistence:
    """Test that credentials persist correctly across store instances."""

    @pytest.fixture
    def temp_creds_dir(self, tmp_path):
        """Create a temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        return str(creds_dir)

    @pytest.fixture
    def sample_credentials(self):
        """Create sample credential data."""
        return Credentials(
            token="ya29.test_access_token",
            refresh_token="1//test_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client_id.apps.googleusercontent.com",
            client_secret="test_client_secret",
            scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/gmail.readonly",
            ],
            expiry=datetime.utcnow() + timedelta(hours=1),
        )

    def test_credentials_survive_store_recreation(self, temp_creds_dir, sample_credentials):
        """Credentials should be retrievable after creating a new store instance."""
        user_email = "test@example.com"

        store1 = LocalDirectoryCredentialStore(temp_creds_dir)
        store1.store_credential(user_email, sample_credentials)

        store2 = LocalDirectoryCredentialStore(temp_creds_dir)

        retrieved = store2.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == sample_credentials.token
        assert retrieved.refresh_token == sample_credentials.refresh_token

    def test_session_mapping_survives_restart(self, tmp_path, monkeypatch):
        """Verify that session mappings persist across store recreation (server restart)."""
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(tmp_path))

        user_email = "test@example.com"
        session_id = "mcp_session_123"

        store1 = OAuth21SessionStore()
        store1.store_session(
            user_email=user_email,
            access_token="test_token",
            token_uri="https://oauth2.googleapis.com/token",
            mcp_session_id=session_id,
        )

        assert store1.get_user_by_mcp_session(session_id) == user_email

        store2 = OAuth21SessionStore()

        assert store2.get_user_by_mcp_session(session_id) == user_email


class TestSessionRecovery:
    """Test session recovery scenarios."""

    @pytest.fixture
    def temp_creds_dir(self, tmp_path, monkeypatch):
        """Create and configure temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(creds_dir))
        return str(creds_dir)

    def test_single_user_mode_finds_credentials(self, temp_creds_dir):
        """In single-user mode, credentials can be found for the only user."""
        user_email = "user@example.com"
        credentials = Credentials(
            token="test_token",
            refresh_token="test_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
            expiry=datetime.utcnow() + timedelta(hours=1),
        )

        store = LocalDirectoryCredentialStore(temp_creds_dir)
        store.store_credential(user_email, credentials)

        users = store.list_users()
        assert len(users) == 1
        assert users[0] == user_email

        retrieved = store.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == "test_token"


class TestTokenRefresh:
    """Test token refresh scenarios."""

    @pytest.fixture
    def temp_creds_dir(self, tmp_path, monkeypatch):
        """Create and configure temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(creds_dir))
        return str(creds_dir)

    def test_updated_credentials_persist(self, temp_creds_dir):
        """When credentials are updated, the new values persist."""
        user_email = "test@example.com"
        store = LocalDirectoryCredentialStore(temp_creds_dir)

        original_creds = Credentials(
            token="original_token",
            refresh_token="original_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/drive"],
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        store.store_credential(user_email, original_creds)

        refreshed_creds = Credentials(
            token="refreshed_token",
            refresh_token="original_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/drive"],
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        store.store_credential(user_email, refreshed_creds)

        new_store = LocalDirectoryCredentialStore(temp_creds_dir)
        retrieved = new_store.get_credential(user_email)

        assert retrieved is not None
        assert retrieved.token == "refreshed_token"
        assert retrieved.refresh_token == "original_refresh"


class TestMultiUserIsolation:
    """Test that multiple users are properly isolated."""

    @pytest.fixture
    def temp_creds_dir(self, tmp_path, monkeypatch):
        """Create and configure temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(creds_dir))
        return str(creds_dir)

    def test_users_have_separate_credentials(self, temp_creds_dir):
        """Each user has their own credentials."""
        store = LocalDirectoryCredentialStore(temp_creds_dir)

        alice_creds = Credentials(
            token="alice_token",
            refresh_token="alice_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        bob_creds = Credentials(
            token="bob_token",
            refresh_token="bob_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/gmail"],
        )

        store.store_credential("alice@example.com", alice_creds)
        store.store_credential("bob@example.com", bob_creds)

        alice_retrieved = store.get_credential("alice@example.com")
        bob_retrieved = store.get_credential("bob@example.com")

        assert alice_retrieved.token == "alice_token"
        assert bob_retrieved.token == "bob_token"
        assert alice_retrieved.scopes != bob_retrieved.scopes

    def test_session_binding_prevents_cross_access(self, tmp_path, monkeypatch):
        """Session bound to one user cannot access another user's credentials."""
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(tmp_path))

        store = OAuth21SessionStore()

        store.store_session(
            user_email="alice@example.com",
            access_token="alice_token",
            token_uri="https://oauth2.googleapis.com/token",
            mcp_session_id="alice_session",
        )
        store.store_session(
            user_email="bob@example.com",
            access_token="bob_token",
            token_uri="https://oauth2.googleapis.com/token",
            mcp_session_id="bob_session",
        )

        alice_creds = store.get_credentials_with_validation(
            requested_user_email="alice@example.com",
            session_id="alice_session",
        )
        assert alice_creds is not None
        assert alice_creds.token == "alice_token"

        cross_access = store.get_credentials_with_validation(
            requested_user_email="bob@example.com",
            session_id="alice_session",
        )
        assert cross_access is None


class TestOAuthStatePersistence:
    """Test OAuth state persistence across restarts."""

    @pytest.fixture
    def temp_dir(self, tmp_path, monkeypatch):
        """Create and configure temporary directory."""
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(tmp_path))
        return str(tmp_path)

    def test_oauth_state_survives_restart(self, temp_dir):
        """OAuth state persists across store recreation."""
        state = "test_oauth_state_12345"
        session_id = "mcp_session_123"

        store1 = OAuth21SessionStore()
        store1.store_oauth_state(state, session_id=session_id)

        store2 = OAuth21SessionStore()

        result = store2.validate_and_consume_oauth_state(state, session_id=session_id)
        assert result["session_id"] == session_id
