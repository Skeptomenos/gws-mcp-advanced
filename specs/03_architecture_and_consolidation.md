# Spec: Phase 3, 4, 5 - Architecture & Consolidation

**Goal**: Architecture and consolidation for long-term maintainability.

## 3.1 Incremental P4 (DI + Error Hierarchy)

### Create DI Container

**File**: `core/container.py` (NEW)

```python
"""
Dependency Injection Container for Google Workspace MCP.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Any
import logging

logger = logging.getLogger(__name__)


@runtime_checkable
class CredentialStoreProtocol(Protocol):
    """Protocol for credential storage implementations."""
    
    def get_credential(self, user_email: str) -> Any | None: ...
    def store_credential(self, user_email: str, credentials: Any) -> bool: ...
    def delete_credential(self, user_email: str) -> bool: ...
    def list_users(self) -> list[str]: ...


@runtime_checkable
class SessionStoreProtocol(Protocol):
    """Protocol for session storage implementations."""
    
    def store_session(self, user_email: str, **kwargs) -> None: ...
    def get_credentials(self, user_email: str) -> Any | None: ...
    def get_credentials_by_mcp_session(self, mcp_session_id: str) -> Any | None: ...
    def get_user_by_mcp_session(self, mcp_session_id: str) -> str | None: ...


@dataclass
class Container:
    """Dependency injection container."""
    
    credential_store: CredentialStoreProtocol | None = None
    session_store: SessionStoreProtocol | None = None
    
    def __post_init__(self):
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
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = Container()
        logger.debug("Initialized default dependency container")
    return _container


def set_container(container: Container) -> None:
    """Set the global container instance (for testing)."""
    global _container
    _container = container
    logger.debug("Set custom dependency container")


def reset_container() -> None:
    """Reset the global container (for testing)."""
    global _container
    _container = None
```

### Extend Error Hierarchy

**File**: `core/errors.py`

Add auth-specific errors:

```python
# Add to existing file:

class CredentialsNotFoundError(AuthenticationError):
    """Raised when no credentials are found for a user."""
    
    def __init__(self, user_email: str):
        super().__init__(
            f"No credentials found for user: {user_email}. "
            "Please authenticate first using start_google_auth."
        )
        self.user_email = user_email


class SessionBindingError(AuthenticationError):
    """Raised when session binding fails."""
    
    def __init__(self, session_id: str, reason: str):
        super().__init__(f"Session binding failed for {session_id}: {reason}")
        self.session_id = session_id
        self.reason = reason


class TokenRefreshError(AuthenticationError):
    """Raised when token refresh fails."""
    
    def __init__(self, user_email: str, reason: str):
        super().__init__(
            f"Failed to refresh token for {user_email}: {reason}. "
            "Please re-authenticate using start_google_auth."
        )
        self.user_email = user_email
        self.reason = reason


class ScopeMismatchError(AuthenticationError):
    """Raised when credentials lack required scopes."""
    
    def __init__(self, required: list[str], available: list[str]):
        missing = set(required) - set(available)
        super().__init__(
            f"Missing required OAuth scopes: {', '.join(missing)}. "
            "Please re-authenticate with the required permissions."
        )
        self.required_scopes = required
        self.available_scopes = available
        self.missing_scopes = list(missing)
```

## 4.1 Auth Consolidation Preparation

### Create Unified Auth Interface

**File**: `auth/interfaces.py` (NEW)

```python
"""
Abstract interfaces for authentication components.
"""

from abc import ABC, abstractmethod
from typing import Any
from google.oauth2.credentials import Credentials


class BaseCredentialStore(ABC):
    """Abstract base for credential storage."""
    
    @abstractmethod
    def get_credential(self, user_email: str) -> Credentials | None:
        """Get credentials for a user."""
        pass
    
    @abstractmethod
    def store_credential(self, user_email: str, credentials: Credentials) -> bool:
        """Store credentials for a user."""
        pass
    
    @abstractmethod
    def delete_credential(self, user_email: str) -> bool:
        """Delete credentials for a user."""
        pass
    
    @abstractmethod
    def list_users(self) -> list[str]:
        """List all users with stored credentials."""
        pass


class BaseSessionStore(ABC):
    """Abstract base for session management."""
    
    @abstractmethod
    def store_session(
        self,
        user_email: str,
        access_token: str,
        refresh_token: str | None = None,
        mcp_session_id: str | None = None,
        **kwargs,
    ) -> None:
        """Store a session."""
        pass
    
    @abstractmethod
    def get_credentials(self, user_email: str) -> Credentials | None:
        """Get credentials by user email."""
        pass
    
    @abstractmethod
    def get_credentials_by_mcp_session(self, mcp_session_id: str) -> Credentials | None:
        """Get credentials by MCP session ID."""
        pass
    
    @abstractmethod
    def get_user_by_mcp_session(self, mcp_session_id: str) -> str | None:
        """Get user email by MCP session ID."""
        pass
    
    @abstractmethod
    def has_session(self, user_email: str) -> bool:
        """Check if user has an active session."""
        pass


class BaseAuthProvider(ABC):
    """Abstract base for OAuth providers."""
    
    @abstractmethod
    async def start_auth_flow(
        self,
        user_email: str | None,
        service_name: str,
        redirect_uri: str,
    ) -> str:
        """Start OAuth flow and return auth URL."""
        pass
    
    @abstractmethod
    async def handle_callback(
        self,
        authorization_response: str,
        redirect_uri: str,
        session_id: str | None = None,
    ) -> tuple[str, Credentials]:
        """Handle OAuth callback and return (user_email, credentials)."""
        pass
    
    @abstractmethod
    def get_credentials(
        self,
        user_email: str | None,
        required_scopes: list[str],
        session_id: str | None = None,
    ) -> Credentials | None:
        """Get valid credentials for a user."""
        pass
```

## 5. Full Auth Consolidation

### Target Structure

```
auth/
├── __init__.py                    # Public API exports
├── config.py                      # MERGE: oauth_config.py + google_oauth_config.py
├── scopes.py                      # KEEP: Already clean
├── decorators.py                  # RENAME: service_decorator.py
├── interfaces.py                  # NEW: Abstract base classes
├── errors.py                      # MOVE: Auth-specific errors from core/errors.py
├── credentials/
│   ├── __init__.py
│   ├── store.py                   # KEEP: credential_store.py
│   ├── session.py                 # EXTRACT: Session management from oauth21_session_store.py
│   └── types.py                   # MERGE: oauth_types.py + dataclasses
├── providers/
│   ├── __init__.py
│   ├── google.py                  # EXTRACT: OAuth flow from google_auth.py
│   └── external.py                # RENAME: external_oauth_provider.py
├── middleware/
│   ├── __init__.py
│   ├── auth_info.py               # RENAME: auth_info_middleware.py
│   └── session.py                 # RENAME: mcp_session_middleware.py
└── server/
    ├── __init__.py
    └── callback.py                # RENAME: oauth_callback_server.py
```
