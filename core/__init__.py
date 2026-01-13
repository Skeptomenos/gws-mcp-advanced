"""Core utilities for Google Workspace MCP."""

from core.errors import (
    AliasNotFoundError,
    APIError,
    AuthenticationError,
    CredentialsExpiredError,
    CredentialsNotFoundError,
    GDriveError,
    InsufficientScopesError,
    LinkNotFoundError,
    LocalFileNotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
    ServiceConfigurationError,
    SyncConflictError,
    ValidationError,
    WorkspaceMCPError,
)
from core.managers import SearchManager, SyncManager, search_manager, sync_manager
from core.utils import TransientNetworkError, UserInputError, handle_http_errors

__all__ = [
    "WorkspaceMCPError",
    "AuthenticationError",
    "CredentialsNotFoundError",
    "CredentialsExpiredError",
    "InsufficientScopesError",
    "ServiceConfigurationError",
    "ValidationError",
    "APIError",
    "ResourceNotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "GDriveError",
    "LinkNotFoundError",
    "LocalFileNotFoundError",
    "SyncConflictError",
    "AliasNotFoundError",
    "SearchManager",
    "SyncManager",
    "search_manager",
    "sync_manager",
    "handle_http_errors",
    "TransientNetworkError",
    "UserInputError",
]
