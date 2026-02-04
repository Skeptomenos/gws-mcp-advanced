# Spec 02: Relocate Comments Module to Google Docs

**Parent Plan:** [`docs/PHASE_1_2_IMPLEMENTATION_PLAN.md`](../../docs/PHASE_1_2_IMPLEMENTATION_PLAN.md)  
**Status:** Ready for Implementation  
**Estimated Time:** 30 minutes

---

## Context

`core/comments.py` contains 283 lines of implementation logic for Google Workspace comments (Read, Create, Reply, Resolve). It imports from `auth/` and `gdrive/`, violating the 3-layer architecture which dictates that `core/` should have no upward dependencies.

**Current State:**
- `core/comments.py` (283 lines) - Full implementation with `create_comment_tools()` factory
- `gdocs/comments.py` (15 lines) - Thin wrapper that imports from `core.comments`

**Approach:** Replace the thin wrapper in `gdocs/comments.py` with the full implementation, then update all consumers to import from `gdocs.comments`. Sheets and Slides will import from `gdocs` (acceptable cross-domain dependency since comments are Drive API based).

---

## Targeted Files

| File | Action |
|------|--------|
| `gdocs/comments.py` | Replace wrapper with full implementation |
| `core/comments.py` | DELETE after migration |
| `core/__init__.py` | Remove `create_comment_tools` export |
| `gsheets/sheets_tools.py` | Update import to `gdocs.comments` |
| `gslides/slides_tools.py` | Update import to `gdocs.comments` |
| `tach.toml` | Add `gdocs` dependency to `gsheets` and `gslides` |

---

## Consumer Inventory

Current imports of `core.comments`:

| File | Line | Import |
|------|------|--------|
| `core/__init__.py` | 4 | `from core.comments import create_comment_tools` |
| `gdocs/comments.py` | 7 | `from core.comments import create_comment_tools` |
| `gsheets/sheets_tools.py` | 13 | `from core.comments import create_comment_tools` |
| `gslides/slides_tools.py` | 12 | `from core.comments import create_comment_tools` |

---

## Implementation Instructions

### Step 1: Copy Implementation to gdocs/comments.py

Replace the contents of `gdocs/comments.py` with the full implementation from `core/comments.py`.

**Critical change:** Update the import of `server` to use `core.server`:

```python
# In the new gdocs/comments.py, ensure this import exists:
from core.server import server
```

The full implementation should include:
- `create_comment_tools()` factory function
- `_read_comments_impl()` 
- `_create_comment_impl()`
- `_reply_to_comment_impl()`
- `_resolve_comment_impl()`
- All decorated tool variants for document/spreadsheet/presentation

### Step 2: Update gsheets/sheets_tools.py

```python
# Before (line 13)
from core.comments import create_comment_tools

# After
from gdocs.comments import create_comment_tools
```

### Step 3: Update gslides/slides_tools.py

```python
# Before (line 12)
from core.comments import create_comment_tools

# After
from gdocs.comments import create_comment_tools
```

### Step 4: Update core/__init__.py

Remove the export of `create_comment_tools`:

```python
# DELETE this line:
from core.comments import create_comment_tools
```

Also remove `create_comment_tools` from the `__all__` list if present.

### Step 5: Update tach.toml

Add `gdocs` as a dependency for `gsheets` and `gslides`:

```toml
[[modules]]
path = "gsheets"
depends_on = [
    "auth",
    "core",
    "gdocs",  # ADD THIS
]

[[modules]]
path = "gslides"
depends_on = [
    "auth",
    "core",
    "gdocs",  # ADD THIS
]
```

Also update the `[[interfaces]]` section for `core` - remove these lines:
```toml
# REMOVE from core interfaces:
"comments.create_comment_tools",
"create_comment_tools",
```

And ensure `gdocs` interfaces include:
```toml
# ADD to gdocs interfaces if not present:
"comments.create_comment_tools",
```

### Step 6: Delete core/comments.py

```bash
rm core/comments.py
```

---

## Verification

1. **Import Check:**
   ```bash
   python -c "from gdocs.comments import create_comment_tools; print('gdocs import OK')"
   python -c "from gsheets.sheets_tools import read_spreadsheet_comments; print('gsheets import OK')"
   python -c "from gslides.slides_tools import read_presentation_comments; print('gslides import OK')"
   ```

2. **Architecture Check:**
   ```bash
   uv run tach check
   ```
   The 2 violations from `core/comments.py` should be resolved.

3. **Lint Check:**
   ```bash
   uv run ruff check gdocs/comments.py gsheets/sheets_tools.py gslides/slides_tools.py
   ```

4. **Functional Check:**
   ```bash
   python main.py --tools gdocs gsheets gslides --single-user
   ```
   Verify server starts without import errors.
