# Implementation Plan: gws-mcp-advanced

> **Generated**: 2026-01-13  
> **Based on**: specs/01_diagnostics_and_testing.md, specs/02_session_persistence_and_recovery.md, specs/03_architecture_and_consolidation.md, AUTH_IMPROVEMENT_PLAN.md  
> **Status**: Phase 6 COMPLETE (v0.8.0) - Additional improvements finished

---

## Executive Summary

The gws-mcp-advanced project has resolved P0-P3 code quality issues. The remaining work focuses on:
1. **Critical Auth Fix**: Session mappings lost on server restart (RC-1)
2. **Test Infrastructure**: Missing auth tests and tool tests
3. **Architecture**: DI container, error hierarchy, auth consolidation

---

## Priority Definitions

| Priority | Description | Timeline |
|----------|-------------|----------|
| **P0** | Critical blocker - prevents normal usage | Immediate |
| **P1** | High impact - significantly improves reliability | This sprint |
| **P2** | Medium impact - improves maintainability | Next sprint |
| **P3** | Low impact - nice to have | Backlog |
| **P4** | Architectural - long-term improvements | Future |

---

## Phase 1: Diagnostic & Test Infrastructure ✅ COMPLETE (v0.1.0)

**Goal**: Create infrastructure for debugging and preventing auth regressions.
**Status**: All 4 tasks completed. 85 tests passing.

### P1-1: Create Auth Diagnostics Module
- **File**: `auth/diagnostics.py` (NEW)
- **Spec**: specs/01_diagnostics_and_testing.md, lines 7-90
- **Effort**: 1 hour
- **Dependencies**: None
- **Description**: Add `log_auth_attempt()`, `log_credential_lookup()`, `log_session_state()` functions controlled by `AUTH_DIAGNOSTICS=1` env var.

### P1-2: Create Credential Store Unit Tests
- **File**: `tests/unit/auth/test_credential_store.py` (NEW)
- **Spec**: specs/01_diagnostics_and_testing.md, lines 252-258
- **Effort**: 1.5 hours
- **Dependencies**: None
- **Description**: Test `LocalDirectoryCredentialStore` - store/retrieve, delete, list_users, expiry preservation.

### P1-3: Create Session Store Unit Tests
- **File**: `tests/unit/auth/test_session_store.py` (NEW)
- **Spec**: specs/01_diagnostics_and_testing.md, lines 256-258
- **Effort**: 2 hours
- **Dependencies**: None
- **Description**: Test `OAuth21SessionStore` - session storage, MCP session mapping, binding immutability, single-user detection.

### P1-4: Create Auth Integration Tests
- **File**: `tests/integration/test_auth_flow.py` (NEW)
- **Spec**: specs/01_diagnostics_and_testing.md, lines 92-250
- **Effort**: 2 hours
- **Dependencies**: P1-2, P1-3
- **Description**: Test credential persistence across restarts, session recovery scenarios, token refresh.

---

## Phase 2: Quick Wins (Fix Immediate Pain) ✅ COMPLETE (v0.2.0)

**Goal**: Fix the critical RC-1 issue and improve user experience.
**Status**: All 4 tasks completed. 85 tests passing. Session mappings now persist across restarts.

### P0-1: Persist Session Mappings to Disk [CRITICAL] ✅
- **File**: `auth/oauth21_session_store.py`
- **Spec**: specs/02_session_persistence_and_recovery.md, lines 5-86
- **Effort**: 2 hours
- **Dependencies**: P1-3 (tests should exist first)
- **Description**: 
  - Add `_get_sessions_file_path()` method
  - Add `_load_session_mappings_from_disk()` method
  - Add `_save_session_mappings_to_disk()` method
  - Call load in `__init__`, save after `store_session()`
  - Persist: `_mcp_session_mapping`, `_session_auth_binding`, session metadata (not tokens)

### P0-2: Add Single-User Auto-Recovery ✅
- **File**: `auth/google_auth.py`
- **Spec**: specs/02_session_persistence_and_recovery.md, lines 88-143
- **Effort**: 1.5 hours
- **Dependencies**: P0-1
- **Description**: In `get_credentials()`, if no credentials found and only one user exists in credential store, auto-bind the session to that user.

### P1-5: Improve Token Refresh Synchronization ✅ (pre-existing)
- **File**: `auth/google_auth.py`
- **Spec**: specs/02_session_persistence_and_recovery.md, lines 145-177
- **Effort**: 1 hour
- **Dependencies**: P0-1
- **Description**: After successful token refresh, update both `LocalDirectoryCredentialStore` and `OAuth21SessionStore`.
- **Note**: Already implemented in existing codebase.

### P1-6: Add Clear Re-auth Instructions ✅ (pre-existing)
- **File**: `auth/service_decorator.py`
- **Spec**: specs/02_session_persistence_and_recovery.md, lines 179-212
- **Effort**: 0.5 hours
- **Dependencies**: None
- **Description**: Create `_handle_token_refresh_error()` function with user-friendly markdown instructions.
- **Note**: Already implemented in existing codebase.

---

## Phase 3: Incremental P4 (DI + Error Hierarchy) ✅ COMPLETE (v0.3.0)

**Goal**: Add testability infrastructure without breaking changes.
**Status**: All tasks completed. 115 tests passing.

### P2-1: Create DI Container ✅
- **File**: `core/container.py` (NEW)
- **Spec**: specs/03_architecture_and_consolidation.md, lines 7-85
- **Effort**: 1.5 hours
- **Dependencies**: None
- **Description**: Created `CredentialStoreProtocol`, `SessionStoreProtocol`, `Container` dataclass, and global getter/setter/reset functions.

### P2-2: Extend Error Hierarchy ✅
- **File**: `core/errors.py`
- **Spec**: specs/03_architecture_and_consolidation.md, lines 87-140
- **Effort**: 1 hour
- **Dependencies**: None
- **Description**: Added `SessionBindingError`, `TokenRefreshError`, `ScopeMismatchError` with enhanced constructors. Enhanced `CredentialsNotFoundError` with `user_email` parameter.

---

## Phase 4: Auth Consolidation Preparation ✅ COMPLETE (v0.4.0)

**Goal**: Prepare for full auth module restructuring.
**Status**: All 2 tasks completed. 115 tests passing.

### P3-1: Create Unified Auth Interfaces ✅
- **File**: `auth/interfaces.py` (NEW)
- **Spec**: specs/03_architecture_and_consolidation.md, lines 142-250
- **Effort**: 1.5 hours
- **Dependencies**: P2-1
- **Description**: Create `BaseCredentialStore`, `BaseSessionStore`, `BaseAuthProvider` abstract base classes.

### P3-2: Document Current Auth Architecture ✅
- **File**: `auth/ARCHITECTURE.md` (NEW)
- **Spec**: AUTH_IMPROVEMENT_PLAN.md, lines 1173-1226
- **Effort**: 1 hour
- **Dependencies**: None
- **Description**: Document file dependencies, data stores, known issues for future consolidation.

---

## Phase 5a: Auth Consolidation - Credentials & Types COMPLETE (v0.5.0)
**Goal**: Move data structures and storage logic first.
**Status**: All tasks completed. 115 tests passing.

### P4-1a: Move Credentials & Types
- **Files**: `auth/credentials/*.py`, `auth/config.py`
- **Spec**: specs/03_architecture_and_consolidation.md
- **Effort**: 2 hours
- **Dependencies**: Phase 4 complete
- **Description**: 
  - Create `auth/config.py` (merge oauth_config.py + google_oauth_config.py)
  - Create `auth/credentials/types.py` (merge oauth_types.py)
  - Create `auth/credentials/store.py` (move credential_store.py)
  - Create shims in old locations for backward compatibility
- **Note**: Session extraction deferred to Phase 5b (requires provider refactoring first)

## Phase 5b: Auth Consolidation - Logic & Middleware ✅ COMPLETE (v0.6.0)
**Goal**: Move business logic and request handling.
**Status**: All tasks completed. 115 tests passing.

### P4-1b: Move Providers & Middleware ✅
- **Files**: `auth/providers/*.py`, `auth/middleware/*.py`
- **Spec**: specs/03_architecture_and_consolidation.md
- **Effort**: 2 hours
- **Dependencies**: Phase 5a
- **Description**:
  - Created `auth/providers/external.py` (moved from `external_oauth_provider.py`)
  - Created `auth/middleware/auth_info.py` (moved from `auth_info_middleware.py`)
  - Created `auth/middleware/session.py` (moved from `mcp_session_middleware.py`)
  - Created backward-compatibility shims with deprecation warnings at old locations
- **Note**: `google_auth.py` extraction deferred to Phase 5c (requires more refactoring)

## Phase 5c: Auth Consolidation - Cleanup ✅ COMPLETE (v0.7.0)
**Goal**: Finalize migration and cleanup.
**Status**: All tasks completed. 115 tests passing.

### P4-1c: Fix Imports & Cleanup ✅
- **Files**: All consumer files
- **Spec**: specs/03_architecture_and_consolidation.md
- **Effort**: 2 hours
- **Dependencies**: Phase 5b
- **Description**:
  - Updated imports in `main.py`, `fastmcp_server.py`, `core/server.py`, `core/config.py`, `core/managers.py`
  - Updated imports in `auth/google_auth.py`, `auth/service_decorator.py`, `auth/oauth21_session_store.py`
  - Updated imports in `gdrive/drive_tools.py`, `gmail/gmail_tools.py`
  - Updated `auth/__init__.py` to use canonical imports from `auth.config`
  - All consumer files now import from canonical locations (`auth.config`, `auth.middleware.*`, `auth.providers.*`)
  - Shim files remain for backward compatibility with deprecation warnings

---

## Phase 6: Additional Improvements ✅ COMPLETE (v0.8.0)

**Goal**: Code quality improvements and test organization.
**Status**: All 3 tasks completed. 121 tests passing.

### P2-3: Standardize Decorator Order ✅
- **Files**: `gtasks/tasks_tools.py`, `gchat/chat_tools.py`
- **Effort**: 0.5 hours
- **Dependencies**: None
- **Description**: Fixed decorator order to match AGENTS.md: `@server.tool` -> `@handle_http_errors` -> `@require_google_service`. Updated 12 functions in gtasks and 4 functions in gchat.

### P3-3: Move OAuth State Persistence Test ✅
- **File**: `tests/test_oauth_state_persistence.py` -> `tests/unit/auth/test_oauth_state_persistence.py`
- **Effort**: 0.25 hours
- **Dependencies**: None
- **Description**: Reorganized for consistency with test directory structure.

### P3-4: Add Tool Unit Tests (Template) ✅
- **File**: `tests/unit/tools/test_gmail_tools.py` (NEW)
- **Effort**: 2 hours
- **Dependencies**: None
- **Description**: Created template for testing MCP tools with mocked Google services. Includes examples for testing helper functions and tool registration.

---

## Implementation Order (Recommended)

```
Week 1: Critical Fixes
├── P1-1: Auth Diagnostics Module
├── P1-2: Credential Store Unit Tests
├── P1-3: Session Store Unit Tests
├── P0-1: Persist Session Mappings [CRITICAL]
└── P0-2: Single-User Auto-Recovery

Week 2: Reliability Improvements
├── P1-4: Auth Integration Tests
├── P1-5: Token Refresh Synchronization
├── P1-6: Clear Re-auth Instructions
├── P2-1: DI Container
└── P2-2: Extend Error Hierarchy

Week 3: Architecture Preparation
├── P2-3: Standardize Decorator Order
├── P3-1: Unified Auth Interfaces
├── P3-2: Document Auth Architecture
├── P3-3: Move OAuth State Test
└── P3-4: Tool Unit Tests Template

Week 4+: Full Consolidation
└── P4-1: Auth Module Restructuring
```

---

## Verification Checklist

### After Each Task
- [ ] All existing tests pass: `uv run pytest tests/ -v`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Server starts: `python main.py`

### After Phase 2 (Critical Fixes)
- [ ] Can authenticate: Complete OAuth flow
- [ ] Credentials persist: Restart server, verify no re-auth needed
- [ ] Single-user mode works without re-auth

### After All Phases
- [ ] Multi-user mode correctly isolates sessions
- [ ] Token refresh works and updates all stores
- [ ] Session mappings survive server restart
- [ ] Clear error messages when re-auth is needed
- [ ] No regressions in existing functionality

---

## Files to Create

| File | Phase | Priority |
|------|-------|----------|
| `auth/diagnostics.py` | 1 | P1 | ✅ Created |
| `tests/unit/auth/test_credential_store.py` | 1 | P1 | ✅ Created |
| `tests/unit/auth/test_session_store.py` | 1 | P1 | ✅ Created |
| `tests/integration/test_auth_flow.py` | 1 | P1 | ✅ Created |
| `core/container.py` | 3 | P2 | ✅ Created |
| `tests/unit/core/test_container.py` | 3 | P2 | ✅ Created |
| `auth/interfaces.py` | 4 | P3 | ✅ Created |
| `auth/ARCHITECTURE.md` | 4 | P3 | ✅ Created |
| `auth/config.py` | 5a | P4 | ✅ Created |
| `auth/credential_types/__init__.py` | 5a | P4 | ✅ Created |
| `auth/credential_types/types.py` | 5a | P4 | ✅ Created |
| `auth/credential_types/store.py` | 5a | P4 | ✅ Created |
| `auth/providers/__init__.py` | 5b | P4 | ✅ Created |
| `auth/providers/external.py` | 5b | P4 | ✅ Created |
| `auth/middleware/__init__.py` | 5b | P4 | ✅ Created |
| `auth/middleware/auth_info.py` | 5b | P4 | ✅ Created |
| `auth/middleware/session.py` | 5b | P4 | ✅ Created |
| `tests/unit/tools/test_gmail_tools.py` | 6 | P3 | ✅ Created |

## Files to Modify

| File | Phase | Priority | Changes |
|------|-------|----------|---------|
| `auth/oauth21_session_store.py` | 2 | P0 | Add session persistence methods |
| `auth/google_auth.py` | 2 | P0 | Add single-user auto-recovery |
| `auth/service_decorator.py` | 2 | P1 | Add clear re-auth instructions |
| `core/errors.py` | 3 | P2 | Add auth-specific errors |
| `gtasks/tasks_tools.py` | 6 | P2 | ✅ Fixed decorator order |
| `gchat/chat_tools.py` | 6 | P2 | ✅ Fixed decorator order |

---

## Notes

1. **Test-First Approach**: Create tests (P1-2, P1-3) before implementing fixes (P0-1, P0-2)
2. **Incremental Changes**: Each task should be a single, reviewable commit
3. **No Breaking Changes**: Maintain backward compatibility throughout
4. **AUTH_IMPROVEMENT_PLAN.md**: This document supersedes the detailed plan in that file
