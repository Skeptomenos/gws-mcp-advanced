# Make the auth directory a Python package
# Public API exports from canonical locations

from auth.config import (
    GOOGLE_OAUTH_CLIENT_ID_EMBEDDED,
    GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED,
    GOOGLE_WORKSPACE_MCP_APP_NAME,
    GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR,
    USER_GOOGLE_EMAIL,
    WORKSPACE_MCP_BASE_URI,
    WORKSPACE_MCP_PORT,
    get_credentials_directory,
    get_google_oauth_config,
    get_oauth_base_url,
    get_oauth_redirect_uri,
    get_sync_map_path,
    get_transport_mode,
    is_oauth21_enabled,
    is_stateless_mode,
    is_using_embedded_credentials,
    set_transport_mode,
)

__all__ = [
    "get_google_oauth_config",
    "get_credentials_directory",
    "get_oauth_base_url",
    "get_oauth_redirect_uri",
    "get_sync_map_path",
    "get_transport_mode",
    "is_oauth21_enabled",
    "is_stateless_mode",
    "is_using_embedded_credentials",
    "set_transport_mode",
    "GOOGLE_WORKSPACE_MCP_APP_NAME",
    "GOOGLE_OAUTH_CLIENT_ID_EMBEDDED",
    "GOOGLE_OAUTH_CLIENT_SECRET_EMBEDDED",
    "GOOGLE_WORKSPACE_MCP_CREDENTIALS_DIR",
    "USER_GOOGLE_EMAIL",
    "WORKSPACE_MCP_BASE_URI",
    "WORKSPACE_MCP_PORT",
]
