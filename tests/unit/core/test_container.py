"""Tests for the dependency injection container."""

import pytest

from core.container import (
    Container,
    CredentialStoreProtocol,
    SessionStoreProtocol,
    get_container,
    reset_container,
    set_container,
)


class MockCredentialStore:
    """Mock implementation of CredentialStoreProtocol for testing."""

    def __init__(self):
        self._credentials: dict = {}

    def get_credential(self, user_email: str):
        return self._credentials.get(user_email)

    def store_credential(self, user_email: str, credentials) -> bool:
        self._credentials[user_email] = credentials
        return True

    def delete_credential(self, user_email: str) -> bool:
        if user_email in self._credentials:
            del self._credentials[user_email]
            return True
        return False

    def list_users(self) -> list[str]:
        return list(self._credentials.keys())


class MockSessionStore:
    """Mock implementation of SessionStoreProtocol for testing."""

    def __init__(self):
        self._sessions: dict = {}
        self._mcp_mapping: dict = {}

    def store_session(self, user_email: str, **kwargs) -> None:
        self._sessions[user_email] = kwargs
        if mcp_session_id := kwargs.get("mcp_session_id"):
            self._mcp_mapping[mcp_session_id] = user_email

    def get_credentials(self, user_email: str):
        return self._sessions.get(user_email, {}).get("credentials")

    def get_credentials_by_mcp_session(self, mcp_session_id: str):
        user_email = self._mcp_mapping.get(mcp_session_id)
        if user_email:
            return self.get_credentials(user_email)
        return None

    def get_user_by_mcp_session(self, mcp_session_id: str) -> str | None:
        return self._mcp_mapping.get(mcp_session_id)


@pytest.fixture(autouse=True)
def clean_container():
    """Reset container before and after each test."""
    reset_container()
    yield
    reset_container()


class TestProtocols:
    """Test that mock implementations satisfy protocols."""

    def test_mock_credential_store_satisfies_protocol(self):
        store = MockCredentialStore()
        assert isinstance(store, CredentialStoreProtocol)

    def test_mock_session_store_satisfies_protocol(self):
        store = MockSessionStore()
        assert isinstance(store, SessionStoreProtocol)


class TestContainer:
    """Test Container class."""

    def test_container_with_custom_stores(self):
        cred_store = MockCredentialStore()
        session_store = MockSessionStore()
        container = Container(credential_store=cred_store, session_store=session_store)

        assert container.credential_store is cred_store
        assert container.session_store is session_store

    def test_container_defaults_to_real_implementations(self):
        container = Container()

        assert container.credential_store is not None
        assert container.session_store is not None
        assert isinstance(container.credential_store, CredentialStoreProtocol)
        assert isinstance(container.session_store, SessionStoreProtocol)


class TestContainerGlobals:
    """Test global container management functions."""

    def test_get_container_creates_default(self):
        container = get_container()

        assert container is not None
        assert isinstance(container, Container)

    def test_get_container_returns_same_instance(self):
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_set_container_replaces_global(self):
        custom_container = Container(
            credential_store=MockCredentialStore(),
            session_store=MockSessionStore(),
        )
        set_container(custom_container)

        assert get_container() is custom_container

    def test_reset_container_clears_global(self):
        get_container()
        reset_container()
        container1 = get_container()
        reset_container()
        container2 = get_container()

        assert container1 is not container2


class TestMockCredentialStore:
    """Test MockCredentialStore functionality."""

    def test_store_and_retrieve(self):
        store = MockCredentialStore()
        store.store_credential("user@example.com", {"token": "abc123"})

        result = store.get_credential("user@example.com")
        assert result == {"token": "abc123"}

    def test_get_nonexistent_returns_none(self):
        store = MockCredentialStore()
        assert store.get_credential("nobody@example.com") is None

    def test_delete_credential(self):
        store = MockCredentialStore()
        store.store_credential("user@example.com", {"token": "abc123"})
        result = store.delete_credential("user@example.com")

        assert result is True
        assert store.get_credential("user@example.com") is None

    def test_delete_nonexistent_returns_false(self):
        store = MockCredentialStore()
        assert store.delete_credential("nobody@example.com") is False

    def test_list_users(self):
        store = MockCredentialStore()
        store.store_credential("alice@example.com", {})
        store.store_credential("bob@example.com", {})

        users = store.list_users()
        assert set(users) == {"alice@example.com", "bob@example.com"}


class TestMockSessionStore:
    """Test MockSessionStore functionality."""

    def test_store_and_retrieve_by_email(self):
        store = MockSessionStore()
        store.store_session("user@example.com", credentials={"token": "xyz"})

        result = store.get_credentials("user@example.com")
        assert result == {"token": "xyz"}

    def test_store_and_retrieve_by_mcp_session(self):
        store = MockSessionStore()
        store.store_session(
            "user@example.com",
            mcp_session_id="mcp-123",
            credentials={"token": "xyz"},
        )

        result = store.get_credentials_by_mcp_session("mcp-123")
        assert result == {"token": "xyz"}

    def test_get_user_by_mcp_session(self):
        store = MockSessionStore()
        store.store_session("user@example.com", mcp_session_id="mcp-456")

        result = store.get_user_by_mcp_session("mcp-456")
        assert result == "user@example.com"

    def test_get_user_by_unknown_session_returns_none(self):
        store = MockSessionStore()
        assert store.get_user_by_mcp_session("unknown") is None
