"""Unit tests for auth flow mode selection and challenge orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from google.oauth2.credentials import Credentials

from auth.google_auth import (
    AUTH_FLOW_AUTO,
    AUTH_FLOW_CALLBACK,
    AUTH_FLOW_DEVICE,
    _get_effective_auth_flow_mode,
    _start_or_resume_device_auth_flow,
    initiate_auth_challenge,
)
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


def test_start_or_resume_device_auth_reuses_pending_flow(monkeypatch):
    class _Store:
        def get_pending_device_flow(self, user_email: str):
            assert user_email == "user@example.com"
            return {
                "user_code": "ABCD-EFGH",
                "verification_url": "https://www.google.com/device",
                "verification_url_complete": "https://www.google.com/device?user_code=ABCD-EFGH",
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            }

    monkeypatch.setattr("auth.google_auth.get_oauth21_session_store", lambda: _Store())

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

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda: AUTH_FLOW_DEVICE)
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

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda: AUTH_FLOW_DEVICE)
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

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda: AUTH_FLOW_DEVICE)
    monkeypatch.setattr("auth.google_auth._poll_pending_device_auth_flow", poll_mock)

    with pytest.raises(GoogleAuthenticationError, match="Device authorization polling failed"):
        await initiate_auth_challenge(
            user_google_email="user@example.com",
            service_name="Google Drive",
            required_scopes=["scope1"],
            session_id="mcp-session",
        )


@pytest.mark.asyncio
async def test_initiate_auth_challenge_callback_mode_uses_start_auth_flow(monkeypatch):
    start_auth_flow_mock = AsyncMock(return_value="callback-auth-link")

    monkeypatch.setattr("auth.google_auth._get_effective_auth_flow_mode", lambda: AUTH_FLOW_CALLBACK)
    monkeypatch.setattr(
        "auth.google_auth.resolve_oauth_redirect_uri_for_auth_flow",
        lambda: "http://localhost:9876/oauth2callback",
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
