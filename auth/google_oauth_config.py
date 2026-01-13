"""
DEPRECATED: This module has been moved to auth/config.py

This shim exists for backward compatibility. Import from auth.config instead.
"""

from auth.config import (
    GOOGLE_OAUTH_CLIENT_ID_EMBEDDED,
    GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED,
    GOOGLE_WORKSPACE_MCP_APP_NAME,
    GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR,
    get_credentials_directory,
    get_google_oauth_config,
    get_sync_map_path,
    is_using_embedded_credentials,
)

__all__ = [
    "GOOGLE_OAUTH_CLIENT_ID_EMBEDDED",
    "GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED",
    "GOOGLE_WORKSPACE_MCP_APP_NAME",
    "GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR",
    "get_google_oauth_config",
    "get_credentials_directory",
    "get_sync_map_path",
    "is_using_embedded_credentials",
]
