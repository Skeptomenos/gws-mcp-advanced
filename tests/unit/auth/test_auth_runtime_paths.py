"""Targeted runtime-path regression tests for auth/session flows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from google.oauth2.credentials import Credentials

import auth.oauth21_session_store as oauth21_session_store_module
from auth.middleware.auth_info import AuthInfoMiddleware
from auth.oauth21_session_store import ensure_session_from_access_token, get_credentials_from_token


class _DummyFastMCPContext:
    """Minimal FastMCP context double for middleware tests."""

    def __init__(self, session_id: str | None = None) -> None:
        self._state: dict[str, object] = {}
        self.session_id = session_id

    def set_state(self, key: str, value: object) -> None:
        self._state[key] = value

    def get_state(self, key: str) -> object | None:
        return self._state.get(key)


@pytest.mark.asyncio
async def test_try_stdio_session_auth_uses_requested_user_binding(monkeypatch):
    """Stdio auth should prefer an explicitly requested user with a cached session."""
    middleware = AuthInfoMiddleware()
    context_obj = _DummyFastMCPContext()
    context = SimpleNamespace(
        fastmcp_context=context_obj,
        request=SimpleNamespace(params={"user_google_email": "alice@example.com"}),
        arguments=None,
    )

    class _Store:
        def has_session(self, email: str) -> bool:
            return email == "alice@example.com"

    monkeypatch.setattr("auth.config.get_transport_mode", lambda: "stdio")
    monkeypatch.setattr("auth.oauth21_session_store.get_oauth21_session_store", lambda: _Store())

    authenticated = await middleware._try_stdio_session_auth(context)  # noqa: SLF001 - private method tested by design

    assert authenticated is True
    assert context_obj.get_state("authenticated_user_email") == "alice@example.com"
    assert context_obj.get_state("authenticated_via") == "stdio_session"
    assert context_obj.get_state("auth_provider_type") == "oauth21_stdio"


@pytest.mark.asyncio
async def test_try_stdio_session_auth_falls_back_to_single_user(monkeypatch):
    """Stdio auth should fall back to single-user session when no explicit request is bound."""
    middleware = AuthInfoMiddleware()
    context_obj = _DummyFastMCPContext()
    context = SimpleNamespace(
        fastmcp_context=context_obj,
        request=SimpleNamespace(params={"user_google_email": "unknown@example.com"}),
        arguments=None,
    )

    class _Store:
        def has_session(self, _email: str) -> bool:
            return False

        def get_single_user_email(self) -> str:
            return "solo@example.com"

    monkeypatch.setattr("auth.config.get_transport_mode", lambda: "stdio")
    monkeypatch.setattr("auth.oauth21_session_store.get_oauth21_session_store", lambda: _Store())

    authenticated = await middleware._try_stdio_session_auth(context)  # noqa: SLF001 - private method tested by design

    assert authenticated is True
    assert context_obj.get_state("authenticated_user_email") == "solo@example.com"
    assert context_obj.get_state("authenticated_via") == "stdio_single_session"
    assert context_obj.get_state("user_email") == "solo@example.com"
    assert context_obj.get_state("username") == "solo@example.com"


@pytest.mark.asyncio
async def test_try_mcp_session_binding_sets_authenticated_user(monkeypatch):
    """MCP session binding should authenticate using stored session-user mapping."""
    middleware = AuthInfoMiddleware()
    context_obj = _DummyFastMCPContext(session_id="mcp_session_123")
    context = SimpleNamespace(fastmcp_context=context_obj, request=None, arguments=None)

    class _Store:
        def get_user_by_mcp_session(self, session_id: str) -> str | None:
            if session_id == "mcp_session_123":
                return "bound@example.com"
            return None

    monkeypatch.setattr("auth.oauth21_session_store.get_oauth21_session_store", lambda: _Store())

    authenticated = await middleware._try_mcp_session_binding(context)  # noqa: SLF001 - private method tested by design

    assert authenticated is True
    assert context_obj.get_state("authenticated_user_email") == "bound@example.com"
    assert context_obj.get_state("authenticated_via") == "mcp_session_binding"
    assert context_obj.get_state("auth_provider_type") == "oauth21_session"


def test_ensure_session_from_access_token_uses_claim_email_and_stores_session(monkeypatch):
    """Token bridge should derive claim email and persist a session mapping when user_email is omitted."""
    captured: dict[str, object] = {}

    class _Store:
        def store_session(self, **kwargs) -> None:
            captured.update(kwargs)

    expiry = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    access_token = SimpleNamespace(
        token="ya29.claim_token",
        claims={"email": "claim@example.com"},
        scopes=["scope.read"],
        expires_at=int(expiry.timestamp()),
    )

    monkeypatch.setattr(oauth21_session_store_module, "_auth_provider", None)
    monkeypatch.setattr(
        oauth21_session_store_module, "_resolve_client_credentials", lambda: ("client-id", "client-secret")
    )
    monkeypatch.setattr(oauth21_session_store_module, "get_oauth21_session_store", lambda: _Store())

    credentials = ensure_session_from_access_token(
        access_token=access_token,
        user_email=None,
        mcp_session_id="mcp-bound-id",
    )

    assert credentials is not None
    assert credentials.token == "ya29.claim_token"
    assert captured["user_email"] == "claim@example.com"
    assert captured["mcp_session_id"] == "mcp-bound-id"
    assert captured["token_uri"] == "https://oauth2.googleapis.com/token"
    assert captured["issuer"] == "https://accounts.google.com"


def test_get_credentials_from_token_prefers_matching_store_credentials(monkeypatch):
    """Token bridge should return persisted credentials when user+token already match the store."""
    stored_credentials = Credentials(
        token="ya29.store_token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["scope.read"],
    )

    class _Store:
        def get_credentials(self, _user_email: str) -> Credentials:
            return stored_credentials

    monkeypatch.setattr(oauth21_session_store_module, "get_oauth21_session_store", lambda: _Store())
    monkeypatch.setattr(oauth21_session_store_module, "_auth_provider", None)

    result = get_credentials_from_token("ya29.store_token", user_email="user@example.com")

    assert result is stored_credentials


def test_get_credentials_from_token_uses_provider_cache_record(monkeypatch):
    """Token bridge should hydrate credentials from provider token cache when available."""
    sentinel_credentials = Credentials(
        token="ya29.cache_token",
        refresh_token=None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
    )
    access_record = SimpleNamespace(token="ya29.cache_token")
    provider = SimpleNamespace(_access_tokens={"ya29.cache_token": access_record})
    observed: dict[str, object] = {}

    class _Store:
        def get_credentials(self, _user_email: str) -> None:
            return None

    def _fake_ensure_session(record: object, email: str | None, _mcp_session_id: str | None = None) -> Credentials:
        observed["record"] = record
        observed["email"] = email
        return sentinel_credentials

    monkeypatch.setattr(oauth21_session_store_module, "get_oauth21_session_store", lambda: _Store())
    monkeypatch.setattr(oauth21_session_store_module, "_auth_provider", provider)
    monkeypatch.setattr(oauth21_session_store_module, "ensure_session_from_access_token", _fake_ensure_session)

    result = get_credentials_from_token("ya29.cache_token", user_email="cached@example.com")

    assert result is sentinel_credentials
    assert observed["record"] is access_record
    assert observed["email"] == "cached@example.com"


def test_get_credentials_from_token_fallback_builds_minimal_credentials(monkeypatch):
    """Token bridge should return minimal credentials when neither store nor provider has token metadata."""

    class _Store:
        def get_credentials(self, _user_email: str) -> None:
            return None

    monkeypatch.setattr(oauth21_session_store_module, "get_oauth21_session_store", lambda: _Store())
    monkeypatch.setattr(oauth21_session_store_module, "_auth_provider", None)
    monkeypatch.setattr(
        oauth21_session_store_module, "_resolve_client_credentials", lambda: ("client-id", "client-secret")
    )

    result = get_credentials_from_token("ya29.fallback_token")

    assert result is not None
    assert result.token == "ya29.fallback_token"
    assert result.token_uri == "https://oauth2.googleapis.com/token"
    assert result.client_id == "client-id"
    assert result.client_secret == "client-secret"
    assert result.expiry is not None
