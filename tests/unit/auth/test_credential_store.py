"""Unit tests for LocalDirectoryCredentialStore."""

from datetime import datetime, timedelta

import pytest
from google.oauth2.credentials import Credentials

from auth.credential_store import LocalDirectoryCredentialStore


class TestLocalDirectoryCredentialStore:
    """Tests for LocalDirectoryCredentialStore."""

    @pytest.fixture
    def temp_creds_dir(self, tmp_path):
        """Create a temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        return str(creds_dir)

    @pytest.fixture
    def store(self, temp_creds_dir):
        """Create a store instance with temp directory."""
        return LocalDirectoryCredentialStore(temp_creds_dir)

    @pytest.fixture
    def sample_credentials(self):
        """Create sample Google credentials."""
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

    def test_store_and_retrieve_credentials(self, store, sample_credentials):
        """Credentials can be stored and retrieved."""
        user_email = "test@example.com"

        result = store.store_credential(user_email, sample_credentials)
        assert result is True

        retrieved = store.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == sample_credentials.token
        assert retrieved.refresh_token == sample_credentials.refresh_token
        assert retrieved.client_id == sample_credentials.client_id
        assert retrieved.client_secret == sample_credentials.client_secret
        assert retrieved.scopes == sample_credentials.scopes

    def test_get_nonexistent_credential_returns_none(self, store):
        """Getting credentials for unknown user returns None."""
        result = store.get_credential("nonexistent@example.com")
        assert result is None

    def test_delete_credential(self, store, sample_credentials):
        """Credentials can be deleted."""
        user_email = "test@example.com"
        store.store_credential(user_email, sample_credentials)

        result = store.delete_credential(user_email)
        assert result is True

        retrieved = store.get_credential(user_email)
        assert retrieved is None

    def test_delete_nonexistent_credential_succeeds(self, store):
        """Deleting nonexistent credentials returns True (idempotent)."""
        result = store.delete_credential("nonexistent@example.com")
        assert result is True

    def test_list_users_empty(self, store):
        """Empty store returns empty list."""
        users = store.list_users()
        assert users == []

    def test_list_users_with_credentials(self, store, sample_credentials):
        """List users returns all stored users."""
        store.store_credential("alice@example.com", sample_credentials)
        store.store_credential("bob@example.com", sample_credentials)
        store.store_credential("charlie@example.com", sample_credentials)

        users = store.list_users()
        assert len(users) == 3
        assert "alice@example.com" in users
        assert "bob@example.com" in users
        assert "charlie@example.com" in users

    def test_list_users_sorted(self, store, sample_credentials):
        """List users returns sorted list."""
        store.store_credential("charlie@example.com", sample_credentials)
        store.store_credential("alice@example.com", sample_credentials)
        store.store_credential("bob@example.com", sample_credentials)

        users = store.list_users()
        assert users == ["alice@example.com", "bob@example.com", "charlie@example.com"]

    def test_expiry_preserved(self, store, sample_credentials):
        """Token expiry time is preserved through store/retrieve cycle."""
        user_email = "test@example.com"
        store.store_credential(user_email, sample_credentials)

        retrieved = store.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.expiry is not None
        # Allow 1 second tolerance for serialization
        assert abs((retrieved.expiry - sample_credentials.expiry).total_seconds()) < 1

    def test_credentials_survive_store_recreation(self, temp_creds_dir, sample_credentials):
        """Credentials persist across store instance recreation."""
        user_email = "test@example.com"

        store1 = LocalDirectoryCredentialStore(temp_creds_dir)
        store1.store_credential(user_email, sample_credentials)

        # Create new store instance (simulates server restart)
        store2 = LocalDirectoryCredentialStore(temp_creds_dir)

        retrieved = store2.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == sample_credentials.token
        assert retrieved.refresh_token == sample_credentials.refresh_token

    def test_overwrite_existing_credentials(self, store, sample_credentials):
        """Storing credentials for existing user overwrites them."""
        user_email = "test@example.com"
        store.store_credential(user_email, sample_credentials)

        new_credentials = Credentials(
            token="new_access_token",
            refresh_token="new_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="new_client_id",
            client_secret="new_client_secret",
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        store.store_credential(user_email, new_credentials)

        retrieved = store.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == "new_access_token"
        assert retrieved.refresh_token == "new_refresh_token"

    def test_credentials_without_expiry(self, store):
        """Credentials without expiry can be stored and retrieved."""
        user_email = "test@example.com"
        credentials = Credentials(
            token="test_token",
            refresh_token="test_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/drive"],
            expiry=None,
        )

        store.store_credential(user_email, credentials)
        retrieved = store.get_credential(user_email)

        assert retrieved is not None
        assert retrieved.token == "test_token"
        assert retrieved.expiry is None
