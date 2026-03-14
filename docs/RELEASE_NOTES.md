# Release Notes

## 2026-03-14 - Deterministic OAuth Callback and Auth Policy Stabilization

### Fixed
- Resolved callback auth policy before browser launch so one auth attempt now commits to one OAuth client, one flow, and one redirect policy.
- Stopped mapped `web` callback auth from silently falling back to unregistered localhost ports.
- Reused persisted OAuth challenge metadata during manual completion so restart or runtime redirect changes no longer cause callback completion to drift away from the original redirect URI.
- Restricted local callback server reuse to identical allowed redirect URIs so concurrent callback attempts fail closed instead of rebinding implicitly.

### Added
- Deterministic callback-port policy enforcement for mapped multi-client auth profiles.
- Auth decision diagnostics behind `AUTH_DIAGNOSTICS=1`.
- Regression coverage for callback policy resolution, callback server reuse rules, runtime diagnostics, and persisted OAuth completion state:
  - `tests/unit/auth/test_google_auth_flow_modes.py`
  - `tests/unit/auth/test_oauth_callback_server.py`
  - `tests/unit/auth/test_auth_runtime_paths.py`
  - `tests/unit/auth/test_oauth_state_persistence.py`

### Changed
- Mapped profiles loaded from `auth_clients.json` must preserve `client_type`; mapped `web` profiles must also preserve `redirect_uris` for local callback auth.
- `import_google_auth_client` is now the recommended way to populate mapped client config because it preserves the Google OAuth client metadata needed for deterministic callback policy.
- Local `installed` and legacy env-only auth still allow sequential localhost callback fallback, while mapped `web` auth now binds only to registered ports.

### Validation
- `uv run pytest tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_oauth_callback_server.py tests/unit/auth/test_auth_runtime_paths.py tests/unit/auth/test_oauth_state_persistence.py -q`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_oauth_callback_server.py tests/unit/auth/test_auth_runtime_paths.py tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_oauth_clients.py -v`
- `uv run pytest`

## 2026-03-12 - PKCE Callback Verifier Persistence + Release v1.0.6

### Fixed
- Persisted OAuth callback PKCE `code_verifier` state across auth initiation and callback completion.
- Rehydrated callback OAuth flows with the original verifier so token exchange no longer sends `code_verifier=None`.
- Updated the OpenCode serve smoke script to pass HTTP Basic Auth credentials automatically when `OPENCODE_SERVER_PASSWORD` is set in the environment.

### Added
- Regression coverage for PKCE callback persistence and callback flow rehydration:
  - `tests/unit/auth/test_google_auth_pkce.py`
  - `tests/unit/auth/test_google_auth_flow_modes.py`
  - `tests/unit/auth/test_oauth_state_persistence.py`
  - `tests/unit/auth/test_session_store.py`

### Changed
- Pinned `google-auth-oauthlib` to `1.3.0` so local development matches the published runtime's PKCE autogeneration behavior.
- Version bump to `1.0.6` in release artifacts:
  - `pyproject.toml`
  - `package.json`
  - `uv.lock`
- Updated pinned `uvx` examples in README and setup/distribution docs to `1.0.6`.

### Validation
- `uv run python scripts/check_release_version_match.py`
- `uv run python scripts/check_distribution_scope.py`
- `uv run pytest -q tests/unit/core/test_distribution_checks.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pyright --project pyrightconfig.json`
- `uv run pytest -q`

## 2026-03-05 - Search OAuth Scope Fix + Release v1.0.5

### Fixed
- Removed `https://www.googleapis.com/auth/cse` from OAuth scope aggregation.
- Removed `search` from `TOOL_SCOPES_MAP` so global auth no longer requests Custom Search scope.
- Removed `customsearch` scope group alias from `auth/service_decorator.py`.
- Updated Search tool decorators to require no OAuth scopes (`@require_google_service("customsearch", [])`), preserving API-key runtime auth model.

### Added
- Regression test coverage for scope policy:
  - `tests/unit/auth/test_search_scope_policy.py`
  - Asserts `cse` never appears in aggregated OAuth scopes.

### Changed
- Version bump to `1.0.5` in release artifacts:
  - `pyproject.toml`
  - `package.json`
  - `uv.lock`
- Updated pinned `uvx` examples in README and setup/distribution docs to `1.0.5`.

### Validation
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pyright --project pyrightconfig.json`
- `uv run pytest -q`

## 2026-03-05 - Cadence Workflow User Guide + Release v1.0.4

### Added
- User-facing cadence workflow documentation:
  - `docs/setup/LIVE_CADENCE_WORKFLOW.md`
- Operational runbook details for:
  - cadence trigger modes,
  - lane behavior (`mcp_protocol`, `live_mcp`, optional `live_write`),
  - cleanup safety model and invocation patterns.

### Changed
- Version bump to `1.0.4` in release artifacts:
  - `pyproject.toml`
  - `package.json`
- Updated pinned `uvx` examples in README and setup/distribution docs to `1.0.4`.

### Validation
- Local release gates passed before tagging:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pyright --project pyrightconfig.json`
  - `uv run pytest -q`

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
