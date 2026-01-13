"""
DEPRECATED: This module has been moved to auth/config.py

This shim exists for backward compatibility. Import from auth.config instead.
"""

from auth.config import (
    OAuthConfig,
    get_allowed_origins,
    get_oauth_base_url,
    get_oauth_config,
    get_oauth_redirect_uri,
    get_redirect_uris,
    get_transport_mode,
    is_external_oauth21_provider,
    is_oauth21_enabled,
    is_oauth_configured,
    is_stateless_mode,
    reload_oauth_config,
    set_transport_mode,
)

__all__ = [
    "OAuthConfig",
    "get_oauth_config",
    "reload_oauth_config",
    "get_oauth_base_url",
    "get_redirect_uris",
    "get_allowed_origins",
    "is_oauth_configured",
    "set_transport_mode",
    "get_transport_mode",
    "is_oauth21_enabled",
    "get_oauth_redirect_uri",
    "is_stateless_mode",
    "is_external_oauth21_provider",
]
