"""
Abstract interfaces for authentication components.

These interfaces define the contracts for credential storage, session management,
and OAuth providers. They enable dependency injection and testability.
"""

from abc import ABC, abstractmethod

from google.oauth2.credentials import Credentials


class BaseCredentialStore(ABC):
    """Abstract base for credential storage.

    Implementations handle persistent storage of OAuth credentials,
    typically to disk or a database.
    """

    @abstractmethod
    def get_credential(self, user_email: str) -> Credentials | None:
        """Get credentials for a user.

        Args:
            user_email: The user's email address.

        Returns:
            Credentials if found, None otherwise.
        """
        pass

    @abstractmethod
    def store_credential(self, user_email: str, credentials: Credentials) -> bool:
        """Store credentials for a user.

        Args:
            user_email: The user's email address.
            credentials: The OAuth credentials to store.

        Returns:
            True if stored successfully, False otherwise.
        """
        pass

    @abstractmethod
    def delete_credential(self, user_email: str) -> bool:
        """Delete credentials for a user.

        Args:
            user_email: The user's email address.

        Returns:
            True if deleted successfully, False otherwise.
        """
        pass

    @abstractmethod
    def list_users(self) -> list[str]:
        """List all users with stored credentials.

        Returns:
            List of user email addresses.
        """
        pass


class BaseSessionStore(ABC):
    """Abstract base for session management.

    Implementations handle in-memory session state with optional
    persistence for recovery across restarts.
    """

    @abstractmethod
    def store_session(
        self,
        user_email: str,
        access_token: str,
        refresh_token: str | None = None,
        mcp_session_id: str | None = None,
        **kwargs,
    ) -> None:
        """Store a session.

        Args:
            user_email: The user's email address.
            access_token: The OAuth access token.
            refresh_token: The OAuth refresh token (optional).
            mcp_session_id: The MCP session ID to bind (optional).
            **kwargs: Additional session metadata.
        """
        pass

    @abstractmethod
    def get_credentials(self, user_email: str) -> Credentials | None:
        """Get credentials by user email.

        Args:
            user_email: The user's email address.

        Returns:
            Credentials if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_credentials_by_mcp_session(self, mcp_session_id: str) -> Credentials | None:
        """Get credentials by MCP session ID.

        Args:
            mcp_session_id: The MCP session identifier.

        Returns:
            Credentials if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_user_by_mcp_session(self, mcp_session_id: str) -> str | None:
        """Get user email by MCP session ID.

        Args:
            mcp_session_id: The MCP session identifier.

        Returns:
            User email if found, None otherwise.
        """
        pass

    @abstractmethod
    def has_session(self, user_email: str) -> bool:
        """Check if user has an active session.

        Args:
            user_email: The user's email address.

        Returns:
            True if session exists, False otherwise.
        """
        pass


class BaseAuthProvider(ABC):
    """Abstract base for OAuth providers.

    Implementations handle the OAuth flow for specific providers
    (e.g., Google, Microsoft).
    """

    @abstractmethod
    async def start_auth_flow(
        self,
        user_email: str | None,
        service_name: str,
        redirect_uri: str,
    ) -> str:
        """Start OAuth flow and return auth URL.

        Args:
            user_email: The user's email address (optional hint).
            service_name: Display name for the service.
            redirect_uri: The OAuth callback URI.

        Returns:
            The authorization URL for the user to visit.
        """
        pass

    @abstractmethod
    async def handle_callback(
        self,
        authorization_response: str,
        redirect_uri: str,
        session_id: str | None = None,
    ) -> tuple[str, Credentials]:
        """Handle OAuth callback and return (user_email, credentials).

        Args:
            authorization_response: The full callback URL with auth code.
            redirect_uri: The OAuth callback URI used in the flow.
            session_id: The MCP session ID to bind (optional).

        Returns:
            Tuple of (user_email, credentials).
        """
        pass

    @abstractmethod
    def get_credentials(
        self,
        user_email: str | None,
        required_scopes: list[str],
        session_id: str | None = None,
    ) -> Credentials | None:
        """Get valid credentials for a user.

        Args:
            user_email: The user's email address.
            required_scopes: List of required OAuth scopes.
            session_id: The MCP session ID (optional).

        Returns:
            Valid credentials if available, None otherwise.
        """
        pass
