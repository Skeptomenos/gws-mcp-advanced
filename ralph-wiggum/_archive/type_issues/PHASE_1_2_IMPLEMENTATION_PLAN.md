# Phase 1.2: Core Decoupling Implementation Plan

**Date:** Feb 02, 2026  
**Status:** Planned  
**Violations to Fix:** 25 `tach` dependency violations  
**Effort:** High | **Risk:** Medium (with mitigation steps)

---

## Executive Summary

The `core/` module currently violates the 3-layer architecture by importing from higher-level modules (`auth/`, `gdrive/`). This plan resolves all 25 violations using a hybrid approach:

1. **Exempt Composition Roots** — `server.py` and `container.py` (~17 violations)
2. **Relocate Misplaced Modules** — `comments.py` and `config.py` (~7 violations)
3. **Apply Constructor Injection** — `managers.py` and `utils.py` (~1 violation)

---

## Architecture Decision Records

### ADR-1: Composition Root Exemption

**Decision:** `core/server.py` and `core/container.py` are designated as **composition roots** and are exempt from strict layering rules.

**Rationale:** 
- Composition roots are responsible for wiring the application together
- They must import from all layers to perform dependency injection
- This is a well-established pattern (Clean Architecture, Hexagonal Architecture)
- Fighting this pattern creates artificial complexity

**Implementation:** Update `tach.toml` to allow these modules to import from any layer.

### ADR-2: Module Relocation Strategy

**Decision:** Relocate modules to their semantic homes rather than extracting shared logic into `core/`.

**Rationale:**
- `core/comments.py` creates Google Docs comment tools → belongs in `gdocs/`
- `core/config.py` is pure auth configuration → belongs in `auth/`
- Code should live where it semantically belongs
- Prevents `core/` from becoming a dumping ground

### ADR-3: Constructor Injection for Dependencies

**Decision:** Use constructor injection (pass values directly) rather than Protocol pattern.

**Rationale:**
- Only 2 simple values needed (`sync_map_path`, `credentials_dir`)
- Values are `Path` objects, not complex behaviors
- Simpler, more direct, less boilerplate
- Can upgrade to Protocol pattern later if needed (YAGNI)

---

## Violation Inventory

| File | Lines | Violations | Category | Resolution |
|------|-------|------------|----------|------------|
| `core/server.py` | 12-304 | 15 | Composition Root | Exempt in `tach.toml` |
| `core/container.py` | 72, 77 | 2 | Composition Root | Exempt in `tach.toml` |
| `core/comments.py` | 11, 14 | 2 | Misplaced Module | Relocate to `gdocs/` |
| `core/config.py` | 13-17 | 5 | Misplaced Module | Merge into `auth/config.py` |
| `core/managers.py` | 14 | 1 | Dependency Violation | Constructor Injection |
| `core/utils.py` | 96 | 0* | Dependency Violation | Constructor Injection |

*Note: `core/utils.py` violation may have been resolved or miscounted in original report.

---

## Implementation Steps

### Step 1: Update `tach.toml` for Composition Roots

**Violations Fixed:** ~17  
**Risk:** Low  
**Breaking Changes:** None

**Action:** Add explicit dependency allowances for composition roots.

```toml
# tach.toml additions

[[modules]]
path = "core.server"
depends_on = ["auth", "gdrive", "gdocs", "gmail", "gcalendar", "gsheets", "gchat", "gforms", "gslides", "gtasks", "gsearch"]

[[modules]]
path = "core.container"
depends_on = ["auth"]
```

**Verification:**
```bash
tach check
```

---

### Step 2: Relocate `core/comments.py` to `gdocs/`

**Violations Fixed:** 2  
**Risk:** Medium  
**Breaking Changes:** Import paths change

#### 2.1 Create new file

```bash
mv core/comments.py gdocs/comments.py
```

#### 2.2 Update imports in `gdocs/comments.py`

The file currently imports:
- `auth.service_decorator.require_google_service` — Keep (valid upward dependency from service layer)
- `gdrive.drive_helpers.resolve_file_id_or_alias` — Keep (peer dependency, gdocs already depends on gdrive)

No changes needed to the file content itself.

#### 2.3 Update `core/__init__.py`

Remove:
```python
from core.comments import create_comment_tools
```

#### 2.4 Update `gdocs/__init__.py`

Add:
```python
from gdocs.comments import create_comment_tools
```

#### 2.5 Update all consumers

Search and replace:
```bash
grep -r "from core.comments import" --include="*.py"
grep -r "from core import.*comments" --include="*.py"
```

Update each occurrence to import from `gdocs.comments`.

#### 2.6 Update `tach.toml`

Remove `core.comments` from interfaces if present.
Add to `gdocs` module dependencies if needed.

**Verification:**
```bash
tach check
python -c "from gdocs.comments import create_comment_tools"
```

---

### Step 3: Merge `core/config.py` into `auth/config.py`

**Violations Fixed:** 5  
**Risk:** Medium  
**Breaking Changes:** Import paths change

#### 3.1 Analyze current `core/config.py`

The file imports these from `auth.config`:
- `get_oauth_config`
- `get_oauth_client_id`
- `get_oauth_client_secret`
- `get_redirect_uri`
- `is_oauth21_enabled`

This is a re-export pattern that creates circular dependencies.

#### 3.2 Determine usage

```bash
grep -r "from core.config import" --include="*.py"
grep -r "from core import.*config" --include="*.py"
```

#### 3.3 Update all consumers

Change imports from:
```python
from core.config import get_oauth_config
```

To:
```python
from auth.config import get_oauth_config
```

#### 3.4 Delete `core/config.py`

```bash
rm core/config.py
```

#### 3.5 Update `core/__init__.py`

Remove any exports from `core.config`.

**Verification:**
```bash
tach check
python -c "from auth.config import get_oauth_config"
```

---

### Step 4: Apply Constructor Injection to `core/managers.py`

**Violations Fixed:** 1  
**Risk:** Low  
**Breaking Changes:** Constructor signature changes (with defaults for backward compatibility)

#### 4.1 Current state

```python
# core/managers.py
from auth.config import get_sync_map_path

class SyncManager:
    def __init__(self):
        self.sync_map_path = get_sync_map_path()
```

#### 4.2 Refactored state

```python
# core/managers.py
from pathlib import Path

class SyncManager:
    def __init__(self, sync_map_path: Path | None = None):
        self._sync_map_path = sync_map_path
    
    @property
    def sync_map_path(self) -> Path:
        if self._sync_map_path is not None:
            return self._sync_map_path
        # Default path - no import from auth needed
        config_dir = Path.home() / ".config" / "gws-mcp-advanced"
        return config_dir / "sync_map.json"
```

#### 4.3 Update composition root

```python
# core/server.py (or wherever SyncManager is instantiated)
from auth.config import get_sync_map_path
from core.managers import SyncManager

sync_manager = SyncManager(sync_map_path=get_sync_map_path())
```

**Verification:**
```bash
tach check
python -c "from core.managers import SyncManager; s = SyncManager(); print(s.sync_map_path)"
```

---

### Step 5: Apply Constructor Injection to `core/utils.py` (if needed)

**Violations Fixed:** 0-1  
**Risk:** Low

#### 5.1 Analyze current imports

```bash
grep "from auth" core/utils.py
```

If `get_default_credentials_dir` is imported, apply same pattern as Step 4.

#### 5.2 Refactor if needed

```python
# Before
from auth.google_auth import get_default_credentials_dir

def check_credentials_directory_permissions(credentials_dir: Path | None = None):
    if credentials_dir is None:
        credentials_dir = get_default_credentials_dir()
    ...

# After
def check_credentials_directory_permissions(credentials_dir: Path | None = None):
    if credentials_dir is None:
        credentials_dir = Path.home() / ".config" / "gws-mcp-advanced" / "credentials"
    ...
```

---

## Rollback Plan

If issues are discovered after deployment:

1. **Step 1 (tach.toml):** Revert `tach.toml` changes
2. **Step 2 (comments.py):** `git checkout core/comments.py` and revert `__init__.py` changes
3. **Step 3 (config.py):** `git checkout core/config.py` and revert import changes
4. **Step 4-5 (injection):** Revert constructor changes in `managers.py` and `utils.py`

All steps are independently revertible.

---

## Testing Strategy

### Pre-Implementation

```bash
# Baseline
tach check 2>&1 | tee baseline_tach.txt
python3 -m pytest tests/ -v 2>&1 | tee baseline_tests.txt
```

### Per-Step Verification

After each step:
```bash
tach check                           # Architecture compliance
python3 -m pytest tests/ -v          # Functionality preserved
python -c "from <module> import <symbol>"  # Import paths work
```

### Post-Implementation

```bash
# Final verification
tach check                           # Should show 0 dependency violations
python3 -m pytest tests/ -v          # All tests pass
ruff check .                         # No lint errors
```

---

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| `tach check` dependency violations | 25 | 0 |
| `pytest` failures | 0 | 0 |
| `ruff check` errors | 0 | 0 |
| Breaking changes to public API | - | 0 |

---

## Estimated Timeline

| Step | Description | Effort | Duration |
|------|-------------|--------|----------|
| 1 | Update `tach.toml` | Low | 15 min |
| 2 | Relocate `comments.py` | Medium | 30 min |
| 3 | Merge `config.py` | Medium | 30 min |
| 4 | Refactor `managers.py` | Low | 20 min |
| 5 | Refactor `utils.py` | Low | 15 min |
| - | Testing & Verification | Medium | 30 min |
| **Total** | | | **~2.5 hours** |

---

## Dependencies

- Phase 3.2 (Type Mismatches) can be done before or after this phase
- No external dependencies
- No infrastructure changes required

---

## Approval

- [ ] Architecture approach approved
- [ ] Breaking change assessment accepted
- [ ] Timeline acceptable
- [ ] Ready to implement
