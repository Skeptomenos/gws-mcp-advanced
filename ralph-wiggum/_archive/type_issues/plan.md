# Implementation Plan: Phase 1.2 - Core Architecture Refactoring

**Objective**: Resolve ~25 `tach` dependency violations in `core/` module by decoupling it from higher-level modules (`auth/`, `gdrive/`).

**Strategy**: 
1. Exempt composition roots (`server`, `container`) via tach config
2. Relocate domain logic (`comments`) to appropriate domain module
3. Consolidate config proxies
4. Apply constructor injection for remaining dependencies

**Environment**: Tests must run in project virtualenv. Use `uvx --python .venv/bin/python pytest` or `.venv/bin/python -m pytest`. For tools use `uvx tach check` and `uvx ruff check .` to avoid workspace config issues.

---

## Tasks

### Phase 1: Tach Configuration (Spec 01)
*Goal: Legitimize upward dependencies for composition roots. ~17 violations resolved.*

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 1.1**: Add `core.server` and `core.container` module entries to `tach.toml` with appropriate dependencies | `specs/01-tach-composition-roots.md` | Also add `gdocs` dependency to `gsheets` and `gslides` for Spec 02 |
| [x] | **Task 1.2**: Run `uv run tach check` and verify violation reduction | `specs/01-tach-composition-roots.md` | May need `uv run --isolated tach check` due to parent workspace config |

### Phase 2: Relocate Comments Module (Spec 02)
*Goal: Move domain-specific logic out of `core`. 2 violations resolved.*

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 2.1**: Replace `gdocs/comments.py` wrapper (15 lines) with full implementation from `core/comments.py` (283 lines) | `specs/02-relocate-comments.md` | Ensure `from core.server import server` is used |
| [x] | **Task 2.2**: Update `gsheets/sheets_tools.py:13` import from `core.comments` to `gdocs.comments` | `specs/02-relocate-comments.md` | |
| [x] | **Task 2.3**: Update `gslides/slides_tools.py:12` import from `core.comments` to `gdocs.comments` | `specs/02-relocate-comments.md` | |
| [x] | **Task 2.4**: Remove `create_comment_tools` export from `core/__init__.py:4` | `specs/02-relocate-comments.md` | |
| [x] | **Task 2.5**: Update `tach.toml` interfaces - remove `comments.create_comment_tools` from `core`, add to `gdocs` | `specs/02-relocate-comments.md` | |
| [x] | **Task 2.6**: Delete `core/comments.py` and verify server starts | `specs/02-relocate-comments.md` | Test with `python main.py --tools gdocs gsheets gslides --single-user` |

### Phase 3: Config Consolidation (Spec 03)
*Goal: Remove `core/config.py` proxy layer. ~5 violations resolved.*

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 3.1**: Update `core/server.py` (lines 22, 26, 29) - change `core.config` imports to `auth.config` | `specs/03-merge-config.md` | Consolidated to single import block |
| [x] | **Task 3.2**: Update `core/attachment_storage.py:202` - inline import to `auth.config` | `specs/03-merge-config.md` | Done |
| [x] | **Task 3.3**: Update `auth/middleware/auth_info.py:164` - inline import to `auth.config` | `specs/03-merge-config.md` | Done |
| [x] | **Task 3.4**: Update `auth/oauth21_session_store.py:801` - inline import to `auth.config` | `specs/03-merge-config.md` | Done |
| [x] | **Task 3.5**: Update `gdrive/files.py:22` - import to `auth.config` | `specs/03-merge-config.md` | Done |
| [x] | **Task 3.6**: Update `tach.toml` interfaces - remove `config.get_transport_mode` from `core`, add new constants to `auth` | `specs/03-merge-config.md` | Added USER_GOOGLE_EMAIL, WORKSPACE_MCP_BASE_URI, WORKSPACE_MCP_PORT |
| [x] | **Task 3.7**: Delete `core/config.py` and verify all imports work | `specs/03-merge-config.md` | Verified with grep, 328 tests pass |

### Phase 4: Constructor Injection (Spec 04)
*Goal: Invert control to remove `auth` dependencies from core logic. Remaining violations.*

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 4.1**: Refactor `SyncManager` in `core/managers.py` to accept `sync_map_path` via constructor and remove `auth.config` import (line 14) | `specs/04-constructor-injection.md` | Done: Added `sync_map_path` param with default, removed `auth.config` import, updated tests |
| [x] | **Task 4.2**: Update `core/container.py` to inject `sync_map_path` from `auth.config.get_sync_map_path()` | `specs/04-constructor-injection.md` | NOT NEEDED: Global `sync_manager` uses default path, no explicit instantiation in composition root |
| [x] | **Task 4.3**: Refactor `check_credentials_directory_permissions` in `core/utils.py:96-98` to use default path, remove `auth` import | `specs/04-constructor-injection.md` | Done: Added `Path` import, default to `~/.config/gws-mcp-advanced/credentials`, accepts `Path | str | None` |
| [x] | **Task 4.4**: Update composition roots to inject credentials path from `auth.google_auth` | `specs/04-constructor-injection.md` | Done: `main.py` and `fastmcp_server.py` use lazy import of `get_default_credentials_dir()` to avoid circular dependency |
| [x] | **Task 4.5**: Update unit tests for refactored signatures | `specs/04-constructor-injection.md` | Done: Updated `tests/unit/test_managers.py` to use `sync_map_path` parameter |

### Phase 5: Final Verification

| Status | Task | Spec Reference | Notes |
|--------|------|----------------|-------|
| [x] | **Task 5.1**: Run lint and format checks (`uv run ruff check . && uv run ruff format .`) | N/A | All checks passed, 104 files already formatted |
| [x] | **Task 5.2**: Run test suite (`uv run pytest`) | N/A | 328 tests pass |
| [x] | **Task 5.3**: Run architecture check (`uv run tach check`) and verify 0 violations for `core` | N/A | ✅ All modules validated! |
| [x] | **Task 5.4**: Manual server startup test: `python main.py --single-user` | N/A | Server starts successfully, credentials directory verified |

---

## Legend

- `[ ]` Pending
- `[x]` Complete
- `[!]` Blocked

---

## Task Count Summary

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Tach Config | 2 | 15 min |
| Phase 2: Relocate Comments | 6 | 30 min |
| Phase 3: Config Consolidation | 7 | 25 min |
| Phase 4: Constructor Injection | 5 | 35 min |
| Phase 5: Verification | 4 | 15 min |
| **Total** | **24** | **~2 hours** |

---

## Notes

### Current State Analysis (Updated 2026-02-02)
1. `core/comments.py` - DELETED, implementation moved to `gdocs/comments.py` (295 lines)
2. `core/config.py` - DELETED, constants moved to `auth/config.py`
3. `core/managers.py` - REFACTORED: `SyncManager` now accepts `sync_map_path` via constructor, `auth.config` import REMOVED
4. `core/utils.py` - REFACTORED: `check_credentials_directory_permissions` uses default path `~/.config/gws-mcp-advanced/credentials`, `auth` import REMOVED
5. All 328 tests pass, tach check passes (0 violations), ruff check passes

### PHASE 1.2 COMPLETE
All 25 tach dependency violations in `core/` have been resolved through:
- Composition root exemptions (server.py, container.py)
- Module relocation (comments.py → gdocs/)
- Config consolidation (core/config.py deleted)
- Constructor injection (managers.py, utils.py)

### Completed Migrations

**core.comments (DONE):**
- Moved to `gdocs/comments.py`
- Updated consumers: `gsheets/sheets_tools.py`, `gslides/slides_tools.py`
- Removed from `core/__init__.py`

**core.config (DONE):**
- Added `USER_GOOGLE_EMAIL`, `WORKSPACE_MCP_BASE_URI`, `WORKSPACE_MCP_PORT` to `auth/config.py`
- Updated all 5 consumer files to import from `auth.config`
- Updated `auth/__init__.py` with new exports
- Updated `tach.toml` interfaces

### Dependencies
- Phase 1 can be done independently
- Phase 2 depends on Phase 1 (tach.toml must have gsheets/gslides → gdocs dependency)
- Phase 3 can be done after Phase 1
- Phase 4 can be done in parallel with Phase 2 and 3
- Phase 5 must be done last

### Execution Order (Recommended)
1. Phase 1 (Tach Config) - unblocks all other phases
2. Phase 2 (Comments) and Phase 3 (Config) - can be parallelized
3. Phase 4 (Constructor Injection)
4. Phase 5 (Verification)
