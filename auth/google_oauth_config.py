"""
Google Workspace OAuth Configuration.

These credentials are for a Desktop OAuth application.
Per Google's documentation, client secrets for Desktop apps
are not confidential and can be embedded in distributed applications.

Reference: https://developers.google.com/identity/protocols/oauth2/native-app
"""

import os
from typing import Any

# =============================================================================
# Google Workspace OAuth Desktop Application Credentials
# =============================================================================
# GCP Project: annular-aria-484116-r2
# OAuth Type: Desktop Application
# =============================================================================

GOOGLE_OAUTH_CLIENT_ID_EMBEDDED = ""
GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED = ""

# Application metadata
GOOGLE_WORKSPACE_MCP_APP_NAME = "GWS MCP Advanced"
GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR = "~/.config/gws-mcp-advanced"


def get_google_oauth_config() -> dict[str, Any]:
    """
    Get the OAuth configuration for Google Workspace MCP.

    Returns:
        OAuth client configuration in Google's expected format.

    Raises:
        ValueError: If OAuth credentials are not configured.
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", GOOGLE_OAUTH_CLIENT_ID_EMBEDDED)
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED)

    if not client_id or not client_secret:
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables, "
            "or provide embedded credentials in auth/google_oauth_config.py"
        )

    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": os.getenv("GOOGLE_PROJECT_ID", "annular-aria-484116-r2"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }


def get_credentials_directory() -> str:
    """
    Get the directory for storing user credentials.

    Returns:
        Expanded path to credentials directory.
    """
    base_dir = os.getenv("WORKSPACE_MCP_CONFIG_DIR", GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR)
    return os.path.expanduser(base_dir)


def get_sync_map_path() -> str:
    """
    Get the path for the sync map file.

    Returns:
        Expanded path to gdrive_map.json.
    """
    return os.path.join(get_credentials_directory(), "gdrive_map.json")


def is_using_embedded_credentials() -> bool:
    """
    Check if using embedded credentials vs environment override.

    Returns:
        True if using embedded credentials.
    """
    return os.getenv("GOOGLE_OAUTH_CLIENT_ID") is None and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") is None
