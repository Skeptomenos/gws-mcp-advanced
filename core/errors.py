"""
Custom error types for Google Drive operations.

Provides user-friendly error messages and structured error handling.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class GDriveError(Exception):
    """Base class for Google Drive errors."""

    message: str
    details: Any | None = None

    def __str__(self) -> str:
        return self.message


@dataclass
class LinkNotFoundError(GDriveError):
    """Raised when a local file is not linked to a Drive file."""

    local_path: str = ""
    message: str = ""

    def __post_init__(self):
        if not self.message:
            self.message = f"No Drive link found for '{self.local_path}'. Use 'link_local_file' to create a link first."


@dataclass
class LocalFileNotFoundError(GDriveError):
    """Raised when a local file does not exist."""

    local_path: str = ""
    message: str = ""

    def __post_init__(self):
        if not self.message:
            self.message = f"Local file not found: '{self.local_path}'"


@dataclass
class SyncConflictError(GDriveError):
    """Raised when there's a sync conflict between local and remote."""

    message: str = ""
    local_version: int = 0
    remote_version: int = 0
    file_id: str = ""

    def __str__(self) -> str:
        return (
            f"Sync conflict: {self.message}\n"
            f"Local version: {self.local_version}, Remote version: {self.remote_version}\n"
            f"Use force=True to overwrite, or download the remote version first."
        )


@dataclass
class AliasNotFoundError(GDriveError):
    """Raised when a search alias is not found."""

    alias: str = ""
    message: str = ""

    def __post_init__(self):
        if not self.message:
            self.message = f"Alias '{self.alias}' not found. Run a search first to populate aliases."


def handle_http_error(error: Exception, file_id: str | None = None) -> GDriveError:
    """
    Convert Google API HTTP errors to user-friendly GDriveError.
    """
    error_str = str(error)

    if "404" in error_str:
        return GDriveError(message=f"File not found: {file_id or 'unknown'}", details=error)
    elif "403" in error_str:
        return GDriveError(message="Permission denied. You may not have access to this file.", details=error)
    elif "401" in error_str:
        return GDriveError(message="Authentication expired. Please re-authenticate.", details=error)
    elif "429" in error_str:
        return GDriveError(message="Rate limit exceeded. Please wait and try again.", details=error)
    else:
        return GDriveError(message=f"Google API error: {error_str}", details=error)


def format_error(operation: str, error: GDriveError) -> str:
    """Format an error for display to the user."""
    return f"{operation} failed: {error.message}"
