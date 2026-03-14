"""
Transport-aware OAuth callback handling.

In streamable-http mode: Uses the existing FastAPI server
In stdio mode: Starts a minimal HTTP server just for OAuth callbacks

Port selection strategy:
1. If the OAuth client JSON declares redirect_uris with a localhost port,
   that port is used first (so it matches Google Cloud Console registration).
2. Otherwise, tries ports sequentially starting from 9876.
3. Falls back to the next port only when the preferred port is occupied.
"""

import asyncio
import logging
import socket
import threading
import time
from collections.abc import Callable
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from auth.google_auth import check_client_secrets, handle_auth_callback
from auth.oauth_responses import (
    create_error_response,
    create_server_error_response,
    create_success_response,
)
from auth.scopes import SCOPES, get_current_scopes  # noqa

logger = logging.getLogger(__name__)

PORT_RANGE_START = 9876
PORT_RANGE_END = 9899


def _build_redirect_uri(base_uri: str, port: int) -> str:
    return f"{base_uri}:{port}/oauth2callback"


def _is_port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("localhost", port))
        return True
    except OSError:
        return False


def _validate_running_server_reuse(
    running_redirect_uri: str,
    allowed_redirect_uris: list[str] | None,
) -> tuple[bool, str]:
    """Validate whether an already-running callback server may be reused."""
    if not allowed_redirect_uris:
        return True, ""

    if running_redirect_uri in allowed_redirect_uris:
        return True, ""

    return (
        False,
        "Another local callback auth challenge is active on "
        f"{running_redirect_uri}. Finish that auth flow before starting a callback flow for a "
        "different registered redirect URI.",
    )


def _resolve_callback_bind_port(
    preferred_ports: list[int] | None,
    allow_sequential_fallback: bool,
    *,
    is_port_available: Callable[[int], bool] | None = None,
    find_fallback_port: Callable[[], int | None] | None = None,
) -> tuple[int | None, str]:
    """Resolve which local callback port should be bound."""
    port_checker = is_port_available or _is_port_available
    fallback_finder = find_fallback_port or find_available_port

    for candidate in preferred_ports or []:
        if port_checker(candidate):
            return candidate, ""

    if preferred_ports and not allow_sequential_fallback:
        return (
            None,
            "All registered OAuth callback ports "
            f"{preferred_ports} are occupied. Another local callback auth challenge is active or the "
            "registered redirect_uris are already in use.",
        )

    if preferred_ports:
        logger.warning(
            "All preferred OAuth callback ports %s are occupied; falling back to sequential allocation",
            preferred_ports,
        )

    fallback_port = fallback_finder() if allow_sequential_fallback else None
    if fallback_port is None:
        return None, f"No available port in range {PORT_RANGE_START}-{PORT_RANGE_END}"

    return fallback_port, ""


def find_available_port(start: int = PORT_RANGE_START, end: int = PORT_RANGE_END) -> int | None:
    """Find an available port in the given range using sequential order.

    Tries ports starting from `start` (default 9876) so the redirect URI is
    deterministic across installations. Only falls back to subsequent ports
    when the preferred port is genuinely occupied by another process.
    """
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("localhost", port))
                return port
        except OSError:
            continue

    return None


class MinimalOAuthServer:
    """
    Minimal HTTP server for OAuth callbacks in stdio mode.
    Only starts when needed and uses dynamic port allocation.
    """

    def __init__(self, port: int, base_uri: str = "http://localhost"):
        self.port = port
        self.base_uri = base_uri
        self.redirect_uri = _build_redirect_uri(base_uri, port)
        self.app = FastAPI()
        self.server: uvicorn.Server | None = None
        self.server_thread: threading.Thread | None = None
        self.is_running = False
        self._auth_completed = False

        self._setup_callback_route()
        self._setup_attachment_route()

    def _setup_callback_route(self):
        server_instance = self

        @self.app.get("/oauth2callback")
        async def oauth_callback(request: Request):
            state = request.query_params.get("state")
            code = request.query_params.get("code")
            error = request.query_params.get("error")

            if error:
                error_message = f"Authentication failed: Google returned an error: {error}. State: {state}."
                logger.error(error_message)
                return create_error_response(error_message)

            if not code:
                error_message = "Authentication failed: No authorization code received from Google."
                logger.error(error_message)
                return create_error_response(error_message)

            try:
                secrets_error = check_client_secrets()
                if secrets_error:
                    return create_server_error_response(secrets_error)

                logger.info(f"OAuth callback: Received code (state: {state}). Attempting to exchange for tokens.")

                verified_user_id, credentials = await handle_auth_callback(
                    scopes=get_current_scopes(),
                    authorization_response=str(request.url),
                    redirect_uri=server_instance.redirect_uri,
                    session_id=None,
                )

                logger.info(f"OAuth callback: Successfully authenticated user: {verified_user_id} (state: {state}).")

                server_instance._auth_completed = True
                asyncio.get_event_loop().call_later(2.0, server_instance.stop)

                return create_success_response(verified_user_id)

            except Exception as e:
                error_message_detail = f"Error processing OAuth callback (state: {state}): {str(e)}"
                logger.error(error_message_detail, exc_info=True)
                return create_server_error_response(str(e))

    def _setup_attachment_route(self):
        """Setup the attachment serving route."""
        from core.attachment_storage import get_attachment_storage

        @self.app.get("/attachments/{file_id}")
        async def serve_attachment(file_id: str, request: Request):
            """Serve a stored attachment file."""
            storage = get_attachment_storage()
            metadata = storage.get_attachment_metadata(file_id)

            if not metadata:
                return JSONResponse({"error": "Attachment not found or expired"}, status_code=404)

            file_path = storage.get_attachment_path(file_id)
            if not file_path:
                return JSONResponse({"error": "Attachment file not found"}, status_code=404)

            return FileResponse(
                path=str(file_path),
                filename=metadata["filename"],
                media_type=metadata["mime_type"],
            )

    def start(self) -> tuple[bool, str]:
        """
        Start the minimal OAuth server.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if self.is_running:
            logger.info("Minimal OAuth server is already running")
            return True, ""

        # Check if port is available
        # Extract hostname from base_uri (e.g., "http://localhost" -> "localhost")
        try:
            parsed_uri = urlparse(self.base_uri)
            hostname = parsed_uri.hostname or "localhost"
        except Exception:
            hostname = "localhost"

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((hostname, self.port))
        except OSError:
            error_msg = f"Port {self.port} is already in use on {hostname}. Cannot start minimal OAuth server."
            logger.error(error_msg)
            return False, error_msg

        def run_server():
            """Run the server in a separate thread."""
            try:
                config = uvicorn.Config(
                    self.app,
                    host=hostname,
                    port=self.port,
                    log_level="warning",
                    access_log=False,
                )
                self.server = uvicorn.Server(config)
                asyncio.run(self.server.serve())

            except Exception as e:
                logger.error(f"Minimal OAuth server error: {e}", exc_info=True)
                self.is_running = False

        # Start server in background thread
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        max_wait = 3.0
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex((hostname, self.port))
                    if result == 0:
                        self.is_running = True
                        logger.info(f"Minimal OAuth server started on {hostname}:{self.port}")
                        return True, ""
            except Exception:
                pass
            time.sleep(0.1)

        error_msg = f"Failed to start minimal OAuth server on {hostname}:{self.port} - server did not respond within {max_wait}s"
        logger.error(error_msg)
        return False, error_msg

    def stop(self):
        """Stop the minimal OAuth server."""
        if not self.is_running:
            return

        try:
            if self.server:
                if hasattr(self.server, "should_exit"):
                    self.server.should_exit = True

            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=3.0)

            self.is_running = False
            logger.info("Minimal OAuth server stopped")

        except Exception as e:
            logger.error(f"Error stopping minimal OAuth server: {e}", exc_info=True)


_minimal_oauth_server: MinimalOAuthServer | None = None


def start_oauth_callback_server(
    base_uri: str = "http://localhost",
    preferred_ports: list[int] | None = None,
    allow_sequential_fallback: bool = True,
) -> tuple[bool, str, str | None]:
    """
    Start OAuth callback server, preferring ports declared in the OAuth client's redirect_uris.

    Args:
        base_uri: Base URI scheme + host (default http://localhost).
        preferred_ports: Ports extracted from the OAuth client's registered redirect_uris.
            Each port is tried in order so the callback URL matches one of the URIs
            registered in Google Cloud Console.  Falls back to sequential allocation
            only when every preferred port is occupied.
        allow_sequential_fallback: Whether sequential localhost fallback remains
            allowed after preferred ports are exhausted.

    Returns:
        Tuple of (success, error_message, redirect_uri)
    """
    global _minimal_oauth_server

    allowed_redirect_uris = [_build_redirect_uri(base_uri, port) for port in preferred_ports or []] or None

    if _minimal_oauth_server is not None and _minimal_oauth_server.is_running:
        can_reuse, reuse_error = _validate_running_server_reuse(
            running_redirect_uri=_minimal_oauth_server.redirect_uri,
            allowed_redirect_uris=allowed_redirect_uris,
        )
        if can_reuse:
            return True, "", _minimal_oauth_server.redirect_uri
        return False, reuse_error, None

    port, error_msg = _resolve_callback_bind_port(
        preferred_ports=preferred_ports,
        allow_sequential_fallback=allow_sequential_fallback,
        is_port_available=_is_port_available,
        find_fallback_port=find_available_port,
    )
    if port is None:
        return False, error_msg, None

    if preferred_ports and port in preferred_ports:
        logger.info("Using preferred OAuth callback port %d (from client redirect_uris)", port)

    logger.info(f"Starting OAuth callback server on {base_uri}:{port}")
    _minimal_oauth_server = MinimalOAuthServer(port, base_uri)

    success, error_msg = _minimal_oauth_server.start()
    if success:
        return True, "", _minimal_oauth_server.redirect_uri
    return False, error_msg, None


def get_active_oauth_redirect_uri() -> str | None:
    """Get the redirect URI of the currently running OAuth server."""
    if _minimal_oauth_server is not None and _minimal_oauth_server.is_running:
        return _minimal_oauth_server.redirect_uri
    return None


def ensure_oauth_callback_available(
    transport_mode: str = "stdio", port: int = 9876, base_uri: str = "http://localhost"
) -> tuple[bool, str]:
    """
    DEPRECATED: Use start_oauth_callback_server() for dynamic port allocation.
    """
    global _minimal_oauth_server

    if transport_mode == "streamable-http":
        logger.debug("Using existing FastAPI server for OAuth callbacks (streamable-http mode)")
        return True, ""

    elif transport_mode == "stdio":
        if _minimal_oauth_server is not None and _minimal_oauth_server.is_running:
            logger.info("Minimal OAuth server is already running")
            return True, ""

        success, error_msg, _ = start_oauth_callback_server(base_uri)
        return success, error_msg

    else:
        error_msg = f"Unknown transport mode: {transport_mode}"
        logger.error(error_msg)
        return False, error_msg


def cleanup_oauth_callback_server():
    """Clean up the minimal OAuth server if it was started."""
    global _minimal_oauth_server
    if _minimal_oauth_server:
        _minimal_oauth_server.stop()
        _minimal_oauth_server = None
