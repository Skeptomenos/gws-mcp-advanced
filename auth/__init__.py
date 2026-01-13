# Make the auth directory a Python package

from auth.google_oauth_config import (
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
    "get_google_oauth_config",
    "get_credentials_directory",
    "get_sync_map_path",
    "is_using_embedded_credentials",
    "GOOGLE_WORKSPACE_MCP_APP_NAME",
    "GOOGLE_OAUTH_CLIENT_ID_EMBEDDED",
    "GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED",
    "GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR",
]
