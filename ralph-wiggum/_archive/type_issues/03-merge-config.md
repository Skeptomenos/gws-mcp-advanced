# Spec 03: Merge Core Config into Auth Config

**Parent Plan:** [`docs/PHASE_1_2_IMPLEMENTATION_PLAN.md`](../../docs/PHASE_1_2_IMPLEMENTATION_PLAN.md)  
**Status:** Ready for Implementation  
**Estimated Time:** 25 minutes

---

## Context

`core/config.py` acts as a re-export layer for OAuth configuration, importing functions from `auth/config.py`. This creates upward dependencies from `core/` to `auth/`, violating the 3-layer architecture. Since this configuration is specifically about authentication, consumers should import directly from `auth/config.py`.

**Current State:**
- `core/config.py` is a pure re-export proxy (no unique logic)
- All functions are already defined in `auth/config.py`
- 7 files consume from `core.config` with 9 total import statements

---

## Targeted Files

| File | Action |
|------|--------|
| `core/config.py` | DELETE after updating consumers |
| `core/server.py` | Update 3 import blocks (lines 22, 26, 29) |
| `core/attachment_storage.py` | Update import (line 202) |
| `auth/middleware/auth_info.py` | Update import (line 164) |
| `auth/oauth21_session_store.py` | Update import (line 801) |
| `gdrive/files.py` | Update import (line 22) |
| `tach.toml` | Remove `core.config` from interfaces |

---

## Consumer Inventory

Complete list of `core.config` imports:

| File | Line | Import Statement |
|------|------|------------------|
| `core/server.py` | 22 | `from core.config import (...)` |
| `core/server.py` | 26 | `from core.config import (...)` |
| `core/server.py` | 29 | `from core.config import (...)` |
| `core/attachment_storage.py` | 202 | `from core.config import WORKSPACE_MCP_BASE_URI, WORKSPACE_MCP_PORT` |
| `auth/middleware/auth_info.py` | 164 | `from core.config import get_transport_mode` |
| `auth/oauth21_session_store.py` | 801 | `from core.config import get_transport_mode` |
| `gdrive/files.py` | 22 | `from core.config import get_transport_mode` |

---

## Implementation Instructions

### Step 1: Update core/server.py

This file has 3 separate import blocks from `core.config`. Update all to `auth.config`:

```python
# Before (lines 22-29, approximate)
from core.config import (
    get_oauth_base_url,
    get_oauth_redirect_uri,
    ...
)
from core.config import (
    is_oauth21_enabled,
    ...
)
from core.config import (
    set_transport_mode,
    ...
)

# After
from auth.config import (
    get_oauth_base_url,
    get_oauth_redirect_uri,
    is_oauth21_enabled,
    set_transport_mode,
    ...
)
```

Consolidate into a single import block if practical.

### Step 2: Update core/attachment_storage.py

```python
# Before (line 202, inline import)
from core.config import WORKSPACE_MCP_BASE_URI, WORKSPACE_MCP_PORT

# After
from auth.config import WORKSPACE_MCP_BASE_URI, WORKSPACE_MCP_PORT
```

### Step 3: Update auth/middleware/auth_info.py

```python
# Before (line 164)
from core.config import get_transport_mode

# After
from auth.config import get_transport_mode
```

### Step 4: Update auth/oauth21_session_store.py

```python
# Before (line 801)
from core.config import get_transport_mode

# After
from auth.config import get_transport_mode
```

### Step 5: Update gdrive/files.py

```python
# Before (line 22)
from core.config import get_transport_mode

# After
from auth.config import get_transport_mode
```

### Step 6: Update tach.toml

Remove `core.config` exports from the `[[interfaces]]` section for `core`:

```toml
# REMOVE these lines from core interfaces:
"config.get_transport_mode",
```

Ensure `auth.config` exports are already present (they should be).

### Step 7: Delete core/config.py

```bash
rm core/config.py
```

---

## Verification

1. **No remaining references:**
   ```bash
   grep -r "core\.config" --include="*.py" .
   # Should return empty or only this spec file
   ```

2. **Import Check:**
   ```bash
   python -c "from auth.config import get_transport_mode, is_oauth21_enabled; print('Import OK')"
   ```

3. **Architecture Check:**
   ```bash
   uv run tach check
   ```
   The ~5 violations from `core/config.py` should be resolved.

4. **Functional Check:**
   ```bash
   python main.py --single-user
   ```

5. **OAuth21 Check:**
   ```bash
   MCP_OAUTH21_ENABLE=1 python -c "from auth.config import is_oauth21_enabled; print(f'OAuth21: {is_oauth21_enabled()}')"
   # Should print: OAuth21: True
   ```
