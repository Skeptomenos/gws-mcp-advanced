# PKCE Code Verifier Investigation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove the root cause of the callback-flow PKCE `code_verifier` failure, rule out nearby false leads, implement the smallest safe remediation, and carry the fix through validation and release preparation.

**Architecture:** The investigation follows the callback auth path end to end: auth challenge creation in `auth/google_auth.py`, OAuth state persistence in `auth/oauth21_session_store.py`, manual callback completion in `core/server.py`, and callback handling in `auth/google_auth.py`. Evidence comes from source tracing, targeted unit-test review, and hermetic runtime probes against the installed OAuth library and local repo code.

**Tech Stack:** Python 3.10+, `uv`, `pytest`, `google-auth-oauthlib`, GitHub issue evidence, local repo runtime

---

## Living Document Controls

- Status: `IN_PROGRESS`
- Last Updated (UTC): `2026-03-12T06:50:40Z`
- Canonical Path: `docs/plans/2026-03-11-pkce-code-verifier-investigation.md`
- Active Branch: `fix/pkce-code-verifier-investigation`
- Scope: `Root cause + fix implementation + release prep`
- Out of Scope: `Unrelated broad refactors`

## Investigation Questions

1. Where is PKCE generated in the current callback flow?
2. Is `code_verifier` stored anywhere durable between auth initiation and callback completion?
3. Does callback handling reconstruct a fresh OAuth flow that no longer has the original PKCE material?
4. Are config path resolution or callback state consumption creating a misleading symptom instead of the real root cause?
5. What is the smallest safe remediation that preserves the existing auth stabilization design?

## Task 1: Trace the Current Callback Flow

**Files:**
- Modify: `docs/plans/2026-03-11-pkce-code-verifier-investigation.md`
- Read: `auth/google_auth.py`
- Read: `auth/oauth21_session_store.py`
- Read: `core/server.py`
- Read: `tests/unit/auth/test_session_store.py`
- Read: `tests/unit/auth/test_oauth_state_persistence.py`

**Step 1: Map auth initiation path**

Identify where callback auth starts, where state is generated, and what metadata is persisted.

**Step 2: Map callback completion path**

Identify where callback data is validated, where the OAuth flow is rebuilt, and when the state is consumed.

**Step 3: Compare persisted state schema to callback needs**

Write down which fields are available during callback handling and which fields are missing.

## Task 2: Prove PKCE Library Behavior Hermetically

**Files:**
- Modify: `docs/plans/2026-03-11-pkce-code-verifier-investigation.md`

**Step 1: Inspect installed OAuth library behavior**

Confirm whether `authorization_url()` creates PKCE state on the flow instance and whether `fetch_token()` later depends on that state.

**Step 2: Reproduce the state-loss condition locally**

Use a hermetic Python probe with a dummy client config to show whether a new flow instance lacks the original `code_verifier` even when the callback URL still has the same `state`.

**Step 3: Record exact evidence**

Capture the observed URL/query params, flow-instance fields, and any source excerpts that prove the failure mechanism.

## Task 3: Check Adjacent Risks Without Scope Creep

**Files:**
- Modify: `docs/plans/2026-03-11-pkce-code-verifier-investigation.md`
- Read: `docs/setup/AUTHENTICATION_MODEL.md`
- Read: `agent-docs/roadmap/AUTH_STABILIZATION_PLAN.md`

**Step 1: Verify persistence-path design is already unified**

Confirm whether current code and tests support one shared config path model.

**Step 2: Verify callback state consumption semantics**

Confirm whether state is intentionally consumed only after successful callback processing, and whether that behavior is a separate concern from the PKCE failure.

**Step 3: Verify refresh-token fallback is adjacent, not causal**

Confirm whether refresh-before-reauth behavior is a separate improvement area rather than the direct cause of this bug.

## Task 4: Produce Fix Strategy and Validation Plan

**Files:**
- Modify: `docs/plans/2026-03-11-pkce-code-verifier-investigation.md`

**Step 1: State the root cause in one sentence**

The statement must name the origin of PKCE generation, the missing persisted field, and the exact handoff boundary where the verifier is lost.

**Step 2: Define the smallest safe remediation**

Describe the minimum code and test changes needed, without implementing them in this pass.

**Step 3: Define validation gates**

List the unit, integration, and runtime checks required before any later patch can be considered complete.

## Evidence Log

- 2026-03-11: Investigation branch created: `fix/pkce-code-verifier-investigation`.
- 2026-03-11: Live investigation document created and set as source of truth for this debugging pass.
- 2026-03-11: Initial code review shows `start_auth_flow()` persists OAuth state through `store_oauth_state(...)`, while `handle_auth_callback()` validates state and rebuilds a fresh flow before calling `fetch_token(...)`.
- 2026-03-11: Initial code review shows `store_oauth_state(...)` currently persists `session_id`, `oauth_client_key`, `expected_user_email`, `redirect_uri`, `expires_at`, and `created_at`, but no PKCE material.
- 2026-03-11: Verified current repo lockfile pins `google-auth-oauthlib==1.2.4` in `uv.lock`, while the published `google-workspace-mcp-advanced==1.0.5` environment resolves `google-auth-oauthlib==1.3.0`.
- 2026-03-11: Inspected local `google-auth-oauthlib==1.2.4` source in the repo venv. `Flow.from_client_config(...)` pops `autogenerate_code_verifier` with default `None`, so `Flow.__init__` receives `autogenerate_code_verifier=None`; `authorization_url()` therefore does not auto-generate PKCE and the resulting auth URL has no `code_challenge`.
- 2026-03-11: Inspected published `google-auth-oauthlib==1.3.0` source under `uv run --with google-workspace-mcp-advanced==1.0.5`. In that version, `Flow.from_client_config(...)` defaults `autogenerate_code_verifier=True`; the resulting auth URL includes `code_challenge` and `code_challenge_method=S256`, and `flow.code_verifier` is populated after `authorization_url()`.
- 2026-03-11: Proved with a hermetic probe that a fresh `Flow` instance created for callback handling has `code_verifier=None` unless the original verifier is explicitly supplied. The subsequent `fetch_token(...)` call forwards `code_verifier=None`.
- 2026-03-11: Proved with a hermetic state-persistence probe that even when a flow instance has a generated `code_verifier`, `start_auth_flow()` persists only `session_id`, `oauth_client_key`, `expected_user_email`, `redirect_uri`, `expires_at`, and `created_at`; `oauth_states.json` does not contain `code_verifier`.
- 2026-03-11: Proved with a published-package probe (`google-workspace-mcp-advanced==1.0.5`) that `start_auth_flow()` emits a callback URL containing `code_challenge`/`S256` but still persists no `code_verifier`, matching the GitHub issue report.
- 2026-03-11: Re-ran targeted state tests in the repo: `uv run pytest tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_session_store.py -q` => `39 passed`. Current tests validate state persistence semantics but do not assert PKCE persistence.
- 2026-03-11: Re-ran integration auth tests in the repo: `uv run pytest tests/integration/test_auth_flow.py -q` => `11 passed`. Existing integration coverage confirms refresh-before-reauth behavior is working separately from callback PKCE handling.
- 2026-03-11: Verified auth stabilization docs and tests already encode unified persistence-path behavior (`WORKSPACE_MCP_CONFIG_DIR` with legacy override support) and validate non-consuming state validation followed by explicit consume-after-success semantics.
- 2026-03-11: Started implementation after approved design. Added a focused PKCE normalization regression test at `tests/unit/auth/test_google_auth_pkce.py` asserting that `create_oauth_flow(...).authorization_url(...)` emits `code_challenge` and `S256`.
- 2026-03-11: Verified RED before dependency normalization: `uv run pytest tests/unit/auth/test_google_auth_pkce.py -q` => `1 failed`, proving local `google-auth-oauthlib==1.2.4` did not match published PKCE behavior.
- 2026-03-11: Normalized local auth dependency behavior by pinning `google-auth-oauthlib==1.3.0` in `pyproject.toml` and refreshing `uv.lock` with `uv lock`, then syncing with `uv sync --extra dev`.
- 2026-03-11: Verified normalization result immediately: `uv run pytest tests/unit/auth/test_google_auth_pkce.py -q` => `1 passed`. Local dev now reproduces the same PKCE autogeneration behavior as the published `1.0.5` runtime.
- 2026-03-11: Added failing regression coverage for the actual bug shape in `tests/unit/auth/test_session_store.py`, `tests/unit/auth/test_oauth_state_persistence.py`, and `tests/unit/auth/test_google_auth_flow_modes.py`.
- 2026-03-11: Verified RED for the real fix slice: `uv run pytest tests/unit/auth/test_session_store.py tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_google_auth_flow_modes.py -q` => `3 failed, 57 passed`.
- 2026-03-11: New finding from the RED run: `OAuth21SessionStore.store_oauth_state(...)` currently rejects a `code_verifier` parameter entirely, confirming the persistence contract itself is missing PKCE support rather than merely failing to serialize an existing field.
- 2026-03-11: Implemented the first GREEN slice by extending the OAuth state contract and callback flow wiring: `create_oauth_flow(...)` now accepts `code_verifier`, `start_auth_flow()` captures `flow.code_verifier`, `store_oauth_state(...)` accepts and stores it, and `handle_auth_callback()` rehydrates the flow with the stored verifier.
- 2026-03-11: First GREEN attempt narrowed the failure to disk serialization only: in-memory state accepted `code_verifier`, but `_save_oauth_states_to_disk()` still dropped the field. This was fixed by extending the serialized state payload.
- 2026-03-11: Verified focused GREEN after the serializer fix: `uv run pytest tests/unit/auth/test_session_store.py tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_google_auth_pkce.py -q` => `61 passed`.
- 2026-03-12: Re-ran auth integration verification: `uv run pytest tests/integration/test_auth_flow.py -q` => `11 passed`.
- 2026-03-12: Re-ran lint verification: `uv run ruff check .` => `All checks passed!`.
- 2026-03-12: Re-ran formatting verification: `uv run ruff format --check .` => `166 files already formatted`.
- 2026-03-12: Re-ran full repo verification: `uv run pytest` => `1 failed, 737 passed, 3 skipped`.
- 2026-03-12: Investigated the lone failing test `tests/opencode/test_opencode_serve_smoke.py`. It is unrelated to the PKCE change set. The failure reproduces outside pytest via `bash scripts/opencode_serve_smoke.sh` and returns `401 Unauthorized` from `/global/health`.
- 2026-03-12: Root cause of the unrelated smoke failure: the local shell environment has `OPENCODE_SERVER_PASSWORD` and `OPENCODE_SERVER_USERNAME` set, so `opencode serve` is intentionally protected by HTTP basic auth. The smoke script curls `/global/health` without credentials, so it times out despite the server starting correctly. This failure is environmental and pre-existing with the current local shell environment, not caused by the PKCE code or dependency normalization changes.
- 2026-03-12: Fixed the unrelated smoke script by making `scripts/opencode_serve_smoke.sh` pass HTTP basic auth credentials to `curl` when `OPENCODE_SERVER_PASSWORD` is set in the environment.
- 2026-03-12: Verified the smoke-test fix directly: `uv run pytest tests/opencode/test_opencode_serve_smoke.py -q` => `1 passed`.
- 2026-03-12: Re-ran the full suite after the smoke fix: `uv run pytest` => `738 passed, 3 skipped`.
- 2026-03-12: Performed a narrow breadcrumb/dead-code cleanup in `auth/google_auth.py`: removed stale inline change-history comments around `redirect_uri` handling and deleted the unused `session_info_for_llm` variable, keeping behavior unchanged.
- 2026-03-12: Re-ran post-cleanup verification end to end: `uv run ruff check .` => `All checks passed!`; `uv run ruff format --check .` => `166 files already formatted`; `uv run pytest` => `738 passed, 3 skipped`.
- 2026-03-12: Scope expanded after implementation success: the live document now also tracks branch review preparation and release publication planning for the PKCE fix.
- 2026-03-12: Release prep review found `.github/workflows/release-pypi.yml` enforces `pyproject.toml`/`package.json` version coupling and runs `ruff`, `ruff format --check`, `pyright`, and full `pytest` before publish. Any release bump must also update pinned `uvx` examples in user-facing docs.
- 2026-03-12: Prepared release artifact updates for `1.0.6`: bumped `pyproject.toml` and `package.json`, refreshed `uv.lock`, added a `docs/RELEASE_NOTES.md` entry for the PKCE fix, and updated pinned `uvx` examples in README/setup/distribution docs.
- 2026-03-12: Re-ran release-grade verification after the `1.0.6` prep changes: `uv run python scripts/check_release_version_match.py` => pass, `uv run python scripts/check_distribution_scope.py` => pass, `uv run pytest -q tests/unit/core/test_distribution_checks.py` => `5 passed`, `uv run ruff check .` => pass, `uv run ruff format --check .` => `166 files already formatted`, `uv run pyright --project pyrightconfig.json` => `0 errors`, `uv run pytest -q` => `738 passed, 3 skipped`.

## Current Findings

- The GitHub issue is real for the published `1.0.5` package path: PKCE is generated by the OAuth library during auth URL creation, but the original `code_verifier` exists only on the in-memory `Flow` instance.
- Local dev is now normalized to the production-relevant auth behavior by pinning `google-auth-oauthlib==1.3.0`; subsequent debugging and regression tests can target the real PKCE path instead of a masked local variant.
- `start_auth_flow()` stores callback correlation metadata in `oauth_states.json` but does not persist the original `code_verifier`.
- `handle_auth_callback()` later reconstructs a new `Flow` from persisted metadata and calls `fetch_token(...)`; because the new flow has no original verifier, token exchange sends `code_verifier=None`.
- This exactly explains `(invalid_grant) Missing code verifier` during `complete_google_auth` or any callback-completion path that does not reuse the original flow object.
- The local dev environment currently masks the published symptom because its locked `google-auth-oauthlib==1.2.4` does not auto-generate PKCE through `create_oauth_flow(...)` at all. That is a separate dependency-drift concern, not a refutation of the root cause.
- Config-path divergence is not the primary cause here: path unification is already implemented and covered. Callback state consumption is also not the primary cause: the code validates state without consuming it and only removes it after successful callback processing. Refresh-before-reauth behavior is adjacent and already covered by tests.
- The implemented fix is behaving as intended under focused and integration auth verification. The remaining full-suite failure is a local OpenCode server-auth environment issue, not a regression in this branch.
- The OpenCode serve smoke regression was addressed separately and verified; the branch is ready for a fresh full-suite run before cleanup work.
- The branch remains green after the narrow cleanup pass; no additional dead code or breadcrumb cleanup was performed outside the touched auth path and the OpenCode smoke script.
- Release publication is now a live follow-on concern: this repo couples Python and npm package versions during release verification, and the PyPI workflow expects a fresh `pyright` run in addition to the standard local quality gates.
- The branch is now locally release-ready for `1.0.6`; the remaining operational steps are branch push/PR creation and deciding whether PyPI publication should happen from this branch or after merge to `main`.

## Candidate Fix Strategy

- Smallest safe remediation:
  1. capture `flow.code_verifier` immediately after `authorization_url(...)` in `start_auth_flow()`;
  2. extend `OAuth21SessionStore.store_oauth_state(...)` and persisted-state schema to include `code_verifier`;
  3. in `handle_auth_callback()`, read `code_verifier` from validated state and pass it into `create_oauth_flow(...)` so the rehydrated flow sends the original verifier during `fetch_token(...)`.
- Defensive follow-up: add a callback-path error if PKCE is expected by the stored auth challenge but `code_verifier` is absent, so operators get a deterministic local error before a Google `invalid_grant` response.
- Compatibility note: the stored verifier is transient challenge state, not a long-lived credential, so it belongs in `oauth_states.json` alongside `state` and `redirect_uri`, with the same expiry/cleanup semantics.
- Secondary remediation to evaluate after the primary fix: pin or upgrade `google-auth-oauthlib` behavior consciously, because local dev (`1.2.4`) and published runtime (`1.3.0`) currently differ in PKCE autogeneration behavior.

## Validation Plan

- Add a unit test proving `store_oauth_state(...)` persists `code_verifier` and reloads it from disk.
- Add a unit test proving `handle_auth_callback()` rehydrates the flow with the stored verifier and that `fetch_token(...)` receives that verifier.
- Add a regression test for the published failure shape: callback URL contains `code_challenge`, persisted state includes `code_verifier`, and callback completion does not send `None`.
- Re-run targeted suites: `uv run pytest tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_session_store.py tests/unit/auth/test_google_auth_flow_modes.py -q`.
- Re-run auth integration coverage: `uv run pytest tests/integration/test_auth_flow.py -q`.
- Re-run repo quality gate before any future patch is considered done: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`.
- Re-run release-specific preflight before publication work: `uv run python scripts/check_release_version_match.py`, `uv run python scripts/check_distribution_scope.py`, `uv run pytest -q tests/unit/core/test_distribution_checks.py`, `uv run pyright --project pyrightconfig.json`.
- Runtime smoke after patch: use the repo-local OpenCode MCP entry, initiate callback auth, inspect the generated auth URL for PKCE, complete callback via `complete_google_auth`, and confirm no `Missing code verifier` error occurs.
