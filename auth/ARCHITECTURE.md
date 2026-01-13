# Auth Module Architecture

## Current State (v0.3.0)

### Module Overview

The auth module handles OAuth 2.0/2.1 authentication for Google Workspace APIs.
It supports both single-user and multi-user modes with MCP session binding.

### File Structure

```
auth/
├── __init__.py                 # Public API exports
├── interfaces.py               # Abstract base classes (NEW in v0.4.0)
├── google_auth.py              # Core OAuth flow and credential management
├── google_oauth_config.py      # Embedded OAuth credentials and paths
├── oauth_config.py             # OAuth configuration and mode detection
├── oauth21_session_store.py    # Session management with persistence
├── credential_store.py         # File-based credential storage
├── service_decorator.py        # @require_google_service decorator
├── scopes.py                   # OAuth scope definitions
├── diagnostics.py              # Auth debugging utilities
├── auth_info_middleware.py     # Auth info extraction middleware
├── mcp_session_middleware.py   # MCP session binding middleware
├── external_oauth_provider.py  # External OAuth provider support
├── oauth_callback_server.py    # Local OAuth callback server
├── oauth_types.py              # OAuth-related type definitions
└── oauth_responses.py          # OAuth response formatting
```

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

| Store | Type | Location | Survives Restart |
|-------|------|----------|------------------|
| LocalDirectoryCredentialStore | File | `~/.config/gws-mcp-advanced/credentials/{email}.json` | Yes |
| OAuth21SessionStore._sessions | Memory | N/A | No |
| OAuth21SessionStore._mcp_session_mapping | Memory + Disk | `sessions.json` | Yes (v0.2.0+) |
| OAuth21SessionStore._session_auth_binding | Memory + Disk | `sessions.json` | Yes (v0.2.0+) |
| OAuth21SessionStore.oauth_states | Disk | `oauth_states.json` | Yes |

### Key Components

#### LocalDirectoryCredentialStore
- Persists OAuth tokens to disk as JSON files
- One file per user: `{email}.json`
- Stores: access_token, refresh_token, scopes, expiry, token_uri

#### OAuth21SessionStore
- Manages in-memory sessions with disk persistence for recovery
- Binds MCP sessions to Google user accounts
- Supports single-user auto-recovery mode

#### GoogleAuth (google_auth.py)
- Handles OAuth flow initiation and callback
- Token refresh with automatic retry
- Credential validation and scope checking

#### ServiceDecorator (@require_google_service)
- Injects authenticated Google API service into tool functions
- Handles token refresh and re-authentication prompts
- Maps service names to required scopes

### Authentication Flow

```
1. Tool invoked with user_google_email
   │
2. @require_google_service decorator
   │
3. Check OAuth21SessionStore for MCP session binding
   │
   ├─ Found → Get credentials from session
   │
   └─ Not found → Check LocalDirectoryCredentialStore
      │
      ├─ Found → Validate and refresh if needed
      │          Bind to MCP session
      │
      └─ Not found → Single-user mode?
         │
         ├─ Yes + 1 user exists → Auto-bind
         │
         └─ No → Return auth URL
```

### Resolved Issues (v0.2.0+)

- **RC-1**: Session mappings now persist to `sessions.json`
- **RC-5**: Single-user auto-recovery implemented

### Interfaces (v0.4.0)

Abstract base classes in `auth/interfaces.py`:
- `BaseCredentialStore`: Contract for credential storage
- `BaseSessionStore`: Contract for session management
- `BaseAuthProvider`: Contract for OAuth providers

These enable dependency injection via `core/container.py`.

## Target State (Phase 5+)

See `specs/03_architecture_and_consolidation.md` for the target structure:

```
auth/
├── config.py                   # MERGE: oauth_config.py + google_oauth_config.py
├── scopes.py                   # KEEP
├── decorators.py               # RENAME: service_decorator.py
├── interfaces.py               # KEEP
├── credentials/
│   ├── store.py                # KEEP: credential_store.py
│   ├── session.py              # EXTRACT: from oauth21_session_store.py
│   └── types.py                # MERGE: oauth_types.py
├── providers/
│   ├── google.py               # EXTRACT: from google_auth.py
│   └── external.py             # RENAME: external_oauth_provider.py
├── middleware/
│   ├── auth_info.py            # RENAME: auth_info_middleware.py
│   └── session.py              # RENAME: mcp_session_middleware.py
└── server/
    └── callback.py             # RENAME: oauth_callback_server.py
```
