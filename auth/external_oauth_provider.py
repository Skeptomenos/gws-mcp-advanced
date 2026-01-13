"""
DEPRECATED: This module has been moved to auth/providers/external.py

This shim exists for backward compatibility. Import from auth.providers.external instead.
"""

import warnings

from auth.providers.external import ExternalOAuthProvider

warnings.warn(
    "auth.external_oauth_provider is deprecated. Use auth.providers.external instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ExternalOAuthProvider"]
