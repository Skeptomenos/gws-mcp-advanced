"""Unit tests for auth flow mode selection and challenge orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from google.oauth2.credentials import Credentials

from auth.google_auth import (
    AUTH_FLOW_AUTO,
    AUTH_FLOW_CALLBACK,
    AUTH_FLOW_DEVICE,
    _get_effective_auth_flow_mode,
    _resolve_callback_port_policy,
    _start_or_resume_device_auth_flow,
    get_authenticated_google_service,
    initiate_auth_challenge,
    resolve_oauth_redirect_uri_for_auth_flow,
)
from auth.oauth_clients import OAuthClientSelection
from core.errors import GoogleAuthenticationError


def _valid_credentials() -> Credentials:
    return Credentials(
        token="ya29.test_access_token",
        refresh_token="1//test_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["https://www.googleapis.com/auth/drive"],
        expiry=datetime.utcnow() + timedelta(hours=1),
    )


def _tool_callable(tool_obj: object) -> Callable[..., Awaitable[str]]:
    tool_fn = getattr(tool_obj, "fn", None) or getattr(tool_obj, "func", None) or getattr(tool_obj, "_fn", None)
    assert callable(tool_fn), "Could not resolve callable tool function"
    return cast(Callable[..., Awaitable[str]], tool_fn)


def test_effective_auth_flow_mode_auto_prefers_device_for_stdio(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_AUTH_FLOW", AUTH_FLOW_AUTO)
    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "stdio")

    assert _get_effective_auth_flow_mode() == AUTH_FLOW_DEVICE


def test_effective_auth_flow_mode_auto_prefers_callback_for_http(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_AUTH_FLOW", AUTH_FLOW_AUTO)
    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "streamable-http")

    assert _get_effective_auth_flow_mode() == AUTH_FLOW_CALLBACK


def test_effective_auth_flow_mode_honors_explicit_setting(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_AUTH_FLOW", AUTH_FLOW_CALLBACK)
    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "stdio")
    assert _get_effective_auth_flow_mode() == AUTH_FLOW_CALLBACK

    monkeypatch.setenv("WORKSPACE_MCP_AUTH_FLOW", AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "streamable-http")
    assert _get_effective_auth_flow_mode() == AUTH_FLOW_DEVICE


def test_effective_auth_flow_mode_honors_client_flow_preference_callback(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_AUTH_FLOW", AUTH_FLOW_AUTO)
    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "stdio")
    monkeypatch.setattr(
        "auth.google_auth.resolve_oauth_client_for_user",
        lambda user_email, **_: OAuthClientSelection(
            client_key="private",
            client_id="private-client-id",
            client_secret="private-client-secret",
            source="account_mapping",
            selection_mode="mapped_only",
            flow_preference=AUTH_FLOW_CALLBACK,
        ),
    )

    assert _get_effective_auth_flow_mode("user@example.com") == AUTH_FLOW_CALLBACK


def test_effective_auth_flow_mode_honors_client_flow_preference_device(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_AUTH_FLOW", AUTH_FLOW_AUTO)
    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "streamable-http")
    monkeypatch.setattr(
        "auth.google_auth.resolve_oauth_client_for_user",
        lambda user_email, **_: OAuthClientSelection(
            client_key="enterprise",
            client_id="enterprise-client-id",
            client_secret="enterprise-client-secret",
            source="domain_mapping",
            selection_mode="mapped_only",
            flow_preference=AUTH_FLOW_DEVICE,
        ),
    )

    assert _get_effective_auth_flow_mode("user@example.com") == AUTH_FLOW_DEVICE


def test_resolve_callback_port_policy_fails_for_mapped_client_missing_client_type():
    oauth_client = OAuthClientSelection(
        client_key="work",
        client_id="client-id",
        client_secret="client-secret",
        source="account_map",
        selection_mode="mapped_only",
        redirect_uris=["http://localhost:9876/oauth2callback"],
        client_type=None,
    )

    with pytest.raises(GoogleAuthenticationError, match="client_type"):
        _resolve_callback_port_policy(oauth_client)


def test_resolve_callback_port_policy_fails_for_mapped_web_client_missing_redirect_uris():
    oauth_client = OAuthClientSelection(
        client_key="work",
        client_id="client-id",
        client_secret="client-secret",
        source="domain_map",
        selection_mode="mapped_only",
        redirect_uris=None,
        client_type="web",
    )

    with pytest.raises(GoogleAuthenticationError, match="redirect_uris"):
        _resolve_callback_port_policy(oauth_client)


def test_resolve_callback_port_policy_disables_fallback_for_mapped_web_redirects():
    oauth_client = OAuthClientSelection(
        client_key="work",
        client_id="client-id",
        client_secret="client-secret",
        source="script_map",
        selection_mode="mapped_only",
        redirect_uris=[
            "http://localhost:9876/oauth2callback",
            "http://localhost:9877/oauth2callback",
            "http://localhost:9876/oauth2callback",
        ],
        client_type="web",
    )

    preferred_ports, allow_sequential_fallback = _resolve_callback_port_policy(oauth_client)

    assert preferred_ports == [9876, 9877]
    assert allow_sequential_fallback is False


def test_resolve_callback_port_policy_allows_fallback_for_installed_client():
    oauth_client = OAuthClientSelection(
        client_key="local-default",
        client_id="client-id",
        client_secret="client-secret",
        source="default_client",
        selection_mode="default_first",
        redirect_uris=None,
        client_type="installed",
    )

    preferred_ports, allow_sequential_fallback = _resolve_callback_port_policy(oauth_client)

    assert preferred_ports == []
    assert allow_sequential_fallback is True


def test_resolve_callback_port_policy_allows_fallback_for_legacy_env_client():
    oauth_client = OAuthClientSelection(
        client_key="legacy-env",
        client_id="client-id",
        client_secret="client-secret",
        source="legacy_env",
        selection_mode="legacy",
        redirect_uris=None,
        client_type=None,
    )

    preferred_ports, allow_sequential_fallback = _resolve_callback_port_policy(oauth_client)

    assert preferred_ports == []
    assert allow_sequential_fallback is True


def test_resolve_oauth_redirect_uri_threads_sequential_fallback_policy(monkeypatch):
    observed: dict[str, object] = {}

    def _start_server(*, preferred_ports=None, allow_sequential_fallback=True, base_uri="http://localhost"):
        observed["preferred_ports"] = preferred_ports
        observed["allow_sequential_fallback"] = allow_sequential_fallback
        observed["base_uri"] = base_uri
        return True, "", "http://localhost:9877/oauth2callback"

    monkeypatch.setattr("auth.google_auth.get_transport_mode", lambda: "stdio")
    monkeypatch.setattr("auth.oauth_callback_server.start_oauth_callback_server", _start_server)

    redirect_uri = resolve_oauth_redirect_uri_for_auth_flow(
        preferred_ports=[9876, 9877],
        allow_sequential_fallback=False,
    )

    assert redirect_uri == "http://localhost:9877/oauth2callback"
    assert observed["preferred_ports"] == [9876, 9877]
    assert observed["allow_sequential_fallback"] is False


def test_start_or_resume_device_auth_reuses_pending_flow(monkeypatch):
    class _Store:
        def get_pending_device_flow(self, user_email: str, oauth_client_key: str | None = None):
            assert user_email == "user@example.com"
            assert oauth_client_key == "legacy-env"
            return {
                "user_code": "ABCD-EFGH",
                "verification_url": "https://www.google.com/device",
                "verification_url_complete": "https://www.google.com/device?user_code=ABCD-EFGH",
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            }

    monkeypatch.setattr("auth.google_auth.get_oauth21_session_store", lambda: _Store())
    monkeypatch.setattr(
        "auth.google_auth._resolve_client_id_and_secret",
        lambda _user, override_client_key=None: (
            OAuthClientSelection(
                client_key="legacy-env",
                client_id="legacy-client-id",
                client_secret="legacy-client-secret",
                source="legacy_env",
                selection_mode="legacy",
            ),
            "legacy-client-id",
            "legacy-client-secret",
        ),
    )

    message = _start_or_resume_device_auth_flow(
        user_google_email="user@example.com",
        service_name="Google Drive",
        required_scopes=["scope1"],
    )

    assert "User Code: `ABCD-EFGH`" in message
    assert "Direct Verification Link:" in message


@pytest.mark.asyncio
async def test_initiate_auth_challenge_device_returns_credentials(monkeypatch):
    credentials = _valid_credentials()
    poll_mock = AsyncMock(return_value=(credentials, None))

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth._poll_pending_device_auth_flow", poll_mock)

    resolved_credentials, message = await initiate_auth_challenge(
        user_google_email="user@example.com",
        service_name="Google Drive",
        required_scopes=["scope1"],
        session_id="mcp-session",
    )

    assert resolved_credentials is credentials
    assert "Authentication completed successfully" in message
    poll_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_initiate_auth_challenge_device_returns_actionable_message(monkeypatch):
    poll_mock = AsyncMock(return_value=(None, "authorization_pending"))

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth._poll_pending_device_auth_flow", poll_mock)
    monkeypatch.setattr("auth.google_auth._start_or_resume_device_auth_flow", lambda **_: "do-device-auth")

    resolved_credentials, message = await initiate_auth_challenge(
        user_google_email="user@example.com",
        service_name="Google Drive",
        required_scopes=["scope1"],
        session_id="mcp-session",
    )

    assert resolved_credentials is None
    assert message == "do-device-auth"


@pytest.mark.asyncio
async def test_initiate_auth_challenge_device_raises_on_poll_error(monkeypatch):
    poll_mock = AsyncMock(return_value=(None, "error:invalid_client"))

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth._poll_pending_device_auth_flow", poll_mock)

    with pytest.raises(GoogleAuthenticationError, match="Device authorization polling failed"):
        await initiate_auth_challenge(
            user_google_email="user@example.com",
            service_name="Google Drive",
            required_scopes=["scope1"],
            session_id="mcp-session",
        )


@pytest.mark.asyncio
async def test_initiate_auth_challenge_device_invalid_client_falls_back_to_callback_in_auto_mode(monkeypatch):
    start_auth_flow_mock = AsyncMock(return_value="callback-auth-link")

    monkeypatch.setattr("auth.google_auth._get_auth_flow_mode", lambda: AUTH_FLOW_AUTO)
    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_DEVICE)
    monkeypatch.setattr(
        "auth.google_auth._resolve_oauth_client_selection",
        lambda *_args, **_kwargs: OAuthClientSelection(
            client_key="legacy-env",
            client_id="client-id",
            client_secret="client-secret",
            source="legacy_env",
            selection_mode="legacy",
            client_type=None,
        ),
    )
    monkeypatch.setattr("auth.google_auth._poll_pending_device_auth_flow", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(
        "auth.google_auth._start_or_resume_device_auth_flow",
        lambda **_: (_ for _ in ()).throw(
            GoogleAuthenticationError("Failed to start device authorization flow: invalid_client: Invalid client type")
        ),
    )
    monkeypatch.setattr(
        "auth.google_auth.resolve_oauth_redirect_uri_for_auth_flow",
        lambda **_: "http://localhost:9876/oauth2callback",
    )
    monkeypatch.setattr("auth.google_auth.start_auth_flow", start_auth_flow_mock)

    resolved_credentials, message = await initiate_auth_challenge(
        user_google_email="user@example.com",
        service_name="Google Drive",
        required_scopes=["scope1"],
        session_id="mcp-session",
    )

    assert resolved_credentials is None
    assert "Automatically falling back to callback flow" in message
    assert "callback-auth-link" in message
    start_auth_flow_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_initiate_auth_challenge_device_invalid_client_raises_in_explicit_device_mode(monkeypatch):
    monkeypatch.setattr("auth.google_auth._get_auth_flow_mode", lambda: AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth._poll_pending_device_auth_flow", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(
        "auth.google_auth._start_or_resume_device_auth_flow",
        lambda **_: (_ for _ in ()).throw(
            GoogleAuthenticationError("Failed to start device authorization flow: invalid_client: Invalid client type")
        ),
    )

    with pytest.raises(GoogleAuthenticationError, match="invalid_client"):
        await initiate_auth_challenge(
            user_google_email="user@example.com",
            service_name="Google Drive",
            required_scopes=["scope1"],
            session_id="mcp-session",
        )


@pytest.mark.asyncio
async def test_initiate_auth_challenge_poll_invalid_client_falls_back_to_callback_in_auto_mode(monkeypatch):
    start_auth_flow_mock = AsyncMock(return_value="callback-auth-link")

    monkeypatch.setattr("auth.google_auth._get_auth_flow_mode", lambda: AUTH_FLOW_AUTO)
    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_DEVICE)
    monkeypatch.setattr(
        "auth.google_auth._resolve_oauth_client_selection",
        lambda *_args, **_kwargs: OAuthClientSelection(
            client_key="legacy-env",
            client_id="client-id",
            client_secret="client-secret",
            source="legacy_env",
            selection_mode="legacy",
            client_type=None,
        ),
    )
    monkeypatch.setattr(
        "auth.google_auth._poll_pending_device_auth_flow",
        AsyncMock(return_value=(None, "error:invalid_client:Invalid client type for device flow")),
    )
    monkeypatch.setattr(
        "auth.google_auth.resolve_oauth_redirect_uri_for_auth_flow",
        lambda **_: "http://localhost:9876/oauth2callback",
    )
    monkeypatch.setattr("auth.google_auth.start_auth_flow", start_auth_flow_mock)

    resolved_credentials, message = await initiate_auth_challenge(
        user_google_email="user@example.com",
        service_name="Google Drive",
        required_scopes=["scope1"],
        session_id="mcp-session",
    )

    assert resolved_credentials is None
    assert "Automatically falling back to callback flow" in message
    assert "callback-auth-link" in message
    start_auth_flow_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_initiate_auth_challenge_callback_mode_uses_start_auth_flow(monkeypatch):
    start_auth_flow_mock = AsyncMock(return_value="callback-auth-link")

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda *_, **__: AUTH_FLOW_CALLBACK)
    monkeypatch.setattr(
        "auth.google_auth._resolve_oauth_client_selection",
        lambda *_args, **_kwargs: OAuthClientSelection(
            client_key="legacy-env",
            client_id="client-id",
            client_secret="client-secret",
            source="legacy_env",
            selection_mode="legacy",
            client_type=None,
        ),
    )
    monkeypatch.setattr(
        "auth.google_auth.resolve_oauth_redirect_uri_for_auth_flow",
        lambda **_: "http://localhost:9876/oauth2callback",
    )
    monkeypatch.setattr("auth.google_auth.start_auth_flow", start_auth_flow_mock)

    resolved_credentials, message = await initiate_auth_challenge(
        user_google_email="user@example.com",
        service_name="Google Drive",
        required_scopes=["scope1"],
        session_id="mcp-session",
    )

    assert resolved_credentials is None
    assert message == "callback-auth-link"
    start_auth_flow_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_google_auth_manual_path_delegates_to_shared_challenge(monkeypatch):
    import core.server as core_server

    challenge_mock = AsyncMock(return_value=(None, "shared-auth-message"))

    monkeypatch.setattr(core_server, "check_client_secrets", lambda: None)
    monkeypatch.setattr(core_server, "get_current_scopes", lambda: {"scope.b", "scope.a"})
    monkeypatch.setattr(core_server, "get_credentials", lambda **_: None)
    monkeypatch.setattr(core_server, "initiate_auth_challenge", challenge_mock)

    start_google_auth = _tool_callable(core_server.start_google_auth)

    result = await start_google_auth(
        service_name="Google Drive",
        user_google_email="user@example.com",
    )

    assert result == "shared-auth-message"
    challenge_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_authenticated_google_service_auto_path_delegates_to_shared_challenge(monkeypatch):
    challenge_mock = AsyncMock(return_value=(None, "shared-auth-message"))

    monkeypatch.setattr("auth.google_auth.get_credentials", lambda **_: None)
    monkeypatch.setattr("auth.google_auth.initiate_auth_challenge", challenge_mock)

    with pytest.raises(GoogleAuthenticationError, match="shared-auth-message"):
        await get_authenticated_google_service(
            service_name="drive",
            version="v3",
            tool_name="test_tool",
            user_google_email="user@example.com",
            required_scopes=["scope.a"],
            session_id="mcp-session-123",
        )

    challenge_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_google_auth_prefers_callback_url(monkeypatch):
    import core.server as core_server

    callback_mock = AsyncMock(return_value=("user@example.com", object()))
    monkeypatch.setattr(core_server, "get_current_scopes", lambda: {"scope.a"})
    monkeypatch.setattr(core_server, "handle_auth_callback", callback_mock)

    complete_google_auth = _tool_callable(core_server.complete_google_auth)
    callback_url = "http://localhost:9876/oauth2callback?code=abc&state=xyz"
    result = await complete_google_auth(
        service_name="Google Drive",
        user_google_email="user@example.com",
        callback_url=callback_url,
    )

    assert "Authentication completed successfully" in result
    assert "user@example.com" in result
    assert callback_mock.await_args is not None
    assert callback_mock.await_args.kwargs["authorization_response"] == callback_url


@pytest.mark.asyncio
async def test_complete_google_auth_uses_persisted_redirect_uri_for_callback_url_state(monkeypatch):
    import core.server as core_server

    class _Store:
        def validate_oauth_state(self, state, session_id=None):
            assert state == "state-1"
            assert session_id is None
            return {
                "redirect_uri": "http://localhost:9877/oauth2callback",
                "oauth_client_key": "work",
                "expected_user_email": "user@example.com",
                "code_verifier": "persisted-verifier",
                "session_id": None,
            }

    callback_mock = AsyncMock(return_value=("user@example.com", object()))
    monkeypatch.setattr(core_server, "get_current_scopes", lambda: {"scope.a"})
    monkeypatch.setattr(core_server, "handle_auth_callback", callback_mock)
    monkeypatch.setattr(core_server, "get_oauth21_session_store", lambda: _Store())

    complete_google_auth = _tool_callable(core_server.complete_google_auth)
    callback_url = "http://localhost:9876/oauth2callback?code=abc&state=state-1"
    result = await complete_google_auth(
        service_name="Google Drive",
        user_google_email="user@example.com",
        callback_url=callback_url,
    )

    assert "Authentication completed successfully" in result
    assert callback_mock.await_args is not None
    assert callback_mock.await_args.kwargs["authorization_response"] == callback_url
    assert callback_mock.await_args.kwargs["redirect_uri"] == "http://localhost:9877/oauth2callback"


@pytest.mark.asyncio
async def test_complete_google_auth_supports_code_state_fallback(monkeypatch):
    import core.server as core_server

    class _Store:
        def validate_oauth_state(self, state, session_id=None):
            assert state == "state-1"
            assert session_id is None
            return {
                "redirect_uri": "http://localhost:9877/oauth2callback",
                "oauth_client_key": "work",
                "expected_user_email": "user@example.com",
                "code_verifier": "persisted-verifier",
                "session_id": None,
            }

    callback_mock = AsyncMock(return_value=("user@example.com", object()))
    monkeypatch.setattr(core_server, "get_current_scopes", lambda: {"scope.a"})
    monkeypatch.setattr(core_server, "handle_auth_callback", callback_mock)
    monkeypatch.setattr(core_server, "get_oauth21_session_store", lambda: _Store())

    complete_google_auth = _tool_callable(core_server.complete_google_auth)
    result = await complete_google_auth(
        service_name="Google Drive",
        user_google_email="user@example.com",
        authorization_code="4/abc",
        state="state-1",
    )

    assert "Authentication completed successfully" in result
    assert callback_mock.await_args is not None
    auth_response = callback_mock.await_args.kwargs["authorization_response"]
    assert auth_response.startswith("http://localhost:9877/oauth2callback?")
    assert "code=4%2Fabc" in auth_response
    assert "state=state-1" in auth_response
    assert callback_mock.await_args.kwargs["redirect_uri"] == "http://localhost:9877/oauth2callback"


@pytest.mark.asyncio
async def test_legacy_oauth2_callback_uses_persisted_redirect_uri(monkeypatch):
    import core.server as core_server

    callback_mock = AsyncMock(return_value=("user@example.com", _valid_credentials()))

    def store_session_mock(**kwargs):
        return None

    class _Store:
        def store_session(self, **kwargs):
            store_session_mock(**kwargs)

    request = SimpleNamespace(
        query_params={"state": "state-1", "code": "abc"},
        url="http://localhost:9876/oauth2callback?code=abc&state=state-1",
        state=SimpleNamespace(session_id="mcp-session-123"),
    )

    monkeypatch.setattr(core_server, "check_client_secrets", lambda: None)
    monkeypatch.setattr(core_server, "get_current_scopes", lambda: {"scope.a"})
    monkeypatch.setattr(core_server, "handle_auth_callback", callback_mock)
    monkeypatch.setattr(core_server, "get_oauth21_session_store", lambda: _Store())
    monkeypatch.setattr(
        core_server,
        "_get_persisted_redirect_uri_for_state",
        lambda state: "http://localhost:9877/oauth2callback",
    )

    response = await core_server.legacy_oauth2_callback(cast(Any, request))

    assert response.status_code == 200
    assert callback_mock.await_args is not None
    assert callback_mock.await_args.kwargs["authorization_response"] == str(request.url)
    assert callback_mock.await_args.kwargs["redirect_uri"] == "http://localhost:9877/oauth2callback"
    assert callback_mock.await_args.kwargs["session_id"] == "mcp-session-123"


@pytest.mark.asyncio
async def test_handle_auth_callback_rehydrates_flow_with_persisted_code_verifier(monkeypatch):
    from auth.google_auth import handle_auth_callback

    class _Store:
        def __init__(self):
            self.consumed_state = None
            self.stored_session = None

        def validate_oauth_state(self, state, session_id=None):
            assert state == "state-1"
            assert session_id is None
            return {
                "oauth_client_key": "work",
                "expected_user_email": "user@example.com",
                "redirect_uri": "http://localhost:9876/oauth2callback",
                "code_verifier": "persisted-verifier",
                "session_id": None,
            }

        def consume_oauth_state(self, state):
            self.consumed_state = state

        def store_session(self, **kwargs):
            self.stored_session = kwargs

    class _Flow:
        def __init__(self):
            self.fetch_kwargs = None
            self.credentials = _valid_credentials()

        def fetch_token(self, **kwargs):
            self.fetch_kwargs = kwargs

    store = _Store()
    flow = _Flow()
    captured = {}

    monkeypatch.setattr("auth.google_auth.get_oauth21_session_store", lambda: store)
    monkeypatch.setattr(
        "auth.google_auth._resolve_oauth_client_selection",
        lambda user_email, override_client_key=None: OAuthClientSelection(
            client_key=override_client_key or "work",
            client_id="client-id",
            client_secret="client-secret",
            source="test",
            selection_mode="mapped_only",
        ),
    )

    def _create_flow(**kwargs):
        captured.update(kwargs)
        return flow

    monkeypatch.setattr("auth.google_auth.create_oauth_flow", _create_flow)
    monkeypatch.setattr(
        "auth.google_auth.get_user_info",
        AsyncMock(return_value={"email": "user@example.com"}),
    )
    monkeypatch.setattr("auth.google_auth.is_stateless_mode", lambda: True)

    verified_user, credentials = await handle_auth_callback(
        scopes=["scope.a"],
        authorization_response="http://localhost:9876/oauth2callback?code=abc&state=state-1",
        redirect_uri="http://localhost:9876/oauth2callback",
        session_id=None,
    )

    assert verified_user == "user@example.com"
    assert credentials is flow.credentials
    assert captured["code_verifier"] == "persisted-verifier"
    assert flow.fetch_kwargs is not None
    assert flow.fetch_kwargs["authorization_response"].endswith("code=abc&state=state-1")
    assert store.consumed_state == "state-1"


@pytest.mark.asyncio
async def test_setup_google_auth_clients_reports_created(monkeypatch):
    import core.server as core_server

    monkeypatch.setattr(core_server, "ensure_auth_clients_config", lambda: ({"selection_mode": "mapped_only"}, True))
    monkeypatch.setattr(
        core_server,
        "get_auth_clients_config_path",
        lambda: "/tmp/auth_clients.json",
    )

    setup_google_auth_clients = _tool_callable(core_server.setup_google_auth_clients)
    result = await setup_google_auth_clients()

    assert "created" in result
    assert "/tmp/auth_clients.json" in result


@pytest.mark.asyncio
async def test_import_google_auth_client_reports_success(monkeypatch):
    import core.server as core_server

    monkeypatch.setattr(
        core_server,
        "import_oauth_client_config",
        lambda **_: {
            "client_key": "work",
            "mapped_script_ids": ["script-123"],
            "mapped_accounts": ["user@hellofresh.com"],
            "mapped_domains": ["hellofresh.com"],
            "config_path": "/tmp/auth_clients.json",
        },
    )

    import_google_auth_client = _tool_callable(core_server.import_google_auth_client)
    result = await import_google_auth_client(
        client_key="work",
        oauth_client_json_path="/tmp/work-client.json",
        mapped_script_ids=["script-123"],
        mapped_accounts=["user@hellofresh.com"],
        mapped_domains=["hellofresh.com"],
    )

    assert "Imported OAuth client 'work'" in result
    assert "/tmp/auth_clients.json" in result
