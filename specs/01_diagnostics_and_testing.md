# Spec: Phase 1 - Diagnostic & Test Infrastructure

**Goal**: Understand exactly when/why re-auth happens, create tests to prevent regressions.

## 1.1 Add Diagnostic Logging

Create `auth/diagnostics.py`:

```python
"""
Auth diagnostics for debugging re-authentication issues.
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Enable with AUTH_DIAGNOSTICS=1
DIAGNOSTICS_ENABLED = os.getenv("AUTH_DIAGNOSTICS", "0") == "1"


def log_auth_attempt(
    tool_name: str,
    user_email: str | None,
    session_id: str | None,
    auth_method: str | None,
    oauth_version: str,
    result: str,
    details: dict | None = None,
):
    """Log authentication attempt for debugging."""
    if not DIAGNOSTICS_ENABLED:
        return
    
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "user_email": user_email,
        "session_id": session_id[:8] if session_id else None,
        "auth_method": auth_method,
        "oauth_version": oauth_version,
        "result": result,
        "details": details or {},
    }
    
    logger.info(f"[AUTH_DIAG] {log_entry}")


def log_credential_lookup(
    source: str,
    user_email: str | None,
    session_id: str | None,
    found: bool,
    reason: str | None = None,
):
    """Log credential lookup attempt."""
    if not DIAGNOSTICS_ENABLED:
        return
    
    logger.info(
        f"[CRED_LOOKUP] source={source} email={user_email} "
        f"session={session_id[:8] if session_id else None} "
        f"found={found} reason={reason}"
    )


def log_session_state():
    """Log current session store state."""
    if not DIAGNOSTICS_ENABLED:
        return
    
    from auth.oauth21_session_store import get_oauth21_session_store
    from auth.credential_store import get_credential_store
    
    session_store = get_oauth21_session_store()
    cred_store = get_credential_store()
    
    stats = session_store.get_stats()
    file_users = cred_store.list_users()
    
    logger.info(
        f"[SESSION_STATE] memory_sessions={stats['total_sessions']} "
        f"memory_users={stats['users']} "
        f"file_users={file_users} "
        f"mcp_mappings={stats['mcp_session_mappings']}"
    )
```

## 1.2 Create Auth Integration Tests

Create `tests/integration/test_auth_flow.py`:

```python
"""
Integration tests for authentication flow.

These tests verify the complete auth flow works correctly,
including credential persistence across "restarts".
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from auth.credential_store import LocalDirectoryCredentialStore, get_credential_store
from auth.oauth21_session_store import OAuth21SessionStore, get_oauth21_session_store
from auth.google_auth import get_credentials


class TestCredentialPersistence:
    """Test that credentials persist correctly."""
    
    @pytest.fixture
    def temp_creds_dir(self, tmp_path):
        """Create a temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        return str(creds_dir)
    
    @pytest.fixture
    def sample_credentials(self):
        """Create sample credential data."""
        return {
            "token": "ya29.test_access_token",
            "refresh_token": "1//test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret",
            "scopes": [
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/gmail.readonly",
            ],
            "expiry": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
    
    def test_credentials_survive_store_recreation(self, temp_creds_dir, sample_credentials):
        """Credentials should be retrievable after creating a new store instance."""
        user_email = "test@example.com"
        
        # Store credentials with first instance
        store1 = LocalDirectoryCredentialStore(temp_creds_dir)
        
        # Create mock credentials
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=sample_credentials["token"],
            refresh_token=sample_credentials["refresh_token"],
            token_uri=sample_credentials["token_uri"],
            client_id=sample_credentials["client_id"],
            client_secret=sample_credentials["client_secret"],
            scopes=sample_credentials["scopes"],
        )
        
        store1.store_credential(user_email, creds)
        
        # Create new store instance (simulates restart)
        store2 = LocalDirectoryCredentialStore(temp_creds_dir)
        
        # Should find credentials
        retrieved = store2.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == sample_credentials["token"]
        assert retrieved.refresh_token == sample_credentials["refresh_token"]
    
    def test_session_mapping_lost_on_restart(self):
        """Demonstrate that session mappings are lost on restart."""
        user_email = "test@example.com"
        session_id = "mcp_session_123"
        
        # Store session in first instance
        store1 = OAuth21SessionStore()
        store1.store_session(
            user_email=user_email,
            access_token="test_token",
            mcp_session_id=session_id,
        )
        
        # Verify it exists
        assert store1.get_user_by_mcp_session(session_id) == user_email
        
        # Create new instance (simulates restart)
        store2 = OAuth21SessionStore()
        
        # Session mapping is LOST
        assert store2.get_user_by_mcp_session(session_id) is None
        
        # This is the bug we need to fix!


class TestSessionRecovery:
    """Test session recovery scenarios."""
    
    @pytest.fixture
    def temp_creds_dir(self, tmp_path, monkeypatch):
        """Create and configure temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        monkeypatch.setenv("GOOGLE_MCP_CREDENTIALS_DIR", str(creds_dir))
        return str(creds_dir)
    
    def test_single_user_mode_finds_any_credentials(self, temp_creds_dir, monkeypatch):
        """In single-user mode, any valid credentials should be used."""
        monkeypatch.setenv("MCP_SINGLE_USER_MODE", "1")
        
        # Create credential file
        user_email = "user@example.com"
        creds_file = os.path.join(temp_creds_dir, f"{user_email}.json")
        with open(creds_file, "w") as f:
            json.dump({
                "token": "test_token",
                "refresh_token": "test_refresh",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test_id",
                "client_secret": "test_secret",
                "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
                "expiry": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }, f)
        
        # Should find credentials without needing exact email
        from auth.google_auth import _find_any_credentials
        creds = _find_any_credentials(temp_creds_dir)
        
        assert creds is not None
        assert creds.token == "test_token"
    
    def test_new_session_binds_to_existing_single_user(self, temp_creds_dir):
        """A new session should auto-bind to the only existing user."""
        # This test documents the DESIRED behavior (not yet implemented)
        pass  # TODO: Implement after fix


class TestTokenRefresh:
    """Test token refresh scenarios."""
    
    def test_refreshed_token_updates_all_stores(self):
        """When a token is refreshed, all stores should be updated."""
        # This test documents the DESIRED behavior
        pass  # TODO: Implement
    
    def test_refresh_failure_triggers_reauth_message(self):
        """When refresh fails, user should get clear reauth instructions."""
        pass  # TODO: Implement
```

## 1.3 Create Credential Store Tests

Create `tests/unit/auth/test_credential_store.py` (see Plan for content).

## 1.4 Create Session Store Tests

Create `tests/unit/auth/test_session_store.py` (see Plan for content).
