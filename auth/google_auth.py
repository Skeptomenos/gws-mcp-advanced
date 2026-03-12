# auth/google_auth.py

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import jwt
import requests
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.config import (
    GOOGLE_WORKSPACE_MCP_APP_NAME,
    get_credentials_directory,
    get_google_oauth_config,
    get_transport_mode,
    is_stateless_mode,
)
from auth.config import (
    get_oauth_redirect_uri as get_oauth_redirect_uri_for_current_mode,
)
from auth.credential_store import get_credential_store
from auth.oauth21_session_store import get_oauth21_session_store
from auth.oauth_clients import OAuthClientSelection, ensure_auth_clients_config, resolve_oauth_client_for_user
from auth.scopes import SCOPES, get_current_scopes  # noqa
from core.errors import AuthenticationError, GoogleAuthenticationError

# Try to import FastMCP dependencies (may not be available in all environments)
try:
    from fastmcp.server.dependencies import get_context as get_fastmcp_context
except ImportError:
    get_fastmcp_context = None  # type: ignore[assignment]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Application name for Google Auth flows
APP_NAME = GOOGLE_WORKSPACE_MCP_APP_NAME


# Constants
def get_default_credentials_dir():
    """Get the default credentials directory path for Google Workspace MCP."""
    # Check for explicit environment variable override
    override_dir = os.getenv("GOOGLE_MCP_CREDENTIALS_DIR")
    if override_dir:
        return override_dir

    # Use default config directory
    return os.path.join(get_credentials_directory(), "credentials")


DEFAULT_CREDENTIALS_DIR = get_default_credentials_dir()

# Centralized Client Secrets Path Logic
_client_secrets_env = os.getenv("GOOGLE_CLIENT_SECRET_PATH") or os.getenv("GOOGLE_CLIENT_SECRETS")
if _client_secrets_env:
    CONFIG_CLIENT_SECRETS_PATH = _client_secrets_env
else:
    # Assumes this file is in auth/ and client_secret.json is in the root
    CONFIG_CLIENT_SECRETS_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "client_secret.json",
    )

# --- Helper Functions ---

DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
DEVICE_AUTH_ENDPOINT = "https://oauth2.googleapis.com/device/code"
DEVICE_TOKEN_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
AUTH_FLOW_MODE_ENV = "WORKSPACE_MCP_AUTH_FLOW"
AUTH_FLOW_AUTO = "auto"
AUTH_FLOW_CALLBACK = "callback"
AUTH_FLOW_DEVICE = "device"


def _token_uri_or_default(credentials: Credentials) -> str:
    token_uri = getattr(credentials, "token_uri", None)
    return token_uri or DEFAULT_TOKEN_URI


def _credential_scopes(credentials: Credentials) -> list[str]:
    raw_scopes = credentials.scopes
    return list(raw_scopes) if raw_scopes else []


def _has_required_scopes(credentials: Credentials, required_scopes: list[str]) -> bool:
    granted_scopes = _credential_scopes(credentials)
    return all(scope in granted_scopes for scope in required_scopes)


def _log_credential_source(
    source: str,
    user_google_email: str | None,
    session_id: str | None,
    found: bool,
    reason: str | None = None,
) -> None:
    """Emit consistent diagnostics for credential source selection."""
    session_hint = session_id[:8] if session_id else None
    logger.info(
        "[CRED_SOURCE] source=%s user=%s session=%s found=%s reason=%s",
        source,
        user_google_email,
        session_hint,
        found,
        reason or "-",
    )


def _get_fastmcp_session_id_safe() -> str | None:
    """Resolve FastMCP session ID without creating import-time cycles."""
    try:
        from core.context import get_fastmcp_session_id

        return get_fastmcp_session_id()
    except Exception:
        return None


def _get_auth_flow_mode() -> str:
    """Return requested auth flow mode from environment, defaulting to auto."""
    mode = os.getenv(AUTH_FLOW_MODE_ENV, AUTH_FLOW_AUTO).strip().lower()
    if mode in {AUTH_FLOW_AUTO, AUTH_FLOW_CALLBACK, AUTH_FLOW_DEVICE}:
        return mode
    logger.warning("Unknown %s value '%s'; falling back to '%s'", AUTH_FLOW_MODE_ENV, mode, AUTH_FLOW_AUTO)
    return AUTH_FLOW_AUTO


def _get_effective_auth_flow_mode(
    user_google_email: str | None = None,
    override_client_key: str | None = None,
) -> str:
    """
    Resolve effective auth mode.

    In `auto` mode, stdio prefers device flow (more robust with MCP-hosted subprocess lifecycles),
    while streamable-http uses callback flow.
    """
    configured_mode = _get_auth_flow_mode()
    if configured_mode in {AUTH_FLOW_CALLBACK, AUTH_FLOW_DEVICE}:
        return configured_mode

    if user_google_email:
        try:
            oauth_client = resolve_oauth_client_for_user(
                user_google_email,
                override_client_key=override_client_key,
            )
            if oauth_client.flow_preference in {AUTH_FLOW_CALLBACK, AUTH_FLOW_DEVICE}:
                logger.info(
                    "Auth flow mode overridden by oauth client config: user=%s flow_preference=%s",
                    user_google_email,
                    oauth_client.flow_preference,
                )
                return oauth_client.flow_preference
        except Exception as exc:
            logger.debug("Could not resolve oauth client flow preference for %s: %s", user_google_email, exc)

    transport_mode = get_transport_mode()
    return AUTH_FLOW_DEVICE if transport_mode == "stdio" else AUTH_FLOW_CALLBACK


def _is_device_flow_invalid_client_error(details: str) -> bool:
    """Return True when Google rejects device flow for OAuth client type."""
    normalized = details.lower()
    return ("invalid_client" in normalized and "device" in normalized) or "invalid client type" in normalized


async def _start_callback_auth_challenge(
    user_google_email: str,
    service_name: str,
    required_scopes: list[str],
    fallback_reason: str | None = None,
    override_client_key: str | None = None,
) -> tuple[None, str]:
    """Start callback flow and optionally prefix a fallback explanation."""
    oauth_redirect_uri = resolve_oauth_redirect_uri_for_auth_flow()
    auth_message = await start_auth_flow(
        user_google_email=user_google_email,
        service_name=service_name,
        redirect_uri=oauth_redirect_uri,
        override_client_key=override_client_key,
    )

    if fallback_reason:
        fallback_header = (
            "Device authorization is not supported by the configured OAuth client for this environment. "
            f"Automatically falling back to callback flow. Details: {fallback_reason}"
        )
        return None, f"{fallback_header}\n\n{auth_message}"

    return None, auth_message


def _resolve_oauth_client_selection(
    user_google_email: str | None,
    override_client_key: str | None = None,
) -> OAuthClientSelection:
    """Resolve OAuth client selection for account/domain-aware auth routing."""
    if user_google_email:
        return resolve_oauth_client_for_user(user_google_email, override_client_key=override_client_key)

    # Backward-compatible fallback for callsites without user context.
    config = load_client_secrets_from_env() or {}
    client_cfg = config.get("web") or config.get("installed") or {}
    client_id = client_cfg.get("client_id")
    client_secret = client_cfg.get("client_secret")
    if not client_id:
        raise AuthenticationError("OAuth client ID is missing. Set GOOGLE_OAUTH_CLIENT_ID.")
    return OAuthClientSelection(
        client_key="legacy-env",
        client_id=client_id,
        client_secret=client_secret,
        source="legacy_env",
        selection_mode="legacy",
    )


def _resolve_client_id_and_secret(
    user_google_email: str | None,
    override_client_key: str | None = None,
) -> tuple[OAuthClientSelection, str, str | None]:
    """Resolve OAuth client selection and credentials for callback/device flows."""
    oauth_client = _resolve_oauth_client_selection(user_google_email, override_client_key=override_client_key)
    return oauth_client, oauth_client.client_id, oauth_client.client_secret


def _store_get_credential_for_client(
    credential_store: Any,
    user_google_email: str,
    oauth_client_key: str | None,
) -> Credentials | None:
    """Compat wrapper for client-scoped credential retrieval."""
    if oauth_client_key and hasattr(credential_store, "get_credential_for_client"):
        return credential_store.get_credential_for_client(oauth_client_key, user_google_email)
    return credential_store.get_credential(user_google_email)


def _store_put_credential_for_client(
    credential_store: Any,
    user_google_email: str,
    credentials: Credentials,
    oauth_client_key: str | None,
) -> bool:
    """Compat wrapper for client-scoped credential persistence."""
    if oauth_client_key and hasattr(credential_store, "store_credential_for_client"):
        return credential_store.store_credential_for_client(oauth_client_key, user_google_email, credentials)
    return credential_store.store_credential(user_google_email, credentials)


def resolve_oauth_redirect_uri_for_auth_flow() -> str:
    """
    Resolve redirect URI for callback-based auth and ensure callback availability in stdio mode.
    """
    transport_mode = get_transport_mode()
    if transport_mode != "stdio":
        return get_oauth_redirect_uri_for_current_mode()

    from auth.oauth_callback_server import start_oauth_callback_server

    success, error_msg, oauth_redirect_uri = start_oauth_callback_server()
    if not success or not oauth_redirect_uri:
        error_detail = f" ({error_msg})" if error_msg else ""
        raise GoogleAuthenticationError(f"Cannot initiate OAuth flow - callback server unavailable{error_detail}")
    return oauth_redirect_uri


def _build_device_auth_message(
    user_google_email: str,
    service_name: str,
    user_code: str,
    verification_url: str,
    expires_in_seconds: int,
    verification_url_complete: str | None = None,
    status_hint: str | None = None,
) -> str:
    minutes = max(1, expires_in_seconds // 60)
    lines = [
        f"**ACTION REQUIRED: Google Device Authentication Needed for {service_name} ('{user_google_email}')**",
        "This MCP is using device authorization flow for reliability in stdio/agent-hosted environments.",
    ]

    if status_hint == "authorization_pending":
        lines.append("Authorization is still pending.")
    elif status_hint == "slow_down":
        lines.append("Google requested slower polling; authorization is still pending.")
    elif status_hint == "expired_token":
        lines.append("Previous device code expired; a new code is provided below.")
    elif status_hint == "access_denied":
        lines.append("Previous device code was denied; a new code is provided below.")

    lines.extend(
        [
            "",
            f"Verification URL: {verification_url}",
            f"User Code: `{user_code}`",
        ]
    )

    if verification_url_complete:
        lines.append(f"Direct Verification Link: {verification_url_complete}")

    lines.extend(
        [
            f"Code expires in about {minutes} minute(s).",
            "After completing authorization in the browser, retry your original command in the MCP client.",
            "Use the same Google account expected for this MCP server.",
        ]
    )

    return "\n".join(lines)


def _start_or_resume_device_auth_flow(
    user_google_email: str,
    service_name: str,
    required_scopes: list[str],
    status_hint: str | None = None,
    override_client_key: str | None = None,
) -> str:
    """
    Create or reuse a pending device flow for a user and return user instructions.
    """
    oauth_client, client_id, client_secret = _resolve_client_id_and_secret(
        user_google_email,
        override_client_key=override_client_key,
    )

    store = get_oauth21_session_store()
    pending = store.get_pending_device_flow(user_google_email, oauth_client_key=oauth_client.client_key)

    if pending and status_hint in {None, "authorization_pending", "slow_down"}:
        expires_at = pending.get("expires_at")
        remaining_seconds = 900
        if isinstance(expires_at, datetime):
            remaining_seconds = max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
        return _build_device_auth_message(
            user_google_email=user_google_email,
            service_name=service_name,
            user_code=pending.get("user_code", "<unknown>"),
            verification_url=pending.get("verification_url", "https://www.google.com/device"),
            verification_url_complete=pending.get("verification_url_complete"),
            expires_in_seconds=remaining_seconds,
            status_hint=status_hint,
        )

    scope_string = " ".join(sorted(set(required_scopes)))
    payload = {
        "client_id": client_id,
        "scope": scope_string,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    response = requests.post(DEVICE_AUTH_ENDPOINT, data=payload, timeout=15)
    if response.status_code >= 400:
        error_details = response.text
        try:
            error_payload = response.json()
            error_details = f"{error_payload.get('error')}: {error_payload.get('error_description') or response.text}"
        except ValueError:
            pass
        raise GoogleAuthenticationError(f"Failed to start device authorization flow: {error_details}")

    data = response.json()
    device_code = data.get("device_code")
    user_code = data.get("user_code")
    verification_url = data.get("verification_url") or data.get("verification_uri")
    verification_url_complete = data.get("verification_url_complete")
    interval = int(data.get("interval", 5))
    expires_in = int(data.get("expires_in", 1800))

    if not device_code or not user_code or not verification_url:
        raise GoogleAuthenticationError("Device authorization response from Google is missing required fields.")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    store.store_pending_device_flow(
        user_email=user_google_email,
        oauth_client_key=oauth_client.client_key,
        device_code=device_code,
        user_code=user_code,
        verification_url=verification_url,
        verification_url_complete=verification_url_complete,
        interval=interval,
        expires_at=expires_at,
    )

    return _build_device_auth_message(
        user_google_email=user_google_email,
        service_name=service_name,
        user_code=user_code,
        verification_url=verification_url,
        verification_url_complete=verification_url_complete,
        expires_in_seconds=expires_in,
        status_hint=status_hint,
    )


async def _poll_pending_device_auth_flow(
    user_google_email: str,
    required_scopes: list[str],
    session_id: str | None = None,
    override_client_key: str | None = None,
) -> tuple[Credentials | None, str | None]:
    """
    Poll pending device flow once.

    Returns:
        (credentials, status_hint)
        - credentials is set when token exchange succeeds
        - status_hint indicates pending/slow_down/expired_token/access_denied/error
    """
    oauth_client, client_id, client_secret = _resolve_client_id_and_secret(
        user_google_email,
        override_client_key=override_client_key,
    )

    store = get_oauth21_session_store()
    pending = store.get_pending_device_flow(user_google_email, oauth_client_key=oauth_client.client_key)
    if not pending:
        return None, None

    device_code = pending.get("device_code")
    if not device_code:
        store.clear_pending_device_flow(user_google_email, oauth_client_key=oauth_client.client_key)
        return None, "error:missing_device_code"

    payload = {
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": DEVICE_TOKEN_GRANT_TYPE,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    response = requests.post(DEFAULT_TOKEN_URI, data=payload, timeout=15)
    if response.status_code < 400:
        token_response = response.json()
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = int(token_response.get("expires_in", 3600))
        scope_field = token_response.get("scope")
        scope_list = scope_field.split() if scope_field else required_scopes

        if not access_token:
            return None, "error:missing_access_token"

        expiry = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in, 60))
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=DEFAULT_TOKEN_URI,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scope_list,
            expiry=expiry,
        )

        resolved_email = user_google_email
        user_info = await get_user_info(credentials)
        if user_info and user_info.get("email"):
            resolved_email = user_info["email"]

        if resolved_email.lower() != user_google_email.lower():
            store.clear_pending_device_flow(user_google_email, oauth_client_key=oauth_client.client_key)
            raise GoogleAuthenticationError(
                f"Device auth completed for '{resolved_email}', but MCP requested '{user_google_email}'. "
                "Please retry using the intended account."
            )

        credential_store = get_credential_store()
        _store_put_credential_for_client(
            credential_store,
            resolved_email,
            credentials,
            oauth_client_key=oauth_client.client_key,
        )

        store.store_session(
            user_email=resolved_email,
            oauth_client_key=oauth_client.client_key,
            access_token=access_token,
            refresh_token=refresh_token,
            token_uri=DEFAULT_TOKEN_URI,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scope_list,
            expiry=expiry,
            mcp_session_id=session_id,
            issuer="https://accounts.google.com",
        )
        store.clear_pending_device_flow(user_google_email, oauth_client_key=oauth_client.client_key)
        return credentials, None

    status_hint = "error:unknown"
    try:
        error_payload = response.json()
        error_code = error_payload.get("error")
        error_description = error_payload.get("error_description")
        if error_code in {"authorization_pending", "slow_down"}:
            status_hint = error_code
        elif error_code in {"expired_token", "access_denied"}:
            status_hint = error_code
            store.clear_pending_device_flow(user_google_email, oauth_client_key=oauth_client.client_key)
        else:
            status_hint = f"error:{error_code}:{error_description}"
    except ValueError:
        status_hint = f"error:http_{response.status_code}:{response.text}"

    return None, status_hint


async def initiate_auth_challenge(
    user_google_email: str,
    service_name: str,
    required_scopes: list[str],
    session_id: str | None = None,
    override_client_key: str | None = None,
) -> tuple[Credentials | None, str]:
    """
    Initiate or resume authentication based on configured auth-flow mode.

    Returns:
        (credentials, message)
        - credentials: set when auth is already complete (e.g., device flow finalized)
        - message: actionable instructions when user interaction is required
    """
    requested_auth_mode = _get_auth_flow_mode()
    effective_auth_mode = _get_effective_auth_flow_mode(
        user_google_email,
        override_client_key=override_client_key,
    )

    if effective_auth_mode == AUTH_FLOW_DEVICE:
        credentials, device_status = await _poll_pending_device_auth_flow(
            user_google_email=user_google_email,
            required_scopes=required_scopes,
            session_id=session_id,
            override_client_key=override_client_key,
        )
        if credentials and credentials.valid:
            return credentials, f"Authentication completed successfully for '{user_google_email}'."

        if device_status and device_status.startswith("error:"):
            if requested_auth_mode == AUTH_FLOW_AUTO and _is_device_flow_invalid_client_error(device_status):
                logger.warning(
                    "Device auth failed with invalid_client in auto mode; falling back to callback flow. "
                    "user=%s service=%s details=%s",
                    user_google_email,
                    service_name,
                    device_status,
                )
                return await _start_callback_auth_challenge(
                    user_google_email=user_google_email,
                    service_name=service_name,
                    required_scopes=required_scopes,
                    fallback_reason=device_status,
                    override_client_key=override_client_key,
                )
            raise GoogleAuthenticationError(
                "Device authorization polling failed. "
                f"Details: {device_status}. Try running the command again to restart auth."
            )

        try:
            challenge_message = _start_or_resume_device_auth_flow(
                user_google_email=user_google_email,
                service_name=service_name,
                required_scopes=required_scopes,
                status_hint=device_status,
                override_client_key=override_client_key,
            )
            return None, challenge_message
        except GoogleAuthenticationError as exc:
            if requested_auth_mode == AUTH_FLOW_AUTO and _is_device_flow_invalid_client_error(str(exc)):
                logger.warning(
                    "Device auth initiation failed with invalid_client in auto mode; "
                    "falling back to callback flow. user=%s service=%s",
                    user_google_email,
                    service_name,
                )
                return await _start_callback_auth_challenge(
                    user_google_email=user_google_email,
                    service_name=service_name,
                    required_scopes=required_scopes,
                    fallback_reason=str(exc),
                    override_client_key=override_client_key,
                )
            raise

    return await _start_callback_auth_challenge(
        user_google_email=user_google_email,
        service_name=service_name,
        required_scopes=required_scopes,
        override_client_key=override_client_key,
    )


def _find_any_credentials(
    base_dir: str = DEFAULT_CREDENTIALS_DIR,
) -> Credentials | None:
    """
    Find and load any valid credentials from the credentials directory.
    Used in single-user mode to bypass session-to-OAuth mapping.

    Returns:
        First valid Credentials object found, or None if none exist.
    """
    try:
        store = get_credential_store()
        users = store.list_users()
        if not users:
            logger.info("[single-user] No users found with credentials via credential store")
            return None

        # Return credentials for the first user found
        first_user = users[0]
        credentials = store.get_credential(first_user)
        if credentials:
            logger.info(f"[single-user] Found credentials for {first_user} via credential store")
            return credentials
        else:
            logger.warning(f"[single-user] Could not load credentials for {first_user} via credential store")

    except Exception as e:
        logger.error(f"[single-user] Error finding credentials via credential store: {e}")

    logger.info("[single-user] No valid credentials found via credential store")
    return None


def save_credentials_to_session(session_id: str, credentials: Credentials):
    """Saves user credentials using OAuth21SessionStore."""
    # Get user email from credentials if possible
    user_email = None
    if credentials and credentials.id_token:
        try:
            decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
            user_email = decoded_token.get("email")
        except Exception as e:
            logger.debug(f"Could not decode id_token to get email: {e}")

    if user_email:
        store = get_oauth21_session_store()
        oauth_client_key: str | None = None
        try:
            oauth_client_key = _resolve_oauth_client_selection(user_email).client_key
        except Exception:
            oauth_client_key = None
        token = credentials.token
        if not token:
            logger.warning("Could not save credentials to session store - missing access token")
            return
        store.store_session(
            user_email=user_email,
            oauth_client_key=oauth_client_key,
            access_token=token,
            refresh_token=credentials.refresh_token,
            token_uri=_token_uri_or_default(credentials),
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=_credential_scopes(credentials),
            expiry=credentials.expiry,
            mcp_session_id=session_id,
        )
        logger.debug(f"Credentials saved to OAuth21SessionStore for session_id: {session_id}, user: {user_email}")
    else:
        logger.warning(f"Could not save credentials to session store - no user email found for session: {session_id}")


def load_credentials_from_session(session_id: str) -> Credentials | None:
    """Loads user credentials from OAuth21SessionStore."""
    store = get_oauth21_session_store()
    credentials = store.get_credentials_by_mcp_session(session_id)
    if credentials:
        logger.debug(f"Credentials loaded from OAuth21SessionStore for session_id: {session_id}")
    else:
        logger.debug(f"No credentials found in OAuth21SessionStore for session_id: {session_id}")
    return credentials


def load_client_secrets_from_env() -> dict[str, Any] | None:
    """
    Loads client secrets from environment variables or embedded config.

    Priority:
    1. Environment variables (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET)
    2. Embedded credentials (default)

    Environment variables used:
        - GOOGLE_OAUTH_CLIENT_ID: OAuth 2.0 client ID
        - GOOGLE_OAUTH_CLIENT_SECRET: OAuth 2.0 client secret
        - GOOGLE_OAUTH_REDIRECT_URI: (optional) OAuth redirect URI

    Returns:
        Client secrets configuration dict compatible with Google OAuth library.
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

    if client_id and client_secret:
        # Create config structure that matches Google client secrets format
        web_config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }

        # Add redirect_uri if provided via environment variable
        if redirect_uri:
            web_config["redirect_uris"] = [redirect_uri]  # type: ignore[assignment]

        # Return the full config structure expected by Google OAuth library
        config = {"web": web_config}

        logger.info("Loaded OAuth client credentials from environment variables")
        return config

    # Use embedded credentials
    logger.info(f"Using embedded {APP_NAME} OAuth credentials")
    return get_google_oauth_config()


def load_client_secrets(client_secrets_path: str) -> dict[str, Any]:
    """
    Loads the client secrets from environment variables (preferred) or from the client secrets file.

    Priority order:
    1. Environment variables (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET)
    2. File-based credentials at the specified path

    Args:
        client_secrets_path: Path to the client secrets JSON file (used as fallback)

    Returns:
        Client secrets configuration dict

    Raises:
        ValueError: If client secrets file has invalid format
        IOError: If file cannot be read and no environment variables are set
    """
    # First, try to load from environment variables
    env_config = load_client_secrets_from_env()
    if env_config:
        # Extract the "web" config from the environment structure
        return env_config["web"]

    # Fall back to loading from file
    try:
        with open(client_secrets_path) as f:
            client_config = json.load(f)
            # The file usually contains a top-level key like "web" or "installed"
            if "web" in client_config:
                logger.info(f"Loaded OAuth client credentials from file: {client_secrets_path}")
                return client_config["web"]
            elif "installed" in client_config:
                logger.info(f"Loaded OAuth client credentials from file: {client_secrets_path}")
                return client_config["installed"]
            else:
                logger.error(f"Client secrets file {client_secrets_path} has unexpected format.")
                raise ValueError("Invalid client secrets file format")
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error loading client secrets file {client_secrets_path}: {e}")
        raise


def check_client_secrets() -> str | None:
    """
    Checks for the presence of OAuth client secrets.

    With embedded credentials, this always succeeds unless
    there's a configuration error.

    Returns:
        An error message string if secrets are not found, otherwise None.
    """
    try:
        env_config = load_client_secrets_from_env()
        if env_config:
            return None
    except Exception:
        # Continue to auth_clients check below.
        pass

    # Multi-client mode: allow setup via auth_clients.json without global env client credentials.
    try:
        auth_clients_config, _ = ensure_auth_clients_config()
        oauth_clients = auth_clients_config.get("oauth_clients", {})
        if isinstance(oauth_clients, dict) and oauth_clients:
            return None
    except Exception:
        pass

    # This should never happen with embedded credentials
    logger.error("OAuth client credentials not available - this should not happen with embedded credentials")
    return "OAuth client credentials not available. Please contact the project maintainers."


def create_oauth_flow(
    scopes: list[str],
    redirect_uri: str,
    state: str | None = None,
    oauth_client: OAuthClientSelection | None = None,
    code_verifier: str | None = None,
) -> Flow:
    """Creates an OAuth flow using environment variables or client secrets file."""
    if oauth_client is not None:
        client_config = {
            "web": {
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri=redirect_uri,
            state=state,
            code_verifier=code_verifier,
        )
        logger.debug("Created OAuth flow from client selection '%s'", oauth_client.client_key)
        return flow

    # Try environment variables first
    env_config = load_client_secrets_from_env()
    if env_config:
        # Use client config directly
        flow = Flow.from_client_config(
            env_config,
            scopes=scopes,
            redirect_uri=redirect_uri,
            state=state,
            code_verifier=code_verifier,
        )
        logger.debug("Created OAuth flow from environment variables")
        return flow

    # Fall back to file-based config
    if not os.path.exists(CONFIG_CLIENT_SECRETS_PATH):
        raise FileNotFoundError(
            f"OAuth client secrets file not found at {CONFIG_CLIENT_SECRETS_PATH} and no environment variables set"
        )

    flow = Flow.from_client_secrets_file(
        CONFIG_CLIENT_SECRETS_PATH,
        scopes=scopes,
        redirect_uri=redirect_uri,
        state=state,
        code_verifier=code_verifier,
    )
    logger.debug(f"Created OAuth flow from client secrets file: {CONFIG_CLIENT_SECRETS_PATH}")
    return flow


# --- Core OAuth Logic ---


async def start_auth_flow(
    user_google_email: str | None,
    service_name: str,  # e.g., "Google Calendar", "Gmail" for user messages
    redirect_uri: str,
    override_client_key: str | None = None,
) -> str:
    """
    Initiates the Google OAuth flow and returns an actionable message for the user.

    Args:
        user_google_email: The user's specified Google email, if provided.
        service_name: The name of the Google service requiring auth (for user messages).
        redirect_uri: The URI Google will redirect to after authorization.

    Returns:
        A formatted string containing guidance for the LLM/user.

    Raises:
        Exception: If the OAuth flow cannot be initiated.
    """
    initial_email_provided = bool(
        user_google_email and user_google_email.strip() and user_google_email.lower() != "default"
    )
    user_display_name = f"{service_name} for '{user_google_email}'" if initial_email_provided else service_name

    logger.info(f"[start_auth_flow] Initiating auth for {user_display_name} with scopes for enabled tools.")

    # Note: Caller should ensure OAuth callback is available before calling this function

    try:
        if "OAUTHLIB_INSECURE_TRANSPORT" not in os.environ and (
            "localhost" in redirect_uri or "127.0.0.1" in redirect_uri
        ):
            logger.warning("OAUTHLIB_INSECURE_TRANSPORT not set. Setting it for localhost/local development.")
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        oauth_state = os.urandom(16).hex()

        oauth_client = _resolve_oauth_client_selection(
            user_google_email,
            override_client_key=override_client_key,
        )

        flow = create_oauth_flow(
            scopes=get_current_scopes(),
            redirect_uri=redirect_uri,
            state=oauth_state,
            oauth_client=oauth_client,
        )

        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        code_verifier = getattr(flow, "code_verifier", None)

        session_id = None
        try:
            session_id = _get_fastmcp_session_id_safe()
        except Exception as e:
            logger.debug(f"Could not retrieve FastMCP session ID for state binding: {e}")

        store = get_oauth21_session_store()
        store.store_oauth_state(
            oauth_state,
            session_id=session_id,
            oauth_client_key=oauth_client.client_key,
            expected_user_email=user_google_email,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )

        logger.info(
            f"Auth flow started for {user_display_name}. State: {oauth_state[:8]}... Advise user to visit: {auth_url}"
        )

        message_lines = [
            f"**ACTION REQUIRED: Google Authentication Needed for {user_display_name}**\n",
            f"To proceed, the user must authorize this application for {service_name} access using all required permissions.",
            "**LLM, please present this exact authorization URL to the user as a clickable hyperlink:**",
            f"Authorization URL: {auth_url}",
            f"Markdown for hyperlink: [Click here to authorize {service_name} access]({auth_url})\n",
            "**LLM, after presenting the link, instruct the user as follows:**",
            "1. Click the link and complete the authorization in their browser.",
        ]

        if not initial_email_provided:
            message_lines.extend(
                [
                    "2. After successful authorization, the browser page will display the authenticated email address.",
                    "   **LLM: Instruct the user to provide you with this email address.**",
                    "3. Once you have the email, **retry their original command, ensuring you include this `user_google_email`.**",
                ]
            )
        else:
            message_lines.append("2. After successful authorization, **retry their original command**.")

        message_lines.append(
            f"\nThe application will use the new credentials. If '{user_google_email}' was provided, it must match the authenticated account."
        )
        return "\n".join(message_lines)

    except FileNotFoundError as e:
        error_text = f"OAuth client credentials not found: {e}. Please either:\n1. Set environment variables: GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET\n2. Ensure '{CONFIG_CLIENT_SECRETS_PATH}' file exists"
        logger.error(error_text, exc_info=True)
        raise AuthenticationError(error_text) from e
    except Exception as e:
        error_text = f"Could not initiate authentication for {user_display_name} due to an unexpected error: {str(e)}"
        logger.error(
            f"Failed to start the OAuth flow for {user_display_name}: {e}",
            exc_info=True,
        )
        raise AuthenticationError(error_text) from e


async def handle_auth_callback(
    scopes: list[str],
    authorization_response: str,
    redirect_uri: str,
    credentials_base_dir: str = DEFAULT_CREDENTIALS_DIR,
    session_id: str | None = None,
    client_secrets_path: str | None = None,
) -> tuple[str, Credentials]:
    """
    Handles the callback from Google, exchanges the code for credentials,
    fetches user info, determines user_google_email, saves credentials (file & session),
    and returns them.

    Args:
        scopes: List of OAuth scopes requested.
        authorization_response: The full callback URL from Google.
        redirect_uri: The redirect URI.
        credentials_base_dir: Base directory for credential files.
        session_id: Optional MCP session ID to associate with the credentials.
        client_secrets_path: (Deprecated) Path to client secrets file. Ignored if environment variables are set.

    Returns:
        A tuple containing the user_google_email and the obtained Credentials object.

    Raises:
        ValueError: If the state is missing or doesn't match.
        FlowExchangeError: If the code exchange fails.
        HttpError: If fetching user info fails.
    """
    try:
        # Log deprecation warning if old parameter is used
        if client_secrets_path:
            logger.warning(
                "The 'client_secrets_path' parameter is deprecated. Use GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables instead."
            )

        # Allow HTTP for localhost in development
        if "OAUTHLIB_INSECURE_TRANSPORT" not in os.environ:
            logger.warning("OAUTHLIB_INSECURE_TRANSPORT not set. Setting it for localhost development.")
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        store = get_oauth21_session_store()
        parsed_response = urlparse(authorization_response)
        state_values = parse_qs(parsed_response.query).get("state")
        state = state_values[0] if state_values else None

        if not state:
            raise ValueError("OAuth state parameter is missing or invalid")
        state_info = store.validate_oauth_state(state, session_id=session_id)
        state_oauth_client_key = state_info.get("oauth_client_key")
        expected_user_email = state_info.get("expected_user_email")
        code_verifier = state_info.get("code_verifier")
        redirect_uri_for_flow = state_info.get("redirect_uri") or redirect_uri
        logger.debug(
            "Validated OAuth callback state %s for session %s",
            (state[:8] if state else "<missing>"),
            state_info.get("session_id") or "<unknown>",
        )

        oauth_client = None
        if isinstance(state_oauth_client_key, str) and state_oauth_client_key.strip():
            oauth_client = _resolve_oauth_client_selection(
                expected_user_email,
                override_client_key=state_oauth_client_key,
            )

        flow = create_oauth_flow(
            scopes=scopes,
            redirect_uri=redirect_uri_for_flow,
            state=state,
            oauth_client=oauth_client,
            code_verifier=code_verifier,
        )

        # Exchange the authorization code for credentials
        # Note: fetch_token will use the redirect_uri configured in the flow
        flow.fetch_token(authorization_response=authorization_response)
        flow_credentials = flow.credentials
        if not isinstance(flow_credentials, Credentials):
            raise AuthenticationError("Unsupported credential type returned by OAuth flow")
        credentials = flow_credentials
        logger.info("Successfully exchanged authorization code for tokens.")

        user_info = await get_user_info(credentials)
        if not user_info or "email" not in user_info:
            logger.error("Could not retrieve user email from Google.")
            raise ValueError("Failed to get user email for identification.")

        user_google_email = user_info["email"]
        if expected_user_email and user_google_email.lower() != str(expected_user_email).lower():
            raise GoogleAuthenticationError(
                f"Authentication completed for '{user_google_email}', but expected '{expected_user_email}'. "
                "Hard-fail policy is active; no cross-client fallback will be attempted."
            )
        logger.info(f"Identified user_google_email: {user_google_email}")

        # Save the credentials
        credential_store = get_credential_store()
        oauth_client_key = oauth_client.client_key if oauth_client else None
        _store_put_credential_for_client(
            credential_store,
            user_google_email,
            credentials,
            oauth_client_key=oauth_client_key,
        )

        # Always save to OAuth21SessionStore for centralized management
        store = get_oauth21_session_store()
        access_token = credentials.token
        if not access_token:
            raise AuthenticationError("OAuth callback did not return an access token")
        store.store_session(
            user_email=user_google_email,
            oauth_client_key=oauth_client_key,
            access_token=access_token,
            refresh_token=credentials.refresh_token,
            token_uri=_token_uri_or_default(credentials),
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=_credential_scopes(credentials),
            expiry=credentials.expiry,
            mcp_session_id=session_id,
            issuer="https://accounts.google.com",  # Add issuer for Google tokens
        )

        # If session_id is provided, also save to session cache for compatibility
        if session_id:
            save_credentials_to_session(session_id, credentials)

        # Consume the state only after callback processing succeeds.
        store.consume_oauth_state(state)

        return user_google_email, credentials

    except Exception as e:  # Catch specific exceptions like FlowExchangeError if needed
        logger.error(f"Error handling auth callback: {e}")
        raise  # Re-raise for the caller


def get_credentials(
    user_google_email: str | None,  # Can be None if relying on session_id
    required_scopes: list[str],
    client_secrets_path: str | None = None,
    credentials_base_dir: str = DEFAULT_CREDENTIALS_DIR,
    session_id: str | None = None,
    override_client_key: str | None = None,
) -> Credentials | None:
    """
    Retrieves stored credentials, prioritizing OAuth 2.1 store, then session, then file. Refreshes if necessary.
    If credentials are loaded from file and a session_id is present, they are cached in the session.
    In single-user mode, bypasses session mapping and uses any available credentials.

    Args:
        user_google_email: Optional user's Google email.
        required_scopes: List of scopes the credentials must have.
        client_secrets_path: Optional path to client secrets (legacy; refresh uses embedded client info).
        credentials_base_dir: Base directory for credential files.
        session_id: Optional MCP session ID.

    Returns:
        Valid Credentials object or None.
    """
    oauth_client_key: str | None = None
    if user_google_email:
        try:
            oauth_client_selection = _resolve_oauth_client_selection(
                user_google_email,
                override_client_key=override_client_key,
            )
            oauth_client_key = oauth_client_selection.client_key
        except Exception as e:
            logger.warning("[get_credentials] OAuth client resolution failed for %s: %s", user_google_email, e)
            return None

    # First, try OAuth 2.1 session store if we have a session_id (FastMCP session)
    if session_id:
        try:
            store = get_oauth21_session_store()

            # Try to get credentials by MCP session
            credentials = store.get_credentials_by_mcp_session(session_id)
            if credentials:
                logger.info(f"[get_credentials] Found OAuth 2.1 credentials for MCP session {session_id}")
                _log_credential_source("oauth21_mcp_session", user_google_email, session_id, True, "loaded")

                # Check scopes
                if not _has_required_scopes(credentials, required_scopes):
                    logger.warning(
                        f"[get_credentials] OAuth 2.1 credentials lack required scopes. Need: {required_scopes}, Have: {_credential_scopes(credentials)}"
                    )
                    return None

                # Return if valid
                if credentials.valid:
                    return credentials
                elif credentials.expired and credentials.refresh_token:
                    # Try to refresh
                    try:
                        credentials.refresh(Request())
                        logger.info(f"[get_credentials] Refreshed OAuth 2.1 credentials for session {session_id}")
                        # Update stored credentials
                        user_email = store.get_user_by_mcp_session(session_id)
                        if user_email:
                            refreshed_token = credentials.token
                            if not refreshed_token:
                                logger.error("[get_credentials] Missing access token after OAuth 2.1 refresh")
                                return None
                            store.store_session(
                                user_email=user_email,
                                oauth_client_key=store.get_client_by_mcp_session(session_id),
                                access_token=refreshed_token,
                                refresh_token=credentials.refresh_token,
                                scopes=_credential_scopes(credentials),
                                expiry=credentials.expiry,
                                mcp_session_id=session_id,
                            )
                        return credentials
                    except Exception as e:
                        logger.error(f"[get_credentials] Failed to refresh OAuth 2.1 credentials: {e}")
                        _log_credential_source(
                            "oauth21_mcp_session",
                            user_google_email,
                            session_id,
                            False,
                            "refresh_failed",
                        )
                        return None
            else:
                _log_credential_source("oauth21_mcp_session", user_google_email, session_id, False, "not_found")
        except ImportError:
            pass  # OAuth 2.1 store not available
        except Exception as e:
            logger.debug(f"[get_credentials] Error checking OAuth 2.1 store: {e}")

    # Auto-recovery: If no credentials found via session but session_id exists,
    # check if there's only one user with credentials and auto-bind
    if (
        session_id
        and not os.getenv("MCP_SINGLE_USER_MODE")
        and (not oauth_client_key or oauth_client_key == "legacy-env")
    ):
        try:
            store = get_oauth21_session_store()
            cred_store = get_credential_store()

            if not store.get_user_by_mcp_session(session_id):
                file_users = cred_store.list_users()
                if len(file_users) == 1:
                    single_user = file_users[0]
                    logger.info(
                        f"[get_credentials] Single user detected ({single_user}), auto-binding session {session_id}"
                    )

                    file_credentials = cred_store.get_credential(single_user)
                    if file_credentials:
                        _log_credential_source(
                            "file_store_auto_recovery", single_user, session_id, True, "single_user_bind"
                        )
                        file_token = file_credentials.token
                        if not file_token:
                            logger.warning("[get_credentials] Auto-recovered credentials missing access token")
                            return None
                        try:
                            store.store_session(
                                user_email=single_user,
                                access_token=file_token,
                                refresh_token=file_credentials.refresh_token,
                                token_uri=_token_uri_or_default(file_credentials),
                                client_id=file_credentials.client_id,
                                client_secret=file_credentials.client_secret,
                                scopes=_credential_scopes(file_credentials),
                                expiry=file_credentials.expiry,
                                mcp_session_id=session_id,
                                issuer="https://accounts.google.com",
                            )

                            if not _has_required_scopes(file_credentials, required_scopes):
                                logger.warning(
                                    f"[get_credentials] Auto-recovered credentials lack required scopes. "
                                    f"Need: {required_scopes}, Have: {_credential_scopes(file_credentials)}"
                                )
                            elif file_credentials.valid:
                                return file_credentials
                            elif file_credentials.expired and file_credentials.refresh_token:
                                try:
                                    file_credentials.refresh(Request())
                                    logger.info("[get_credentials] Refreshed auto-recovered credentials")
                                    cred_store.store_credential(single_user, file_credentials)
                                    refreshed_file_token = file_credentials.token
                                    if not refreshed_file_token:
                                        logger.error(
                                            "[get_credentials] Missing access token after auto-recovery refresh"
                                        )
                                        return None
                                    store.store_session(
                                        user_email=single_user,
                                        access_token=refreshed_file_token,
                                        refresh_token=file_credentials.refresh_token,
                                        token_uri=_token_uri_or_default(file_credentials),
                                        client_id=file_credentials.client_id,
                                        client_secret=file_credentials.client_secret,
                                        scopes=_credential_scopes(file_credentials),
                                        expiry=file_credentials.expiry,
                                        mcp_session_id=session_id,
                                        issuer="https://accounts.google.com",
                                    )
                                    return file_credentials
                                except Exception as e:
                                    logger.error(f"[get_credentials] Failed to refresh auto-recovered credentials: {e}")
                        except ValueError as e:
                            logger.warning(f"[get_credentials] Could not auto-bind session: {e}")
                    else:
                        _log_credential_source(
                            "file_store_auto_recovery", single_user, session_id, False, "missing_user_file"
                        )
        except Exception as e:
            logger.debug(f"[get_credentials] Error in auto-recovery: {e}")

    # Check for single-user mode
    if os.getenv("MCP_SINGLE_USER_MODE") == "1":
        logger.info("[get_credentials] Single-user mode: bypassing session mapping, finding any credentials")
        credentials = _find_any_credentials(credentials_base_dir)
        if not credentials:
            logger.info(f"[get_credentials] Single-user mode: No credentials found in {credentials_base_dir}")
            _log_credential_source("single_user_scan", user_google_email, session_id, False, "no_files")
            return None
        _log_credential_source("single_user_scan", user_google_email, session_id, True, "loaded")

        if not user_google_email and credentials.valid:
            try:
                user_info = asyncio.run(get_user_info(credentials))
                if user_info and "email" in user_info:
                    user_google_email = user_info["email"]
                    logger.debug(
                        f"[get_credentials] Single-user mode: extracted user email {user_google_email} from credentials"
                    )
            except Exception as e:
                logger.debug(f"[get_credentials] Single-user mode: could not extract user email: {e}")
    else:
        credentials = None

        # Session ID should be provided by the caller
        if not session_id:
            logger.debug("[get_credentials] No session_id provided")

        logger.debug(
            f"[get_credentials] Called for user_google_email: '{user_google_email}', session_id: '{session_id}', required_scopes: {required_scopes}"
        )

        if session_id:
            credentials = load_credentials_from_session(session_id)
            if credentials:
                logger.debug(f"[get_credentials] Loaded credentials from session for session_id '{session_id}'.")
                _log_credential_source("session_cache", user_google_email, session_id, True, "loaded")

        if not credentials and user_google_email:
            if not is_stateless_mode():
                logger.debug(
                    f"[get_credentials] No session credentials, trying credential store for user_google_email '{user_google_email}'."
                )
                credential_store = get_credential_store()
                credentials = _store_get_credential_for_client(
                    credential_store,
                    user_google_email,
                    oauth_client_key=oauth_client_key,
                )
                _log_credential_source("file_store", user_google_email, session_id, bool(credentials), "lookup")
            else:
                logger.debug(
                    f"[get_credentials] No session credentials, skipping file store in stateless mode for user_google_email '{user_google_email}'."
                )
                _log_credential_source("file_store", user_google_email, session_id, False, "stateless_skip")

            if credentials and session_id:
                logger.debug(
                    f"[get_credentials] Loaded from file for user '{user_google_email}', caching to session '{session_id}'."
                )
                save_credentials_to_session(session_id, credentials)  # Cache for current session

        if not credentials:
            logger.info(
                f"[get_credentials] No credentials found for user '{user_google_email}' or session '{session_id}'."
            )
            _log_credential_source("all_sources", user_google_email, session_id, False, "none_available")
            return None

    logger.debug(
        f"[get_credentials] Credentials found. Scopes: {credentials.scopes}, Valid: {credentials.valid}, Expired: {credentials.expired}"
    )

    if not _has_required_scopes(credentials, required_scopes):
        logger.warning(
            f"[get_credentials] Credentials lack required scopes. Need: {required_scopes}, Have: {_credential_scopes(credentials)}. User: '{user_google_email}', Session: '{session_id}'"
        )
        return None  # Re-authentication needed for scopes

    logger.debug(
        f"[get_credentials] Credentials have sufficient scopes. User: '{user_google_email}', Session: '{session_id}'"
    )

    if credentials.valid:
        logger.debug(f"[get_credentials] Credentials are valid. User: '{user_google_email}', Session: '{session_id}'")
        return credentials
    elif credentials.expired and credentials.refresh_token:
        logger.info(
            f"[get_credentials] Credentials expired. Attempting refresh. User: '{user_google_email}', Session: '{session_id}'"
        )
        try:
            logger.debug("[get_credentials] Refreshing token using embedded client credentials")
            # client_config = load_client_secrets(client_secrets_path) # Not strictly needed if creds have client_id/secret
            credentials.refresh(Request())
            logger.info(
                f"[get_credentials] Credentials refreshed successfully. User: '{user_google_email}', Session: '{session_id}'"
            )

            # Save refreshed credentials (skip file save in stateless mode)
            if user_google_email:  # Always save to credential store if email is known
                if not is_stateless_mode():
                    credential_store = get_credential_store()
                    _store_put_credential_for_client(
                        credential_store,
                        user_google_email,
                        credentials,
                        oauth_client_key=oauth_client_key,
                    )
                else:
                    logger.info(f"Skipping credential file save in stateless mode for {user_google_email}")

                # Also update OAuth21SessionStore
                store = get_oauth21_session_store()
                refreshed_token = credentials.token
                if not refreshed_token:
                    logger.error("[get_credentials] Missing access token after refresh")
                    return None
                store.store_session(
                    user_email=user_google_email,
                    oauth_client_key=oauth_client_key,
                    access_token=refreshed_token,
                    refresh_token=credentials.refresh_token,
                    token_uri=_token_uri_or_default(credentials),
                    client_id=credentials.client_id,
                    client_secret=credentials.client_secret,
                    scopes=_credential_scopes(credentials),
                    expiry=credentials.expiry,
                    mcp_session_id=session_id,
                    issuer="https://accounts.google.com",  # Add issuer for Google tokens
                )

            if session_id:  # Update session cache if it was the source or is active
                save_credentials_to_session(session_id, credentials)
            return credentials
        except RefreshError as e:
            logger.warning(
                f"[get_credentials] RefreshError - token expired/revoked: {e}. User: '{user_google_email}', Session: '{session_id}'"
            )
            # For RefreshError, we should return None to trigger reauthentication
            return None
        except Exception as e:
            logger.error(
                f"[get_credentials] Error refreshing credentials: {e}. User: '{user_google_email}', Session: '{session_id}'",
                exc_info=True,
            )
            return None  # Failed to refresh
    else:
        logger.warning(
            f"[get_credentials] Credentials invalid/cannot refresh. Valid: {credentials.valid}, Refresh Token: {credentials.refresh_token is not None}. User: '{user_google_email}', Session: '{session_id}'"
        )
        return None


async def get_user_info(credentials: Credentials) -> dict[str, Any] | None:
    """Fetches basic user profile information (requires userinfo.email scope)."""
    if not credentials or not credentials.valid:
        logger.error("Cannot get user info: Invalid or missing credentials.")
        return None
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = await asyncio.to_thread(service.userinfo().get().execute)
        logger.info(f"Successfully fetched user info: {user_info.get('email')}")
        return user_info
    except HttpError as e:
        logger.error(f"HttpError fetching user info: {e.status_code} {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching user info: {e}")
        return None


# --- Centralized Google Service Authentication ---


async def get_authenticated_google_service(
    service_name: str,  # "gmail", "calendar", "drive", "docs"
    version: str,  # "v1", "v3"
    tool_name: str,  # For logging/debugging
    user_google_email: str,  # Required - no more Optional
    required_scopes: list[str],
    session_id: str | None = None,  # Session context for logging
    override_client_key: str | None = None,
) -> tuple[Any, str]:
    """
    Centralized Google service authentication for all MCP tools.
    Returns (service, user_email) on success or raises GoogleAuthenticationError.

    Args:
        service_name: The Google service name ("gmail", "calendar", "drive", "docs")
        version: The API version ("v1", "v3", etc.)
        tool_name: The name of the calling tool (for logging/debugging)
        user_google_email: The user's Google email address (required)
        required_scopes: List of required OAuth scopes

    Returns:
        tuple[service, user_email] on success

    Raises:
        GoogleAuthenticationError: When authentication is required or fails
    """

    # Try to get FastMCP session ID if not provided
    if not session_id:
        try:
            # First try context variable (works in async context)
            session_id = _get_fastmcp_session_id_safe()
            if session_id:
                logger.debug(f"[{tool_name}] Got FastMCP session ID from context: {session_id}")
            else:
                logger.debug(f"[{tool_name}] Context variable returned None/empty session ID")
        except Exception as e:
            logger.debug(f"[{tool_name}] Could not get FastMCP session from context: {e}")

        # Fallback to direct FastMCP context if context variable not set
        if not session_id and get_fastmcp_context is not None:
            try:
                fastmcp_ctx = get_fastmcp_context()
                if fastmcp_ctx and hasattr(fastmcp_ctx, "session_id"):
                    session_id = fastmcp_ctx.session_id
                    logger.debug(f"[{tool_name}] Got FastMCP session ID directly: {session_id}")
                else:
                    logger.debug(f"[{tool_name}] FastMCP context exists but no session_id attribute")
            except Exception as e:
                logger.debug(f"[{tool_name}] Could not get FastMCP context directly: {e}")

        # Final fallback: log if we still don't have session_id
        if not session_id:
            logger.warning(f"[{tool_name}] Unable to obtain FastMCP session ID from any source")

    logger.info(
        f"[{tool_name}] Attempting to get authenticated {service_name} service. Email: '{user_google_email}', Session: '{session_id}'"
    )

    # Validate email format
    if not user_google_email or "@" not in user_google_email:
        error_msg = f"Authentication required for {tool_name}. No valid 'user_google_email' provided. Please provide a valid Google email address."
        logger.info(f"[{tool_name}] {error_msg}")
        raise GoogleAuthenticationError(error_msg)

    credentials = await asyncio.to_thread(
        get_credentials,
        user_google_email=user_google_email,
        required_scopes=required_scopes,
        client_secrets_path=CONFIG_CLIENT_SECRETS_PATH,
        session_id=session_id,  # Pass through session context
        override_client_key=override_client_key,
    )

    if not credentials or not credentials.valid:
        logger.warning(f"[{tool_name}] No valid credentials. Email: '{user_google_email}'.")
        logger.info(f"[{tool_name}] Valid email '{user_google_email}' provided, initiating auth flow.")

        credentials, auth_response = await initiate_auth_challenge(
            user_google_email=user_google_email,
            service_name=f"Google {service_name.title()}",
            required_scopes=required_scopes,
            session_id=session_id,
            override_client_key=override_client_key,
        )
        if not credentials or not credentials.valid:
            raise GoogleAuthenticationError(auth_response)

    try:
        service = build(service_name, version, credentials=credentials)
        log_user_email = user_google_email

        # Try to get email from credentials if needed for validation
        if credentials and credentials.id_token:
            try:
                # Decode without verification (just to get email for logging)
                decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
                token_email = decoded_token.get("email")
                if token_email:
                    log_user_email = token_email
                    logger.info(f"[{tool_name}] Token email: {token_email}")
            except Exception as e:
                logger.debug(f"[{tool_name}] Could not decode id_token: {e}")

        logger.info(f"[{tool_name}] Successfully authenticated {service_name} service for user: {log_user_email}")
        return service, log_user_email

    except Exception as e:
        error_msg = f"[{tool_name}] Failed to build {service_name} service: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise GoogleAuthenticationError(error_msg) from e
