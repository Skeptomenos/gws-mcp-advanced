"""Tests for unverified JWT identity guardrails."""

from types import SimpleNamespace

import jwt
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from auth.middleware.auth_info import AuthInfoMiddleware
from auth.middleware.session import MCPSessionMiddleware
from auth.oauth21_session_store import get_session_context


class _DummyFastMCPContext:
    """Minimal FastMCP context test double."""

    def __init__(self) -> None:
        self._state: dict[str, object] = {}

    def set_state(self, key: str, value: object) -> None:
        self._state[key] = value

    def get_state(self, key: str) -> object | None:
        return self._state.get(key)


def _build_middleware_context() -> object:
    """Create a minimal middleware context object for unit tests."""
    return SimpleNamespace(fastmcp_context=_DummyFastMCPContext())


def _make_jwt(email: str = "attacker@example.com") -> str:
    """Create a signed JWT used as a test token payload carrier."""
    return jwt.encode(
        {
            "sub": "user-123",
            "email": email,
            "username": email,
            "client_id": "test-client",
        },
        "test-secret-with-minimum-32-byte-length",
        algorithm="HS256",
    )


def test_auth_info_rejects_unverified_jwt_by_default(monkeypatch):
    """Unverified JWT identity must be rejected unless override is enabled."""
    monkeypatch.delenv("WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT", raising=False)
    middleware = AuthInfoMiddleware()
    context = _build_middleware_context()

    accepted = middleware._handle_jwt_token(context, _make_jwt())  # noqa: SLF001 - private method tested by design

    assert accepted is False
    assert context.fastmcp_context.get_state("authenticated_user_email") is None


def test_auth_info_accepts_unverified_jwt_when_override_enabled(monkeypatch):
    """Break-glass override should allow legacy unverified JWT identity extraction."""
    monkeypatch.setenv("WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT", "true")
    middleware = AuthInfoMiddleware()
    context = _build_middleware_context()
    email = "legacy@example.com"

    accepted = middleware._handle_jwt_token(  # noqa: SLF001 - private method tested by design
        context, _make_jwt(email=email)
    )

    assert accepted is True
    assert context.fastmcp_context.get_state("authenticated_user_email") == email
    assert context.fastmcp_context.get_state("authenticated_via") == "jwt_token_unverified"


def test_session_middleware_ignores_unverified_jwt_identity_by_default(monkeypatch):
    """Session middleware should not derive user identity from unverified JWT by default."""
    monkeypatch.delenv("WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT", raising=False)

    async def endpoint(_request):
        session = get_session_context()
        return JSONResponse({"user_id": session.user_id if session else None})

    app = Starlette(routes=[Route("/mcp/test", endpoint)])
    app.add_middleware(MCPSessionMiddleware)

    with TestClient(app) as client:
        response = client.get("/mcp/test", headers={"Authorization": f"Bearer {_make_jwt()}"})

    assert response.status_code == 200
    assert response.json()["user_id"] is None


def test_session_middleware_allows_unverified_jwt_identity_when_override_enabled(monkeypatch):
    """Session middleware should support legacy identity extraction only under explicit override."""
    monkeypatch.setenv("WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT", "true")

    async def endpoint(_request):
        session = get_session_context()
        return JSONResponse({"user_id": session.user_id if session else None})

    app = Starlette(routes=[Route("/mcp/test", endpoint)])
    app.add_middleware(MCPSessionMiddleware)
    email = "legacy-session@example.com"

    with TestClient(app) as client:
        response = client.get("/mcp/test", headers={"Authorization": f"Bearer {_make_jwt(email=email)}"})

    assert response.status_code == 200
    assert response.json()["user_id"] == email


def test_auth_info_preserves_verified_google_oauth_identity_path(monkeypatch):
    """Verified Google OAuth tokens should continue to populate identity state."""
    monkeypatch.delenv("WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT", raising=False)
    middleware = AuthInfoMiddleware()
    context = _build_middleware_context()

    verified_auth = SimpleNamespace(
        claims={"email": "verified@example.com"},
        scopes=["scope-1"],
        sub="verified-sub",
        expires_at=2_000_000_000,
    )

    monkeypatch.setattr("auth.middleware.auth_info.ensure_session_from_access_token", lambda *_args, **_kwargs: None)

    accepted = middleware._process_verified_google_auth(  # noqa: SLF001 - private method tested by design
        context=context,
        verified_auth=verified_auth,
        token_str="ya29.verified_token",
    )

    assert accepted is True
    assert context.fastmcp_context.get_state("authenticated_user_email") == "verified@example.com"
    assert context.fastmcp_context.get_state("authenticated_via") == "bearer_token"
