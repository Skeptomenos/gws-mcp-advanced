# Release Notes

## 2026-03-03 - Apps Script v1 Rollout (`APPS-01`..`APPS-06`)

### Added
- New Apps Script service domain with read + mutation tooling.
- Read tools:
  - `get_script_project`
  - `list_script_projects` (Drive-backed standalone scripts)
  - `get_script_content`
  - `list_deployments`
  - `list_versions`
  - `get_version`
  - `list_script_processes`
  - `get_script_metrics`
- Mutating tools (default `dry_run=True`):
  - `create_script_project`
  - `update_script_content`
  - `create_version`
  - `create_deployment`
  - `update_deployment`
  - `delete_deployment`
  - `delete_script_project`
  - `run_script_function`

### Policy and Safety
- Expanded least-privilege scope mapping for Apps Script read/mutation surfaces.
- Added appscript tier mapping in `core/tool_tiers.yaml`.
- Extended static dry-run policy checker coverage to Apps Script mutators.

### Validation
- Local gates green:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pyright --project pyrightconfig.json`
  - `uv run pytest` (`709 passed`, `3 skipped`)
- Convex live mutation probes executed for Apps Script mutators with cleanup.

### Important Notes
1. `create_deployment` requires explicit `version_number >= 1`.
2. Drive-backed list/delete tools affect standalone script files only, not container-bound scripts.
3. `run_script_function` can return environment/runtime 404 for scripts that are not execution-ready in the active Apps Script environment.
