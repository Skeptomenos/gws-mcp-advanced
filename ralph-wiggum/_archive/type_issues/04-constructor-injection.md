# Spec 04: Apply Constructor Injection to Core Utilities

**Parent Plan:** [`docs/PHASE_1_2_IMPLEMENTATION_PLAN.md`](../../docs/PHASE_1_2_IMPLEMENTATION_PLAN.md)  
**Status:** Ready for Implementation  
**Estimated Time:** 30 minutes

---

## Context

`core/managers.py` and `core/utils.py` currently import from `auth/` to retrieve default configuration paths (like the sync map file or credentials directory). This creates upward dependencies from the core layer. 

Following ADR-3, we will use **Constructor Injection** to decouple these modules. The core modules will define default behaviors but allow the composition root (`core/server.py`) to inject the actual values.

---

## Targeted Files

| File | Lines | Action |
|------|-------|--------|
| `core/managers.py` | 14, 137 | Refactor `SyncManager` to accept `sync_map_path` |
| `core/utils.py` | 96, 98 | Refactor `check_credentials_directory_permissions` to accept `credentials_dir` |
| `core/server.py` | ~150-300 | Inject values during instantiation |

---

## Implementation Instructions

### 1. Refactor `core/managers.py`

1.  Remove `from auth.config import get_sync_map_path` (line 14).
2.  Update `SyncManager.__init__`:
```python
# Before
def __init__(self):
    self.sync_map_path = get_sync_map_path()

# After
def __init__(self, sync_map_path: Path | str | None = None):
    self._sync_map_path = sync_map_path
```
3.  Add a property to handle defaults:
```python
@property
def sync_map_path(self) -> Path:
    if self._sync_map_path:
        return Path(self._sync_map_path)
    # Generic default - no import from auth needed
    return Path.home() / ".config" / "gws-mcp-advanced" / "sync_map.json"
```

### 2. Refactor `core/utils.py`

Update `check_credentials_directory_permissions` to remove the inline import of `get_default_credentials_dir`.

```python
# Before (line 96)
if credentials_dir is None:
    from auth.google_auth import get_default_credentials_dir
    credentials_dir = get_default_credentials_dir()

# After
if credentials_dir is None:
    credentials_dir = Path.home() / ".config" / "gws-mcp-advanced" / "credentials"
```

### 3. Update Composition Root (`core/server.py`)

Locate where `SyncManager` is instantiated and inject the correct path using the `auth.config` helper.

```python
from auth.config import get_sync_map_path
from core.managers import SyncManager

# Inject during instantiation
sync_manager = SyncManager(sync_map_path=get_sync_map_path())
```

---

## Verification

1.  **Architecture Check:**
    ```bash
    uv run tach check
    ```
    All dependency violations in `core/managers.py` and `core/utils.py` should be resolved.

2.  **Functional Check:**
    Verify that the sync map path is still correctly resolved by default:
    ```bash
    python -c "from core.managers import SyncManager; print(SyncManager().sync_map_path)"
    ```

3.  **Test Check:**
    Run existing tests to ensure no regressions:
    ```bash
    uv run pytest tests/unit/core/test_managers.py
    ```
    (Note: Some tests may need to be updated if they relied on the old constructor signature).
    ```bash
    uv run pytest tests/unit/core/test_utils.py
    ```
