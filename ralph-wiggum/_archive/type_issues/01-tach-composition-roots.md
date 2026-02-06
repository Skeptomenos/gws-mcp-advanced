# Spec 01: Allow Core Module Dependencies for Composition Roots

**Parent Plan:** [`docs/PHASE_1_2_IMPLEMENTATION_PLAN.md`](../../docs/PHASE_1_2_IMPLEMENTATION_PLAN.md)  
**Status:** COMPLETE  
**Estimated Time:** 15 minutes

---

## Context

The `core/` module is intended to be the base layer of the 3-layer architecture. However, `core/server.py` and `core/container.py` act as "Composition Roots" — they are responsible for wiring all dependencies together. Consequently, they *must* import from higher-level modules (`auth/`, `gdrive/`, etc.), which `tach` flags as dependency violations.

**Solution Chosen: Option A** - Add `auth` and `gdrive` as allowed dependencies for the `core` module itself, with documentation explaining that only composition root files should use these imports. This is simpler than creating child modules and avoids tach's parent-child dependency restrictions.

---

## Targeted Files

| File | Goal |
|------|------|
| `tach.toml` | Add `auth` and `gdrive` to `core` module's `depends_on` |

---

## Implementation (COMPLETED)

The following change was applied to `tach.toml`:

```toml
# Core depends on auth for composition roots (server.py, container.py)
# and gdrive for comments.py. Per ADR-1, this is acceptable for
# composition roots that wire dependencies together.
[[modules]]
path = "core"
depends_on = [
    "auth",
    "gdrive",
]
```

**Why Option A over child modules:**
- Creating `path = "core.server"` makes it a separate module that `core` cannot depend on
- This breaks `core/__init__.py` which re-exports from `core.server`
- Option A is simpler: trust developers to only use `auth`/`gdrive` imports in composition roots

---

## Post-Refactoring Tightening

After Specs 02-04 are complete:
- `core/comments.py` will be moved to `gdocs/` (Spec 02) → can remove `gdrive` from `core` dependencies
- `core/config.py` will be deleted (Spec 03)
- `core/managers.py` and `core/utils.py` will use constructor injection (Spec 04) → may be able to remove `auth` dependency

The final `tach.toml` after all specs may have `core` with `depends_on = []` again.

---

## Verification

```bash
# Run tach check (use uvx if uv run has workspace issues)
uvx tach check
# Expected: ✅ All modules validated!
```

**Success Criteria:**
- All tach violations resolved
- `core` module can now legitimately depend on `auth` and `gdrive`
