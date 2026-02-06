"""
Authentication middleware to populate context state with user information
"""

import logging
import os
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING

import jwt
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from auth.oauth21_session_store import ensure_session_from_access_token

if TYPE_CHECKING:
    from fastmcp import Context

logger = logging.getLogger(__name__)


def _get_context(context: MiddlewareContext) -> "Context":
    """Get the fastmcp_context, raising if None."""
    if context.fastmcp_context is None:
        raise RuntimeError("fastmcp_context is None")
    return context.fastmcp_context


class AuthInfoMiddleware(Middleware):
    """Middleware to extract authentication information and populate FastMCP context state."""

    def __init__(self):
        super().__init__()
        self.auth_provider_type = "GoogleProvider"

    def _create_unverified_token(self, token_str: str) -> SimpleNamespace:
        """Create an unverified token object for storage."""
        return SimpleNamespace(
            token=token_str,
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID", "google"),
            scopes=[],
            session_id=f"google_oauth_{token_str[:8]}",
            expires_at=int(time.time()) + 3600,
            sub="unknown",
            email="",
        )

    def _store_unverified_token(self, context: MiddlewareContext, token_str: str) -> None:
        """Store an unverified token in context."""
        ctx = _get_context(context)
        access_token = self._create_unverified_token(token_str)
        ctx.set_state("access_token", access_token)
        ctx.set_state("auth_provider_type", self.auth_provider_type)
        ctx.set_state("token_type", "google_oauth")

    def _process_verified_google_auth(self, context: MiddlewareContext, verified_auth, token_str: str) -> bool:
        """Process a verified Google OAuth token and store in context."""
        ctx = _get_context(context)
        user_email = None
        if hasattr(verified_auth, "claims"):
            user_email = verified_auth.claims.get("email")

        expires_at = getattr(verified_auth, "expires_at", int(time.time()) + 3600)
        client_id = getattr(verified_auth, "client_id", None) or "google"

        access_token = SimpleNamespace(
            token=token_str,
            client_id=client_id,
            scopes=verified_auth.scopes if hasattr(verified_auth, "scopes") else [],
            session_id=f"google_oauth_{token_str[:8]}",
            expires_at=expires_at,
            sub=verified_auth.sub if hasattr(verified_auth, "sub") else user_email,
            email=user_email,
        )

        ctx.set_state("access_token", access_token)
        mcp_session_id = getattr(ctx, "session_id", None)
        ensure_session_from_access_token(verified_auth, user_email, mcp_session_id)
        ctx.set_state("access_token_obj", verified_auth)
        ctx.set_state("auth_provider_type", self.auth_provider_type)
        ctx.set_state("token_type", "google_oauth")
        ctx.set_state("user_email", user_email)
        ctx.set_state("username", user_email)
        ctx.set_state("authenticated_user_email", user_email)
        ctx.set_state("authenticated_via", "bearer_token")

        logger.info(f"Authenticated via Google OAuth: {user_email}")
        return True

    async def _handle_google_oauth_token(self, context: MiddlewareContext, token_str: str) -> bool:
        """Handle Google OAuth access token (ya29.* format)."""
        from core.server import get_auth_provider

        auth_provider = get_auth_provider()
        if not auth_provider:
            logger.warning("No auth provider available to verify Google token")
            self._store_unverified_token(context, token_str)
            return False

        try:
            verified_auth = await auth_provider.verify_token(token_str)
            if not verified_auth:
                logger.error("Failed to verify Google OAuth token")
                return False
            return self._process_verified_google_auth(context, verified_auth, token_str)
        except Exception as e:
            logger.error(f"Error verifying Google OAuth token: {e}")
            self._store_unverified_token(context, token_str)
            return False

    def _handle_jwt_token(self, context: MiddlewareContext, token_str: str) -> bool:
        """Handle JWT token authentication."""
        ctx = _get_context(context)
        try:
            token_payload = jwt.decode(token_str, options={"verify_signature": False})
            logger.debug(f"JWT payload decoded: {list(token_payload.keys())}")

            access_token = SimpleNamespace(
                token=token_str,
                client_id=token_payload.get("client_id", "unknown"),
                scopes=token_payload.get("scope", "").split() if token_payload.get("scope") else [],
                session_id=token_payload.get("sid", token_payload.get("jti", "unknown")),
                expires_at=token_payload.get("exp", 0),
            )

            ctx.set_state("access_token", access_token)
            ctx.set_state("user_id", token_payload.get("sub"))
            ctx.set_state("username", token_payload.get("username", token_payload.get("email")))
            ctx.set_state("name", token_payload.get("name"))
            ctx.set_state("auth_time", token_payload.get("auth_time"))
            ctx.set_state("issuer", token_payload.get("iss"))
            ctx.set_state("audience", token_payload.get("aud"))
            ctx.set_state("jti", token_payload.get("jti"))
            ctx.set_state("auth_provider_type", self.auth_provider_type)

            user_email = token_payload.get("email", token_payload.get("username"))
            if user_email:
                ctx.set_state("authenticated_user_email", user_email)
                ctx.set_state("authenticated_via", "jwt_token")
                return True
            return False

        except jwt.DecodeError as e:
            logger.error(f"Failed to decode JWT: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing JWT: {e}")
            return False

    async def _try_bearer_token_auth(self, context: MiddlewareContext) -> bool:
        """Attempt authentication via Bearer token in Authorization header."""
        try:
            headers = get_http_headers()
            if not headers:
                logger.debug("No HTTP headers available (might be using stdio transport)")
                return False

            auth_header = headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                logger.debug("No Bearer token in Authorization header")
                return False

            token_str = auth_header[7:]
            logger.debug("Found Bearer token")

            if token_str.startswith("ya29."):
                return await self._handle_google_oauth_token(context, token_str)
            else:
                return self._handle_jwt_token(context, token_str)

        except Exception as e:
            logger.debug(f"Could not get HTTP request: {e}")
            return False

    async def _try_stdio_session_auth(self, context: MiddlewareContext) -> bool:
        """Attempt authentication via stdio session (single-user mode)."""
        from auth.config import get_transport_mode

        if get_transport_mode() != "stdio":
            return False

        logger.debug("Checking for stdio mode authentication")

        requested_user = None
        if hasattr(context, "request") and hasattr(context.request, "params"):
            requested_user = context.request.params.get("user_google_email")
        elif hasattr(context, "arguments"):
            requested_user = context.arguments.get("user_google_email")

        ctx = _get_context(context)
        if requested_user:
            try:
                from auth.oauth21_session_store import get_oauth21_session_store

                store = get_oauth21_session_store()
                if store.has_session(requested_user):
                    logger.debug(f"Using recent stdio session for {requested_user}")
                    ctx.set_state("authenticated_user_email", requested_user)
                    ctx.set_state("authenticated_via", "stdio_session")
                    ctx.set_state("auth_provider_type", "oauth21_stdio")
                    return True
            except Exception as e:
                logger.debug(f"Error checking stdio session: {e}")

        try:
            from auth.oauth21_session_store import get_oauth21_session_store

            store = get_oauth21_session_store()
            single_user = store.get_single_user_email()
            if single_user:
                logger.debug(f"Defaulting to single stdio OAuth session for {single_user}")
                ctx.set_state("authenticated_user_email", single_user)
                ctx.set_state("authenticated_via", "stdio_single_session")
                ctx.set_state("auth_provider_type", "oauth21_stdio")
                ctx.set_state("user_email", single_user)
                ctx.set_state("username", single_user)
                return True
        except Exception as e:
            logger.debug(f"Error determining stdio single-user session: {e}")

        return False

    async def _try_mcp_session_binding(self, context: MiddlewareContext) -> bool:
        """Attempt authentication via MCP session binding."""
        ctx = _get_context(context)
        if not hasattr(ctx, "session_id"):
            return False

        mcp_session_id = ctx.session_id
        if not mcp_session_id:
            return False

        try:
            from auth.oauth21_session_store import get_oauth21_session_store

            store = get_oauth21_session_store()
            bound_user = store.get_user_by_mcp_session(mcp_session_id)
            if bound_user:
                logger.debug(f"MCP session bound to {bound_user}")
                ctx.set_state("authenticated_user_email", bound_user)
                ctx.set_state("authenticated_via", "mcp_session_binding")
                ctx.set_state("auth_provider_type", "oauth21_session")
                return True
        except Exception as e:
            logger.debug(f"Error checking MCP session binding: {e}")

        return False

    async def _process_request_for_auth(self, context: MiddlewareContext) -> None:
        """Extract, verify, and store auth info from a request."""
        if not context.fastmcp_context:
            logger.warning("No fastmcp_context available")
            return

        ctx = _get_context(context)
        if ctx.get_state("authenticated_user_email"):
            logger.debug("Authentication state already set")
            return

        if await self._try_bearer_token_auth(context):
            return

        logger.debug("No authentication found via bearer token, checking other methods")

        if await self._try_stdio_session_auth(context):
            return

        await self._try_mcp_session_binding(context)

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Extract auth info from token and set in context state"""
        logger.debug("Processing tool call authentication")

        try:
            await self._process_request_for_auth(context)

            logger.debug("Passing to next handler")
            result = await call_next(context)
            logger.debug("Handler completed")
            return result

        except Exception as e:
            if "GoogleAuthenticationError" in str(type(e)) or "Access denied: Cannot retrieve credentials" in str(e):
                logger.info(f"Authentication check failed: {e}")
            else:
                logger.error(f"Error in on_call_tool middleware: {e}", exc_info=True)
            raise

    async def on_get_prompt(self, context: MiddlewareContext, call_next):
        """Extract auth info for prompt requests too"""
        logger.debug("Processing prompt authentication")

        try:
            await self._process_request_for_auth(context)

            logger.debug("Passing prompt to next handler")
            result = await call_next(context)
            logger.debug("Prompt handler completed")
            return result

        except Exception as e:
            if "GoogleAuthenticationError" in str(type(e)) or "Access denied: Cannot retrieve credentials" in str(e):
                logger.info(f"Authentication check failed in prompt: {e}")
            else:
                logger.error(f"Error in on_get_prompt middleware: {e}", exc_info=True)
            raise
