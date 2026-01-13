# Spec: Phase 2 - Quick Wins (Fix Immediate Pain)

**Goal**: Fix the most impactful issues with minimal risk.

## 2.1 Persist Session Mappings to Disk

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

## 2.2 Add Single-User Auto-Recovery

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

## 2.3 Improve Token Refresh Synchronization

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

## 2.4 Add Clear Re-auth Instructions

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
