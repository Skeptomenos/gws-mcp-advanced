"""
Auth diagnostics for debugging re-authentication issues.

Enable with AUTH_DIAGNOSTICS=1 environment variable.
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Enable with AUTH_DIAGNOSTICS=1
DIAGNOSTICS_ENABLED = os.getenv("AUTH_DIAGNOSTICS", "0") == "1"


def log_auth_attempt(
    tool_name: str,
    user_email: str | None,
    session_id: str | None,
    auth_method: str | None,
    oauth_version: str,
    result: str,
    details: dict | None = None,
) -> None:
    """
    Log authentication attempt for debugging.

    Args:
        tool_name: Name of the tool being accessed
        user_email: User's email address (if known)
        session_id: Session identifier (if available)
        auth_method: Authentication method used (e.g., "oauth21", "file", "session")
        oauth_version: OAuth version ("2.0" or "2.1")
        result: Result of the auth attempt ("success", "failure", "refresh_needed")
        details: Additional context for debugging
    """
    if not DIAGNOSTICS_ENABLED:
        return

    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "user_email": user_email,
        "session_id": session_id[:8] if session_id else None,
        "auth_method": auth_method,
        "oauth_version": oauth_version,
        "result": result,
        "details": details or {},
    }

    logger.info(f"[AUTH_DIAG] {log_entry}")


def log_credential_lookup(
    source: str,
    user_email: str | None,
    session_id: str | None,
    found: bool,
    reason: str | None = None,
) -> None:
    """
    Log credential lookup attempt.

    Args:
        source: Where credentials were looked up ("session_store", "file_store", "mcp_session")
        user_email: User's email address (if known)
        session_id: Session identifier (if available)
        found: Whether credentials were found
        reason: Additional context (e.g., "expired", "missing_refresh_token")
    """
    if not DIAGNOSTICS_ENABLED:
        return

    logger.info(
        f"[CRED_LOOKUP] source={source} email={user_email} "
        f"session={session_id[:8] if session_id else None} "
        f"found={found} reason={reason}"
    )


def log_session_state() -> None:
    """
    Log current session store state.

    This provides a snapshot of all active sessions and credential mappings
    for debugging session persistence issues.
    """
    if not DIAGNOSTICS_ENABLED:
        return

    # Import here to avoid circular imports
    from auth.credential_store import get_credential_store
    from auth.oauth21_session_store import get_oauth21_session_store

    session_store = get_oauth21_session_store()
    cred_store = get_credential_store()

    stats = session_store.get_stats()
    file_users = cred_store.list_users()

    logger.info(
        f"[SESSION_STATE] memory_sessions={stats['total_sessions']} "
        f"memory_users={stats['users']} "
        f"file_users={file_users} "
        f"mcp_mappings={stats['mcp_session_mappings']}"
    )


def log_token_refresh(
    user_email: str,
    success: bool,
    error: str | None = None,
    stores_updated: list[str] | None = None,
) -> None:
    """
    Log token refresh attempt.

    Args:
        user_email: User's email address
        success: Whether the refresh succeeded
        error: Error message if refresh failed
        stores_updated: List of stores that were updated (e.g., ["file", "session"])
    """
    if not DIAGNOSTICS_ENABLED:
        return

    logger.info(
        f"[TOKEN_REFRESH] email={user_email} success={success} error={error} stores_updated={stores_updated or []}"
    )


def log_session_binding(
    mcp_session_id: str,
    user_email: str,
    action: str,
    success: bool,
    reason: str | None = None,
) -> None:
    """
    Log session binding operations.

    Args:
        mcp_session_id: MCP session identifier
        user_email: User's email address
        action: Action performed ("bind", "lookup", "auto_recover")
        success: Whether the operation succeeded
        reason: Additional context
    """
    if not DIAGNOSTICS_ENABLED:
        return

    logger.info(
        f"[SESSION_BIND] mcp_session={mcp_session_id[:8] if mcp_session_id else None} "
        f"email={user_email} action={action} success={success} reason={reason}"
    )
