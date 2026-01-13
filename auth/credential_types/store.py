"""
Credential Store API for Google Workspace MCP.

This module provides a standardized interface for credential storage and retrieval,
supporting multiple backends configurable via environment variables.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


class CredentialStore(ABC):
    """Abstract base class for credential storage."""

    @abstractmethod
    def get_credential(self, user_email: str) -> Credentials | None:
        """Get credentials for a user by email."""
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


class LocalDirectoryCredentialStore(CredentialStore):
    """Credential store that uses local JSON files for storage."""

    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            env_dir = os.getenv("GOOGLE_MCP_CREDENTIALS_DIR")
            if env_dir:
                base_dir = env_dir
            else:
                home_dir = os.path.expanduser("~")
                if home_dir and home_dir != "~":
                    base_dir = os.path.join(home_dir, ".config", "google-workspace-mcp", "credentials")
                else:
                    base_dir = os.path.join(os.getcwd(), ".credentials")

        self.base_dir: str = base_dir
        logger.info(f"LocalJsonCredentialStore initialized with base_dir: {base_dir}")

    def _get_credential_path(self, user_email: str) -> str:
        """Get the file path for a user's credentials."""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            logger.info(f"Created credentials directory: {self.base_dir}")
        return os.path.join(self.base_dir, f"{user_email}.json")

    def get_credential(self, user_email: str) -> Credentials | None:
        """Get credentials from local JSON file."""
        creds_path = self._get_credential_path(user_email)

        if not os.path.exists(creds_path):
            logger.debug(f"No credential file found for {user_email} at {creds_path}")
            return None

        try:
            with open(creds_path) as f:
                creds_data = json.load(f)

            expiry = None
            if creds_data.get("expiry"):
                try:
                    expiry = datetime.fromisoformat(creds_data["expiry"])
                    if expiry.tzinfo is not None:
                        expiry = expiry.replace(tzinfo=None)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse expiry time for {user_email}: {e}")

            credentials = Credentials(
                token=creds_data.get("token"),
                refresh_token=creds_data.get("refresh_token"),
                token_uri=creds_data.get("token_uri"),
                client_id=creds_data.get("client_id"),
                client_secret=creds_data.get("client_secret"),
                scopes=creds_data.get("scopes"),
                expiry=expiry,
            )

            logger.debug(f"Loaded credentials for {user_email} from {creds_path}")
            return credentials

        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading credentials for {user_email} from {creds_path}: {e}")
            return None

    def store_credential(self, user_email: str, credentials: Credentials) -> bool:
        """Store credentials to local JSON file."""
        creds_path = self._get_credential_path(user_email)

        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }

        try:
            with open(creds_path, "w") as f:
                json.dump(creds_data, f, indent=2)
            logger.info(f"Stored credentials for {user_email} to {creds_path}")
            return True
        except OSError as e:
            logger.error(f"Error storing credentials for {user_email} to {creds_path}: {e}")
            return False

    def delete_credential(self, user_email: str) -> bool:
        """Delete credential file for a user."""
        creds_path = self._get_credential_path(user_email)

        try:
            if os.path.exists(creds_path):
                os.remove(creds_path)
                logger.info(f"Deleted credentials for {user_email} from {creds_path}")
                return True
            else:
                logger.debug(f"No credential file to delete for {user_email} at {creds_path}")
                return True
        except OSError as e:
            logger.error(f"Error deleting credentials for {user_email} from {creds_path}: {e}")
            return False

    def list_users(self) -> list[str]:
        """List all users with credential files."""
        if not os.path.exists(self.base_dir):
            return []

        users = []
        try:
            for filename in os.listdir(self.base_dir):
                if filename.endswith(".json"):
                    user_email = filename[:-5]
                    users.append(user_email)
            logger.debug(f"Found {len(users)} users with credentials in {self.base_dir}")
        except OSError as e:
            logger.error(f"Error listing credential files in {self.base_dir}: {e}")

        return sorted(users)


_credential_store: CredentialStore | None = None


def get_credential_store() -> CredentialStore:
    """Get the global credential store instance."""
    global _credential_store

    if _credential_store is None:
        _credential_store = LocalDirectoryCredentialStore()
        logger.info(f"Initialized credential store: {type(_credential_store).__name__}")

    return _credential_store


def set_credential_store(store: CredentialStore) -> None:
    """Set the global credential store instance (for testing)."""
    global _credential_store
    _credential_store = store
    logger.info(f"Set credential store: {type(store).__name__}")
