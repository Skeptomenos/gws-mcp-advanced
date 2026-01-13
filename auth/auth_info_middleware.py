"""
DEPRECATED: This module has been moved to auth/middleware/auth_info.py

This shim exists for backward compatibility. Import from auth.middleware.auth_info instead.
"""

import warnings

from auth.middleware.auth_info import AuthInfoMiddleware

warnings.warn(
    "auth.auth_info_middleware is deprecated. Use auth.middleware.auth_info instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AuthInfoMiddleware"]
