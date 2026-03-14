"""Unit tests for deterministic OAuth callback server policy."""

from __future__ import annotations


def test_running_callback_server_must_match_allowed_redirect_uri():
    from auth.oauth_callback_server import _validate_running_server_reuse

    success, error = _validate_running_server_reuse(
        running_redirect_uri="http://localhost:9876/oauth2callback",
        allowed_redirect_uris=["http://localhost:9877/oauth2callback"],
    )

    assert success is False
    assert "another local callback auth challenge is active" in error.lower()


def test_running_callback_server_reuse_allows_identical_redirect_uri():
    from auth.oauth_callback_server import _validate_running_server_reuse

    success, error = _validate_running_server_reuse(
        running_redirect_uri="http://localhost:9876/oauth2callback",
        allowed_redirect_uris=["http://localhost:9876/oauth2callback"],
    )

    assert success is True
    assert error == ""


def test_callback_port_resolution_fails_when_registered_ports_occupied_and_fallback_disabled():
    from auth.oauth_callback_server import _resolve_callback_bind_port

    port, error = _resolve_callback_bind_port(
        preferred_ports=[9876],
        allow_sequential_fallback=False,
        is_port_available=lambda _port: False,
        find_fallback_port=lambda: 9880,
    )

    assert port is None
    assert "registered oauth callback ports" in error.lower()


def test_callback_port_resolution_uses_second_registered_port_before_fallback():
    from auth.oauth_callback_server import _resolve_callback_bind_port

    observed: list[int] = []

    def _is_port_available(port: int) -> bool:
        observed.append(port)
        return port == 9877

    port, error = _resolve_callback_bind_port(
        preferred_ports=[9876, 9877],
        allow_sequential_fallback=False,
        is_port_available=_is_port_available,
        find_fallback_port=lambda: 9880,
    )

    assert port == 9877
    assert error == ""
    assert observed == [9876, 9877]


def test_callback_port_resolution_allows_sequential_fallback_when_enabled():
    from auth.oauth_callback_server import _resolve_callback_bind_port

    port, error = _resolve_callback_bind_port(
        preferred_ports=[9876],
        allow_sequential_fallback=True,
        is_port_available=lambda _port: False,
        find_fallback_port=lambda: 9888,
    )

    assert port == 9888
    assert error == ""


def test_start_oauth_callback_server_fails_closed_for_incompatible_running_server(monkeypatch):
    import auth.oauth_callback_server as callback_server

    callback_server._minimal_oauth_server = type(
        "RunningServer",
        (),
        {"is_running": True, "redirect_uri": "http://localhost:9876/oauth2callback"},
    )()

    monkeypatch.setattr(
        callback_server,
        "_validate_running_server_reuse",
        lambda running_redirect_uri, allowed_redirect_uris: (
            False,
            "another local callback auth challenge is active on http://localhost:9876/oauth2callback",
        ),
    )

    success, error, redirect_uri = callback_server.start_oauth_callback_server(
        preferred_ports=[9877],
        allow_sequential_fallback=False,
    )

    assert success is False
    assert "another local callback auth challenge is active" in error.lower()
    assert redirect_uri is None

    callback_server._minimal_oauth_server = None


def test_start_oauth_callback_server_reuses_running_server_when_allowed(monkeypatch):
    import auth.oauth_callback_server as callback_server

    callback_server._minimal_oauth_server = type(
        "RunningServer",
        (),
        {"is_running": True, "redirect_uri": "http://localhost:9876/oauth2callback"},
    )()

    monkeypatch.setattr(
        callback_server,
        "_validate_running_server_reuse",
        lambda running_redirect_uri, allowed_redirect_uris: (True, ""),
    )

    success, error, redirect_uri = callback_server.start_oauth_callback_server(
        preferred_ports=[9876],
        allow_sequential_fallback=False,
    )

    assert success is True
    assert error == ""
    assert redirect_uri == "http://localhost:9876/oauth2callback"

    callback_server._minimal_oauth_server = None
