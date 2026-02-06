"""Core utilities for Google Workspace MCP."""

from core.attachment_storage import get_attachment_storage, get_attachment_url
from core.context import get_fastmcp_session_id, set_fastmcp_session_id
from core.errors import (
    AliasNotFoundError,
    APIError,
    AuthenticationError,
    CredentialsExpiredError,
    CredentialsNotFoundError,
    GDriveError,
    GoogleAuthenticationError,
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
    format_error,
    handle_http_error,
)
from core.managers import SearchManager, SyncManager, search_manager, sync_manager
from core.server import get_auth_provider, server
from core.types import GoogleDriveService
from core.utils import (
    TransientNetworkError,
    UserInputError,
    extract_office_xml_text,
    handle_http_errors,
    validate_path_within_base,
)

__all__ = [
    "AliasNotFoundError",
    "APIError",
    "AuthenticationError",
    "CredentialsExpiredError",
    "CredentialsNotFoundError",
    "extract_office_xml_text",
    "format_error",
    "GDriveError",
    "get_attachment_storage",
    "get_attachment_url",
    "get_auth_provider",
    "get_fastmcp_session_id",
    "GoogleAuthenticationError",
    "GoogleDriveService",
    "handle_http_error",
    "handle_http_errors",
    "InsufficientScopesError",
    "LinkNotFoundError",
    "LocalFileNotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "ResourceNotFoundError",
    "search_manager",
    "SearchManager",
    "server",
    "ServiceConfigurationError",
    "set_fastmcp_session_id",
    "sync_manager",
    "SyncConflictError",
    "SyncManager",
    "TransientNetworkError",
    "UserInputError",
    "validate_path_within_base",
    "ValidationError",
    "WorkspaceMCPError",
]
