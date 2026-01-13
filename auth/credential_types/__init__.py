"""
Credential types subpackage for Google Workspace MCP.

This package contains:
- types: OAuth type definitions and dataclasses
- store: Credential storage implementations
"""

from auth.credential_types.store import (
    CredentialStore,
    LocalDirectoryCredentialStore,
    get_credential_store,
    set_credential_store,
)
from auth.credential_types.types import OAuth21ServiceRequest, OAuthVersionDetectionParams

__all__ = [
    "OAuth21ServiceRequest",
    "OAuthVersionDetectionParams",
    "CredentialStore",
    "LocalDirectoryCredentialStore",
    "get_credential_store",
    "set_credential_store",
]
