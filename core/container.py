"""
Dependency Injection Container for Google Workspace MCP.

Provides a centralized container for managing dependencies, enabling
testability through mock injection and decoupling components.
"""

import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class CredentialStoreProtocol(Protocol):
    """Protocol for credential storage implementations."""

    def get_credential(self, user_email: str) -> Any | None:
        """Get credentials for a user."""
        ...

    def store_credential(self, user_email: str, credentials: Any) -> bool:
        """Store credentials for a user."""
        ...

    def delete_credential(self, user_email: str) -> bool:
        """Delete credentials for a user."""
        ...

    def list_users(self) -> list[str]:
        """List all users with stored credentials."""
        ...


@runtime_checkable
class SessionStoreProtocol(Protocol):
    """Protocol for session storage implementations."""

    def store_session(self, user_email: str, **kwargs: Any) -> None:
        """Store a session for a user."""
        ...

    def get_credentials(self, user_email: str) -> Any | None:
        """Get credentials by user email."""
        ...

    def get_credentials_by_mcp_session(self, mcp_session_id: str) -> Any | None:
        """Get credentials by MCP session ID."""
        ...

    def get_user_by_mcp_session(self, mcp_session_id: str) -> str | None:
        """Get user email by MCP session ID."""
        ...


@dataclass
class Container:
    """
    Dependency injection container.

    Holds references to the credential store and session store implementations.
    If not provided, defaults to the standard implementations.
    """

    credential_store: CredentialStoreProtocol | None = None
    session_store: SessionStoreProtocol | None = None

    def __post_init__(self) -> None:
        """Initialize with defaults if not provided."""
        if self.credential_store is None:
            from auth.credential_store import LocalDirectoryCredentialStore

            self.credential_store = LocalDirectoryCredentialStore()

        if self.session_store is None:
            from auth.oauth21_session_store import get_oauth21_session_store

            self.session_store = get_oauth21_session_store()


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """
    Get the global container instance.

    Creates a new container with default implementations if none exists.

    Returns:
        The global Container instance.
    """
    global _container
    if _container is None:
        _container = Container()
        logger.debug("Initialized default dependency container")
    return _container


def set_container(container: Container) -> None:
    """
    Set the global container instance.

    Use this for testing to inject mock implementations.

    Args:
        container: The container to use as the global instance.
    """
    global _container
    _container = container
    logger.debug("Set custom dependency container")


def reset_container() -> None:
    """
    Reset the global container.

    Use this between tests to ensure a clean state.
    """
    global _container
    _container = None
    logger.debug("Reset dependency container")
