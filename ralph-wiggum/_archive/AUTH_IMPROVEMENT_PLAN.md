# Auth Improvement Plan: Fixing Re-authentication Issues

> **Created**: 2026-01-13  
> **Goal**: Eliminate constant re-authentication prompts and establish a solid foundation for auth consolidation  
> **Approach**: Test-first, incremental improvements, then architectural cleanup

---

## Project Context & History

**Status as of Session 4**:
- **Completed**: P0 (Critical), P1 (High), P2 (Medium), and P3 (Low) issues from the original mitigation plan.
- **Metrics**: 43 tests passing, linting clean, ~1M+ lines analyzed.
- **Current Focus**: P4 (Architectural) issues, specifically the Critical Authentication Flaw (RC-1 to RC-5) causing workflow-blocking re-auth prompts.

**Previous Work**:
- Fixed blocking `execute()` calls in async functions.
- Removed placeholder credentials.
- Standardized error handling with custom exceptions.
- Added type safety and removed `type: ignore` comments.
- Fixed 50+ identified code quality issues.

---

## Table of Contents

1. [Problem Analysis](#1-problem-analysis)
2. [Root Causes](#2-root-causes)
3. [Phase 1: Diagnostic & Test Infrastructure](#3-phase-1-diagnostic--test-infrastructure)
4. [Phase 2: Quick Wins (Fix Immediate Pain)](#4-phase-2-quick-wins-fix-immediate-pain)
5. [Phase 3: Incremental P4 (DI + Error Hierarchy)](#5-phase-3-incremental-p4-di--error-hierarchy)
6. [Phase 4: Auth Consolidation Preparation](#6-phase-4-auth-consolidation-preparation)
7. [Phase 5: Full Auth Consolidation](#7-phase-5-full-auth-consolidation)
8. [Verification Checklist](#8-verification-checklist)

---

## 1. Problem Analysis

### Symptoms
- Constantly asked to re-authenticate
- Authentication doesn't persist across sessions
- Workflow interruptions when credentials should still be valid

### Current Auth Architecture (14 files, ~3500 lines)

```
auth/
├── credential_store.py          # File-based credential storage (LocalDirectoryCredentialStore)
├── oauth21_session_store.py     # In-memory session store (OAuth21SessionStore) 
├── google_auth.py               # Core OAuth flow + get_credentials()
├── service_decorator.py         # @require_google_service decorator
├── google_oauth_config.py       # Embedded OAuth credentials
├── oauth_config.py              # OAuth mode detection
├── auth_info_middleware.py      # JWT/token extraction
├── mcp_session_middleware.py    # MCP session context
├── external_oauth_provider.py   # External token validation
├── oauth_callback_server.py     # Local OAuth callback
├── oauth_responses.py           # Response formatting
├── oauth_types.py               # Type definitions
├── scopes.py                    # Scope definitions
└── __init__.py                  # Exports
```

### Data Flow (Current)

```
Tool Call
    │
    ▼
@require_google_service
    │
    ├─► _get_auth_context() ─► FastMCP context (session_id, authenticated_user)
    │
    ├─► _detect_oauth_version() ─► OAuth 2.0 or 2.1?
    │
    └─► _authenticate_service()
            │
            ├─► OAuth 2.1: get_authenticated_google_service_oauth21()
            │       │
            │       ├─► get_auth_provider() + get_access_token()
            │       │       └─► ensure_session_from_access_token()
            │       │
            │       └─► OAuth21SessionStore.get_credentials_with_validation()
            │
            └─► OAuth 2.0: get_authenticated_google_service()
                    │
                    └─► get_credentials()
                            │
                            ├─► OAuth21SessionStore (by session_id)
                            ├─► load_credentials_from_session()
                            ├─► LocalDirectoryCredentialStore (by email)
                            └─► Refresh if expired
```

---

## 2. Root Causes

### RC-1: Session Store is In-Memory Only

**Location**: `auth/oauth21_session_store.py`

```python
class OAuth21SessionStore:
    def __init__(self):
        self._sessions: dict[str, dict[str, Any]] = {}  # IN-MEMORY!
        self._mcp_session_mapping: dict[str, str] = {}  # IN-MEMORY!
```

**Impact**: When the MCP server restarts (which happens frequently), all session mappings are lost. The file-based `LocalDirectoryCredentialStore` has credentials, but the session-to-user mapping is gone.

**Evidence**: OAuth states ARE persisted (`_save_oauth_states_to_disk`), but sessions are NOT.

### RC-2: Session ID Mismatch Between Runs

**Location**: `auth/google_auth.py:504-546`

The `get_credentials()` function tries to find credentials by `session_id` first:

```python
if session_id:
    store = get_oauth21_session_store()
    credentials = store.get_credentials_by_mcp_session(session_id)
```

But after a restart, `_mcp_session_mapping` is empty, so this always returns `None`.

### RC-3: Credential Store Lookup Requires Exact Email

**Location**: `auth/google_auth.py:582-598`

```python
if not credentials and user_google_email:
    if not is_stateless_mode():
        store = get_credential_store()
        credentials = store.get_credential(user_google_email)
```

This works, BUT only if `user_google_email` is provided AND matches exactly. If the MCP client doesn't send the email (or sends a different format), credentials aren't found.

### RC-4: Token Refresh Doesn't Update All Stores

**Location**: `auth/google_auth.py:627-659`

When tokens are refreshed, they're saved to:
1. `LocalDirectoryCredentialStore` (file)
2. `OAuth21SessionStore` (memory)
3. Session cache

But if the session mapping was lost (RC-1), the refreshed token isn't properly associated with the new session.

### RC-5: No Credential Recovery on Session Mismatch

When a new session starts and can't find credentials by session_id, there's no fallback to:
1. Check if there's only one user with credentials (single-user optimization)
2. Prompt for email and then look up credentials
3. Automatically bind the new session to existing credentials

---

## 3. Phase 1: Diagnostic & Test Infrastructure

**Goal**: Understand exactly when/why re-auth happens, create tests to prevent regressions.

**Effort**: 2-3 hours

### Step 1.1: Add Diagnostic Logging

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

### Step 1.2: Create Auth Integration Tests

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

### Step 1.3: Create Credential Store Tests

Create `tests/unit/auth/test_credential_store.py`:

```python
"""Tests for credential store implementations."""

import json
import os
from datetime import datetime, timedelta

import pytest
from google.oauth2.credentials import Credentials

from auth.credential_store import (
    CredentialStore,
    LocalDirectoryCredentialStore,
    get_credential_store,
    set_credential_store,
)


class TestLocalDirectoryCredentialStore:
    """Test LocalDirectoryCredentialStore implementation."""
    
    @pytest.fixture
    def temp_creds_dir(self, tmp_path):
        """Create a temporary credentials directory."""
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        return str(creds_dir)
    
    @pytest.fixture
    def sample_credentials(self):
        """Create sample Google credentials."""
        return Credentials(
            token="ya29.test_access_token",
            refresh_token="1//test_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client_id.apps.googleusercontent.com",
            client_secret="test_client_secret",
            scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/gmail.readonly",
            ],
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
    
    def test_store_and_retrieve_credentials(self, temp_creds_dir, sample_credentials):
        """Test storing and retrieving credentials."""
        store = LocalDirectoryCredentialStore(temp_creds_dir)
        user_email = "test@example.com"
        
        # Store
        result = store.store_credential(user_email, sample_credentials)
        assert result is True
        
        # Verify file exists
        creds_path = os.path.join(temp_creds_dir, f"{user_email}.json")
        assert os.path.exists(creds_path)
        
        # Retrieve
        retrieved = store.get_credential(user_email)
        assert retrieved is not None
        assert retrieved.token == sample_credentials.token
        assert retrieved.refresh_token == sample_credentials.refresh_token
        assert retrieved.scopes == sample_credentials.scopes
    
    def test_get_nonexistent_returns_none(self, temp_creds_dir):
        """Getting nonexistent credentials should return None."""
        store = LocalDirectoryCredentialStore(temp_creds_dir)
        result = store.get_credential("nonexistent@example.com")
        assert result is None
    
    def test_delete_credentials(self, temp_creds_dir, sample_credentials):
        """Test deleting credentials."""
        store = LocalDirectoryCredentialStore(temp_creds_dir)
        user_email = "test@example.com"
        
        # Store first
        store.store_credential(user_email, sample_credentials)
        
        # Delete
        result = store.delete_credential(user_email)
        assert result is True
        
        # Verify gone
        assert store.get_credential(user_email) is None
    
    def test_list_users(self, temp_creds_dir, sample_credentials):
        """Test listing users with credentials."""
        store = LocalDirectoryCredentialStore(temp_creds_dir)
        
        # Store for multiple users
        store.store_credential("user1@example.com", sample_credentials)
        store.store_credential("user2@example.com", sample_credentials)
        
        users = store.list_users()
        assert len(users) == 2
        assert "user1@example.com" in users
        assert "user2@example.com" in users
    
    def test_expiry_preserved_correctly(self, temp_creds_dir):
        """Test that expiry time is preserved through store/retrieve cycle."""
        store = LocalDirectoryCredentialStore(temp_creds_dir)
        user_email = "test@example.com"
        
        # Create credentials with specific expiry
        expiry = datetime.utcnow() + timedelta(hours=2)
        creds = Credentials(
            token="test_token",
            refresh_token="test_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_id",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
            expiry=expiry,
        )
        
        store.store_credential(user_email, creds)
        retrieved = store.get_credential(user_email)
        
        # Expiry should be close (within 1 second due to serialization)
        assert retrieved.expiry is not None
        delta = abs((retrieved.expiry - expiry).total_seconds())
        assert delta < 1
```

### Step 1.4: Create Session Store Tests

Create `tests/unit/auth/test_session_store.py`:

```python
"""Tests for OAuth21SessionStore."""

import pytest
from datetime import datetime, timedelta, timezone

from auth.oauth21_session_store import (
    OAuth21SessionStore,
    SessionContext,
    get_oauth21_session_store,
)


class TestOAuth21SessionStore:
    """Test OAuth21SessionStore implementation."""
    
    @pytest.fixture
    def store(self):
        """Create a fresh session store."""
        return OAuth21SessionStore()
    
    def test_store_and_retrieve_session(self, store):
        """Test storing and retrieving a session."""
        user_email = "test@example.com"
        
        store.store_session(
            user_email=user_email,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        
        credentials = store.get_credentials(user_email)
        assert credentials is not None
        assert credentials.token == "test_access_token"
        assert credentials.refresh_token == "test_refresh_token"
    
    def test_mcp_session_mapping(self, store):
        """Test MCP session ID to user mapping."""
        user_email = "test@example.com"
        mcp_session_id = "mcp_session_123"
        
        store.store_session(
            user_email=user_email,
            access_token="test_token",
            mcp_session_id=mcp_session_id,
        )
        
        # Should find user by MCP session
        found_email = store.get_user_by_mcp_session(mcp_session_id)
        assert found_email == user_email
        
        # Should get credentials by MCP session
        credentials = store.get_credentials_by_mcp_session(mcp_session_id)
        assert credentials is not None
        assert credentials.token == "test_token"
    
    def test_session_binding_immutable(self, store):
        """Test that session binding cannot be changed."""
        mcp_session_id = "mcp_session_123"
        
        # First binding
        store.store_session(
            user_email="user1@example.com",
            access_token="token1",
            mcp_session_id=mcp_session_id,
        )
        
        # Attempt to rebind to different user should fail
        with pytest.raises(ValueError, match="already bound"):
            store.store_session(
                user_email="user2@example.com",
                access_token="token2",
                mcp_session_id=mcp_session_id,
            )
    
    def test_oauth_state_persistence(self, store, tmp_path, monkeypatch):
        """Test that OAuth states are persisted to disk."""
        # Point to temp directory
        states_file = tmp_path / "oauth_states.json"
        monkeypatch.setattr(store, "_states_file_path", str(states_file))
        
        # Store a state
        store.store_oauth_state("test_state_123", session_id="session_456")
        
        # Verify file was created
        assert states_file.exists()
        
        # Create new store instance and verify state is loaded
        store2 = OAuth21SessionStore()
        monkeypatch.setattr(store2, "_states_file_path", str(states_file))
        store2._load_oauth_states_from_disk()
        
        # State should be found (not consumed yet)
        assert "test_state_123" in store2._oauth_states
    
    def test_get_single_user_email(self, store):
        """Test getting single user when only one session exists."""
        # No sessions
        assert store.get_single_user_email() is None
        
        # One session
        store.store_session(
            user_email="only@example.com",
            access_token="token",
        )
        assert store.get_single_user_email() == "only@example.com"
        
        # Two sessions
        store.store_session(
            user_email="another@example.com",
            access_token="token2",
        )
        assert store.get_single_user_email() is None
    
    def test_credentials_with_validation_blocks_cross_access(self, store):
        """Test that validation prevents cross-account access."""
        # Store session for user1
        store.store_session(
            user_email="user1@example.com",
            access_token="token1",
            mcp_session_id="session_1",
        )
        
        # Session 1 should NOT be able to access user2's credentials
        credentials = store.get_credentials_with_validation(
            requested_user_email="user2@example.com",
            session_id="session_1",
        )
        assert credentials is None


class TestSessionContext:
    """Test SessionContext dataclass."""
    
    def test_session_context_repr(self):
        """Test SessionContext string representation."""
        ctx = SessionContext(
            session_id="test_session",
            user_id="test_user",
            issuer="https://accounts.google.com",
        )
        
        repr_str = repr(ctx)
        assert "test_session" in repr_str
        assert "test_user" in repr_str
```

---

## 4. Phase 2: Quick Wins (Fix Immediate Pain)

**Goal**: Fix the most impactful issues with minimal risk.

**Effort**: 2-3 hours

### Step 2.1: Persist Session Mappings to Disk

**File**: `auth/oauth21_session_store.py`

Add session persistence alongside OAuth state persistence:

```python
def _get_sessions_file_path(self) -> str:
    """Get the file path for persisting session mappings."""
    base_dir = os.path.dirname(self._states_file_path)
    return os.path.join(base_dir, "session_mappings.json")

def _load_session_mappings_from_disk(self):
    """Load persisted session mappings on initialization."""
    sessions_file = self._get_sessions_file_path()
    try:
        if not os.path.exists(sessions_file):
            logger.debug("No persisted session mappings file found")
            return
        
        with open(sessions_file) as f:
            data = json.load(f)
        
        # Load MCP session mappings
        self._mcp_session_mapping = data.get("mcp_session_mapping", {})
        self._session_auth_binding = data.get("session_auth_binding", {})
        
        # Load session data (but not access tokens - those should come from credential store)
        for user_email, session_info in data.get("sessions", {}).items():
            # Only restore metadata, not tokens
            if user_email not in self._sessions:
                self._sessions[user_email] = {
                    "session_id": session_info.get("session_id"),
                    "mcp_session_id": session_info.get("mcp_session_id"),
                    "issuer": session_info.get("issuer"),
                    "scopes": session_info.get("scopes", []),
                }
        
        logger.info(
            f"Loaded session mappings: {len(self._mcp_session_mapping)} MCP sessions, "
            f"{len(self._session_auth_binding)} auth bindings"
        )
    except Exception as e:
        logger.warning(f"Failed to load session mappings: {e}")

def _save_session_mappings_to_disk(self):
    """Persist session mappings to disk."""
    sessions_file = self._get_sessions_file_path()
    try:
        data = {
            "mcp_session_mapping": self._mcp_session_mapping,
            "session_auth_binding": self._session_auth_binding,
            "sessions": {
                email: {
                    "session_id": info.get("session_id"),
                    "mcp_session_id": info.get("mcp_session_id"),
                    "issuer": info.get("issuer"),
                    "scopes": info.get("scopes", []),
                }
                for email, info in self._sessions.items()
            },
        }
        
        with open(sessions_file, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Persisted session mappings to {sessions_file}")
    except Exception as e:
        logger.error(f"Failed to persist session mappings: {e}")
```

Update `__init__` and `store_session`:

```python
def __init__(self):
    # ... existing code ...
    self._load_session_mappings_from_disk()  # Add this

def store_session(self, ...):
    # ... existing code ...
    self._save_session_mappings_to_disk()  # Add at end
```

### Step 2.2: Add Single-User Auto-Recovery

**File**: `auth/google_auth.py`

Enhance `get_credentials()` to auto-recover when there's only one user:

```python
def get_credentials(
    user_google_email: str | None,
    required_scopes: list[str],
    client_secrets_path: str | None = None,
    credentials_base_dir: str = DEFAULT_CREDENTIALS_DIR,
    session_id: str | None = None,
) -> Credentials | None:
    """
    Retrieves stored credentials with improved recovery logic.
    """
    # ... existing OAuth 2.1 session store check ...
    
    # NEW: Auto-recovery for single-user scenarios
    if not credentials and session_id:
        store = get_oauth21_session_store()
        cred_store = get_credential_store()
        
        # Check if there's only one user with credentials
        file_users = cred_store.list_users()
        if len(file_users) == 1:
            single_user = file_users[0]
            logger.info(
                f"[get_credentials] Single user detected ({single_user}), "
                f"auto-binding session {session_id}"
            )
            
            # Load credentials from file
            credentials = cred_store.get_credential(single_user)
            if credentials:
                # Bind this session to the user
                try:
                    store.store_session(
                        user_email=single_user,
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        token_uri=credentials.token_uri,
                        client_id=credentials.client_id,
                        client_secret=credentials.client_secret,
                        scopes=credentials.scopes,
                        expiry=credentials.expiry,
                        mcp_session_id=session_id,
                    )
                    user_google_email = single_user
                except ValueError as e:
                    # Session already bound to different user
                    logger.warning(f"Could not auto-bind session: {e}")
    
    # ... rest of existing code ...
```

### Step 2.3: Improve Token Refresh Synchronization

**File**: `auth/google_auth.py`

Ensure refreshed tokens update the credential store:

```python
# In get_credentials(), after successful refresh:
if credentials.valid:
    # Update file store
    if user_google_email and not is_stateless_mode():
        credential_store = get_credential_store()
        credential_store.store_credential(user_google_email, credentials)
    
    # Update session store
    store = get_oauth21_session_store()
    if user_google_email:
        store.store_session(
            user_email=user_google_email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes,
            expiry=credentials.expiry,
            mcp_session_id=session_id,
        )
    
    # Update session cache
    if session_id:
        save_credentials_to_session(session_id, credentials)
```

### Step 2.4: Add Clear Re-auth Instructions

**File**: `auth/service_decorator.py`

Improve the error message when re-auth is needed:

```python
def _handle_token_refresh_error(error: RefreshError, user_email: str, service_name: str) -> str:
    """Handle token refresh errors with clear instructions."""
    error_str = str(error).lower()
    
    # Check for common refresh failure reasons
    if "invalid_grant" in error_str or "expired or revoked" in error_str:
        return (
            f"## Authentication Required\n\n"
            f"Your Google credentials for **{user_email}** have expired or been revoked.\n\n"
            f"### Why this happens:\n"
            f"- Token unused for extended period (Google expires after ~6 months)\n"
            f"- Password changed on Google account\n"
            f"- Access revoked in Google Account settings\n"
            f"- App permissions modified\n\n"
            f"### To fix:\n"
            f"Run `start_google_auth` with:\n"
            f"- `user_google_email`: `{user_email}`\n"
            f"- `service_name`: `Google {service_name.title()}`\n\n"
            f"Then retry your original command."
        )
    else:
        return (
            f"Authentication error for {user_email}. "
            f"Please run `start_google_auth` to reauthenticate."
        )
```

---

## 5. Phase 3: Incremental P4 (DI + Error Hierarchy)

**Goal**: Add testability infrastructure without breaking changes.

**Effort**: 2-3 hours

### Step 3.1: Create DI Container

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

### Step 3.2: Extend Error Hierarchy

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

---

## 6. Phase 4: Auth Consolidation Preparation

**Goal**: Prepare for full auth module restructuring without breaking changes.

**Effort**: 2-3 hours

### Step 4.1: Create Unified Auth Interface

**File**: `auth/interfaces.py` (NEW)

```python
"""
Abstract interfaces for authentication components.

These interfaces define the contracts that implementations must satisfy,
enabling future refactoring without breaking existing code.
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

### Step 4.2: Document Current Dependencies

**File**: `auth/ARCHITECTURE.md` (NEW)

```markdown
# Auth Module Architecture

## Current State (Pre-Consolidation)

### File Dependencies

```
google_auth.py
├── credential_store.py (get_credential_store)
├── google_oauth_config.py (get_google_oauth_config, get_credentials_directory)
├── oauth21_session_store.py (get_oauth21_session_store)
├── oauth_config.py (is_stateless_mode)
├── scopes.py (SCOPES, get_current_scopes)
└── core/context.py (get_fastmcp_session_id)

service_decorator.py
├── google_auth.py (GoogleAuthenticationError, get_authenticated_google_service)
├── oauth21_session_store.py (ensure_session_from_access_token, get_auth_provider, get_oauth21_session_store)
├── oauth_config.py (get_oauth_config, is_oauth21_enabled)
├── scopes.py (all scope constants)
└── core/context.py (set_fastmcp_session_id)

oauth21_session_store.py
├── core/config.py (get_transport_mode)
└── auth/oauth_config.py (get_oauth_config)
```

### Data Stores

1. **LocalDirectoryCredentialStore** (file-based)
   - Location: `~/.config/google-workspace-mcp/credentials/{email}.json`
   - Persists: tokens, refresh tokens, scopes, expiry
   - Survives: server restarts

2. **OAuth21SessionStore** (memory + partial disk)
   - Memory: `_sessions`, `_mcp_session_mapping`, `_session_auth_binding`
   - Disk: `oauth_states.json` (OAuth flow states only)
   - Survives: OAuth states survive, session mappings DO NOT

### Known Issues

1. Session mappings lost on restart (RC-1)
2. Session ID mismatch between runs (RC-2)
3. No single-user auto-recovery (RC-5)

## Target State (Post-Consolidation)

See Phase 5 for the target architecture.
```

---

## 7. Phase 5: Full Auth Consolidation

**Goal**: Restructure auth module for long-term maintainability.

**Effort**: 4-6 hours

**Prerequisites**: Phases 1-4 complete, all tests passing.

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

### Migration Steps

1. Create new directory structure
2. Create `auth/config.py` (merge configs)
3. Create `auth/credentials/types.py` (dataclasses)
4. Create `auth/credentials/session.py` (extract from oauth21_session_store.py)
5. Create compatibility shims in old locations
6. Update imports across codebase
7. Run tests, fix any issues
8. Remove old files after deprecation period

---

## 8. Verification Checklist

### After Each Phase

- [ ] All existing tests pass: `uv run pytest tests/ -v`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Server starts: `python main.py`
- [ ] Can authenticate: Complete OAuth flow
- [ ] Credentials persist: Restart server, verify no re-auth needed

### Final Verification

- [ ] Single-user mode works without re-auth
- [ ] Multi-user mode correctly isolates sessions
- [ ] Token refresh works and updates all stores
- [ ] Session mappings survive server restart
- [ ] Clear error messages when re-auth is needed
- [ ] No regressions in existing functionality

---

## Quick Start

To begin fixing the re-authentication issues:

```bash
# 1. Enable diagnostics
export AUTH_DIAGNOSTICS=1

# 2. Run the server and reproduce the issue
python main.py

# 3. Check the logs for [AUTH_DIAG] and [CRED_LOOKUP] entries

# 4. Run the new tests
uv run pytest tests/integration/test_auth_flow.py -v
uv run pytest tests/unit/auth/ -v
```

The diagnostic logs will show exactly where credentials are being looked up and why they're not being found.
