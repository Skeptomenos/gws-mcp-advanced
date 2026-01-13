"""
DEPRECATED: This module has been moved to auth/middleware/session.py

This shim exists for backward compatibility. Import from auth.middleware.session instead.
"""

import warnings

from auth.middleware.session import MCPSessionMiddleware
from auth.oauth21_session_store import (
    SessionContext,
    SessionContextManager,
    extract_session_from_headers,
)

warnings.warn(
    "auth.mcp_session_middleware is deprecated. Use auth.middleware.session instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["MCPSessionMiddleware", "SessionContext", "SessionContextManager", "extract_session_from_headers"]
