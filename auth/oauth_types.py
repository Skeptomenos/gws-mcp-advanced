"""
DEPRECATED: This module has been moved to auth/credential_types/types.py

This shim exists for backward compatibility. Import from auth.credential_types.types instead.
"""

from auth.credential_types.types import OAuth21ServiceRequest, OAuthVersionDetectionParams

__all__ = ["OAuth21ServiceRequest", "OAuthVersionDetectionParams"]
