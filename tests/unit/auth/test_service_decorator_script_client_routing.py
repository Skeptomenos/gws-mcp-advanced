"""Unit tests for script-aware OAuth client routing in service decorator."""

from __future__ import annotations

import inspect

import pytest

from auth.oauth_clients import OAuthClientSelection
from auth.service_decorator import _resolve_script_client_override
from core.errors import AuthenticationError, GoogleAuthenticationError


def _wrapper_signature() -> inspect.Signature:
    def _tool(script_id: str | None = None, user_google_email: str | None = None) -> None:
        return None

    return inspect.signature(_tool)


def test_resolve_script_client_override_returns_none_for_non_appscript():
    override = _resolve_script_client_override(
        user_google_email="user@example.com",
        service_type="drive",
        args=(),
        kwargs={"script_id": "script-123"},
        wrapper_sig=_wrapper_signature(),
    )

    assert override is None


def test_resolve_script_client_override_returns_none_without_script_id():
    override = _resolve_script_client_override(
        user_google_email="user@example.com",
        service_type="appscript",
        args=(),
        kwargs={},
        wrapper_sig=_wrapper_signature(),
    )

    assert override is None


def test_resolve_script_client_override_uses_script_id_mapping(monkeypatch):
    seen: dict[str, str | None] = {}

    def _resolver(user_google_email: str, *, override_client_key: str | None = None, script_id: str | None = None):
        seen["user_google_email"] = user_google_email
        seen["script_id"] = script_id
        return OAuthClientSelection(
            client_key="script-client",
            client_id="id",
            client_secret="secret",
            source="script_map",
            selection_mode="mapped_only",
        )

    monkeypatch.setattr("auth.service_decorator.resolve_oauth_client_for_user", _resolver)

    override = _resolve_script_client_override(
        user_google_email="user@example.com",
        service_type="appscript",
        args=(),
        kwargs={"script_id": "script-123"},
        wrapper_sig=_wrapper_signature(),
    )

    assert override == "script-client"
    assert seen == {"user_google_email": "user@example.com", "script_id": "script-123"}


def test_resolve_script_client_override_wraps_resolution_errors(monkeypatch):
    def _resolver(user_google_email: str, *, override_client_key: str | None = None, script_id: str | None = None):
        raise AuthenticationError("missing mapping")

    monkeypatch.setattr("auth.service_decorator.resolve_oauth_client_for_user", _resolver)

    with pytest.raises(GoogleAuthenticationError, match="OAuth client resolution failed for script"):
        _resolve_script_client_override(
            user_google_email="user@example.com",
            service_type="appscript",
            args=(),
            kwargs={"script_id": "script-123"},
            wrapper_sig=_wrapper_signature(),
        )
