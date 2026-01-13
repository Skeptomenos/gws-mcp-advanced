"""
DEPRECATED: This module has been moved to auth/credential_types/store.py

This shim exists for backward compatibility. Import from auth.credential_types.store instead.
"""

from auth.credential_types.store import (
    CredentialStore,
    LocalDirectoryCredentialStore,
    get_credential_store,
    set_credential_store,
)

__all__ = [
    "CredentialStore",
    "LocalDirectoryCredentialStore",
    "get_credential_store",
    "set_credential_store",
]
