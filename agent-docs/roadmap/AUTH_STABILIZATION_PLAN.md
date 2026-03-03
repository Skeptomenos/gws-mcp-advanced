# ExecPlan: Authentication Stabilization (Production + Enterprise)

## Living Document Controls
- Status: `DONE_AUTH_STABILIZATION_SCOPE`
- Last Updated (UTC): `2026-03-03T10:40:00Z`
- Canonical Path: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/AUTH_STABILIZATION_PLAN.md`
- Parent Plan: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`
- Active Branch: `main`
- Owner: `Codex`
- Severity: `P0` (auth bootstrap/re-auth reliability)

## Source of Truth and Update Rules
1. This file is the source of truth for authentication stabilization scope, status, risks, and evidence.
2. Update this file immediately after each completed subtask.
3. Update this file before any pause, handoff, or context switch.
4. Update this file before commit, push, and release steps.
5. If this file conflicts with `PLAN.md`, reconcile both in the same session.

## Problem Statement
Authentication bootstrap/re-auth behavior in MCP-hosted stdio environments is not reliable enough for production use.

Observed failure themes:
1. Manual auth entrypoint (`start_google_auth`) does not guarantee callback server readiness in stdio mode.
2. OAuth state/session persistence paths can diverge from configured credentials path.
3. Callback state consumption behavior can obscure root cause when callback processing fails.
4. Existing credential-file fallback/refresh behavior needs explicit coverage and diagnostics evidence.
5. A callback-only path is fragile in some MCP host lifecycle models; a callback-independent fallback path is required.
6. One MCP process currently uses one global OAuth client config; enterprise/private mixed-tenant operation in one MCP requires per-account/per-domain OAuth client routing.

## Goals
1. Make first-time auth and re-auth deterministic in stdio MCP hosts.
2. Ensure all auth persistence uses one directory model (with backward-compatible override support).
3. Keep callback flow secure and replay-safe while improving operational debuggability.
4. Add a fallback auth mode that does not require a localhost callback roundtrip.
5. Ship a new PyPI version with clear rollout, verification, and rollback guidance.
6. Support single-MCP multi-client authentication for enterprise/private tenant coexistence with credential/session isolation.

## Non-Goals
1. Rebuilding external OAuth provider integration architecture.
2. Introducing breaking changes to existing tool interfaces unless explicitly required.
3. Removing callback flow; callback remains supported.
4. Requiring two MCP server entries as the long-term tenant strategy.

## Workstreams and Tasks

### WS-01 Callback Flow Reliability
- [x] WS-01.1 Add shared redirect resolver that guarantees callback readiness in stdio mode.
- [x] WS-01.2 Use shared resolver in auto-auth path (`get_authenticated_google_service`).
- [x] WS-01.3 Use shared resolver in manual-auth tool (`start_google_auth`).
- [x] WS-01.4 Ensure message output always reflects the actual active callback URI.
- [x] WS-01.5 Add regression tests for manual and automatic auth parity.

### WS-02 Persistence Path Unification
- [x] WS-02.1 Unify OAuth state/session persistence with `WORKSPACE_MCP_CONFIG_DIR` path model.
- [x] WS-02.2 Preserve `GOOGLE_MCP_CREDENTIALS_DIR` override for backward compatibility.
- [x] WS-02.3 Add regression tests proving shared path behavior.
- [x] WS-02.4 Add migration/compatibility notes in docs.

### WS-03 Callback State Handling and Error Clarity
- [x] WS-03.1 Split state validation and consumption semantics (validate first, consume after success).
- [x] WS-03.2 Preserve session-mismatch replay protection.
- [x] WS-03.3 Improve callback error messages to avoid misleading follow-up states.
- [x] WS-03.4 Add tests for success, mismatch, retryable failure, and consumed-state replay.

### WS-04 Credentials Read/Refresh Confidence
- [x] WS-04.1 Add integration tests for loading credentials from disk path configured by env.
- [x] WS-04.2 Add integration tests for expired token refresh path before re-auth fallback.
- [x] WS-04.3 Add diagnostics improvements for credential source selection.
- [x] WS-04.4 Update docs with concrete expected credential file location and format.

### WS-05 Device Flow Fallback (Callback-Independent)
- [x] WS-05.1 Add auth mode flag (`WORKSPACE_MCP_AUTH_FLOW=auto|callback|device`).
- [x] WS-05.2 Implement device-code flow initiation for Google OAuth.
- [x] WS-05.3 Persist pending device-flow state across tool calls and process restarts.
- [x] WS-05.4 Poll/complete device flow on subsequent tool calls and persist credentials.
- [x] WS-05.5 Add guardrails for expired/denied/slowdown states and actionable user messages.
- [x] WS-05.6 Add unit/integration tests for device-flow lifecycle.

### WS-06 Release Readiness and Publication
- [x] WS-06.1 Run full verification protocol (`ruff check`, `ruff format --check`, `pytest`).
- [x] WS-06.2 Run targeted auth test suite and capture evidence.
- [x] WS-06.3 Update user docs (auth modes, enterprise rollout, troubleshooting).
- [x] WS-06.4 Bump version and prepare release notes.
- [x] WS-06.5 Publish to PyPI and verify `uvx` install path.
- [x] WS-06.6 Post-release smoke validation in MCP hosts. **DONE** — OP-74/OP-76 now pass in OpenCode host with persistence proof.

### WS-07 Single-MCP Multi-Client Authentication (New)
- [x] WS-07.1 Define and approve config schema for named OAuth clients (`oauth_clients`), account mapping (`account_clients`), domain mapping (`domain_clients`), and `selection_mode=mapped_only`.
- [x] WS-07.2 Implement setup bootstrap: auto-create `auth_clients.json` skeleton when missing and return actionable setup guidance.
- [x] WS-07.3 Implement OAuth client import path for setup (explicit import workflow; no free-text LLM secret authoring).
- [x] WS-07.4 Implement deterministic client resolution precedence (internal/admin override -> account map -> domain map -> default -> legacy env fallback) while honoring `mapped_only` hard-fail policy.
- [x] WS-07.5 Make auth challenge generation client-aware (device/callback/manual flow must use selected client context).
- [x] WS-07.6 Partition credential store by `(client, user)` with backward-compatible migration from flat per-email files.
- [x] WS-07.7 Extend OAuth session/state persistence to include client dimension and enforce `(client, user)` binding.
- [x] WS-07.8 Add headless-safe callback completion tool contract (`start_google_auth` + `complete_google_auth`) with persisted challenge state and hybrid input (`callback_url` primary, optional `code/state` fallback).
- [x] WS-07.9 Add full test matrix for multi-client routing/isolation/migration and mixed auth-flow behavior.
- [x] WS-07.10 Update user/operator docs for single-MCP multi-client setup and enterprise policy troubleshooting.

## Risk Register

| ID | Risk | Impact | Mitigation | Status |
|---|---|---|---|---|
| AUTH-R1 | Regression in existing callback auth | High | Keep callback path, add parity tests, gate on full suite | Mitigated |
| AUTH-R2 | Device flow unsupported for current OAuth client type (Web application) | High | Auto fallback in `auto` mode (`device invalid_client -> callback`) plus explicit flow override/docs | Mitigated (code + tests + OpenCode runtime evidence) |
| AUTH-R3 | Session/state migration breaks existing installations | Medium | Backward-compatible env override path + migration tests | Mitigated |
| AUTH-R4 | Ambiguous auth errors reduce operator confidence | Medium | Structured error messages + diagnostics coverage | Mitigated |
| AUTH-R5 | Release drift between docs and code | Medium | Update docs in same PR and run release checklist | Partial |
| AUTH-R6 | Multi-client credential mixing or cross-tenant session reuse | High | Partition credential/session storage by client and enforce `(client, user)` binding validation | Mitigated (code/tests + OpenCode runtime validation) |
| AUTH-R7 | Ambiguous client resolution causes wrong OAuth client selection | High | Deterministic precedence + `mapped_only` hard-fail policy + diagnostics logging + config validation at startup | Mitigated (code/tests + OpenCode runtime validation) |
| AUTH-R8 | Breaking migration from legacy per-email credential files | Medium | Read-through migration + compatibility fallback + explicit migration tests/runbook | Mitigated in code/tests; pending operator docs finalization |
| AUTH-R9 | Tenant OAuth client lifecycle drift (deleted/disabled client in GCP) blocks one tenant while another passes | High | Add runtime preflight that probes mapped clients and surfaces actionable remediation (`import_google_auth_client` with a valid replacement JSON) | Mitigated (private mapping repaired with valid local client credentials) |

## Test and Evidence Matrix

| Area | Test Type | Command / Location | Pass Criteria | Status |
|---|---|---|---|---|
| Callback parity | Unit/Integration | `tests/unit/auth/test_google_auth_flow_modes.py` | Manual and auto auth delegate to shared auth-challenge orchestration path | Pass |
| Persistence path | Unit/Integration | `tests/unit/auth/test_oauth_state_persistence.py`, `tests/unit/auth/test_session_store.py` | State/session files resolve to configured dir | Pass |
| State semantics | Unit | `tests/unit/auth/test_session_store.py`, `tests/unit/auth/test_oauth_state_persistence.py` | Validate/consume behavior matches contract | Pass |
| Credential refresh | Integration | `tests/integration/test_auth_flow.py` | Expired credentials refresh before re-auth | Pass |
| Credential source diagnostics | Unit | `tests/unit/auth/test_auth_runtime_paths.py` | Credential source selection emits deterministic diagnostics (`[CRED_SOURCE] ...`) | Pass |
| Release installability | Runtime smoke | `uvx --from google-workspace-mcp-advanced==1.0.1 google-workspace-mcp-advanced --help` | Published package can be resolved/launched via uvx | Pass |
| Device flow | Unit/Integration (mocked HTTP) | `tests/unit/auth/test_google_auth_flow_modes.py` | Device lifecycle stable across retries | Pass (unit) |
| Full quality gate | Repo-wide | `uv run ruff check . && uv run ruff format --check . && uv run pytest` | All green | Pass |
| Post-release smoke (stdio) | Runtime smoke | OpenCode MCP host, `uvx google-workspace-mcp-advanced==1.0.1 --transport stdio` + direct runtime probes | Protected tool triggers auth, auth completes, retry succeeds, second tool confirms persistence | **PASS** — OP-74/OP-76 runtime matrix passed with persistence proof |
| Credential file loading | Runtime smoke | `get_credentials()` with on-disk credential file | Credential store finds and loads `david.helmus@hellofresh.com.json` from configured dir | **PASS** — `[CRED_SOURCE] source=file_store found=True` |
| Token refresh (revoked grant) | Runtime smoke | `credentials.refresh(Request())` with expired/revoked refresh token | Refresh returns `RefreshError` and triggers re-auth flow | **PASS** — `invalid_grant: Bad Request` correctly triggers re-auth |
| Device flow (Web client) | Runtime smoke | `initiate_auth_challenge()` with `auto` mode (stdio → device) | Device flow initiation with Web OAuth client | **FAIL** — `invalid_client: Invalid client type` |
| Callback flow (Web client) | Runtime smoke | `initiate_auth_challenge()` with `WORKSPACE_MCP_AUTH_FLOW=callback` | Callback server starts, auth URL generated, flow initiates | **PASS** — callback server on `localhost:9890`, valid auth URL |
| Multi-client routing | Unit/Integration | `tests/unit/auth/test_oauth_clients.py` + `tests/unit/auth/test_session_store.py` + `tests/integration/test_auth_flow.py` | selected OAuth client matches account/domain mapping deterministically | Pass |
| Multi-client runtime setup/routing | Runtime smoke | `setup_google_auth_clients` + `import_google_auth_client` + `start_google_auth` probes | One MCP entry routes tenant auth to mapped OAuth clients; mismatch hard-fails; no dual-server requirement | Pass |
| Multi-client credential isolation | Unit/Integration | `tests/unit/auth/test_credential_store.py` + `tests/unit/auth/test_session_store.py` | credentials for two users on different clients never collide in storage/refresh; legacy read-through migration works | Pass |
| Manual callback completion | Unit/Integration/Runtime smoke | `tests/unit/auth/test_google_auth_flow_modes.py` + OpenCode smoke (`complete_google_auth`) | auth can complete in MCP-hosted lifecycles without relying on long-lived localhost callback timing | Pass (runtime: callback-server auto-complete path + persisted credentials confirmed) |

## Implementation Log (Append-Only)
- 2026-03-02T16:10:16Z: Created dedicated auth stabilization living plan with workstreams WS-01..WS-06.
- 2026-03-02T16:10:16Z: Confirmed active implementation already started in `auth/oauth21_session_store.py` for persistence/state hardening.
- 2026-03-02T16:31:22Z: Completed auth-flow orchestration refactor: unified `initiate_auth_challenge` path for auto/manual flows with `WORKSPACE_MCP_AUTH_FLOW` mode selection (`auto|device|callback`).
- 2026-03-02T16:31:22Z: Added persistent pending device-flow state in `OAuth21SessionStore` with disk-backed recovery and expiry cleanup.
- 2026-03-02T16:31:22Z: Added non-consuming OAuth state validation + explicit consumption after successful callback handling.
- 2026-03-02T16:31:22Z: Added auth unit coverage (`tests/unit/auth/test_google_auth_flow_modes.py`) and expanded session/state persistence coverage.
- 2026-03-02T16:31:22Z: Ran full quality gate successfully: `ruff check .`, `ruff format .`, `pytest` (`628 passed`, `3 skipped`).
- 2026-03-02T16:31:22Z: Updated user auth docs (`README.md`, `docs/setup/MCP_CLIENT_SETUP_GUIDE.md`, `docs/setup/AUTHENTICATION_MODEL.md`) to document device-flow default and auth mode flag.
- 2026-03-02T21:34:45Z: Bumped release version to `1.0.1` (`pyproject.toml`, `package.json`, `uv.lock`) and updated pinned user-doc examples.
- 2026-03-02T21:34:45Z: Tagged and pushed `v1.0.1` (`86b6b04`) to trigger `.github/workflows/release-pypi.yml`.
- 2026-03-02T21:34:45Z: GitHub/PyPI API verification is blocked in this environment due restricted outbound DNS/network; publish confirmation must be validated from CI UI or external shell.
- 2026-03-03T00:20:00Z: Closed WS-01.5 and WS-04.1/WS-04.2/WS-04.3 by adding manual+automatic auth parity regressions, env-path credential-store integration coverage, refresh-before-reauth integration coverage, and credential-source diagnostics in `auth/google_auth.py`.
- 2026-03-03T00:20:00Z: Ran targeted auth suite (`29 passed`) and full verification protocol (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`) with green results (`633 passed`, `3 skipped`).
- 2026-03-03T00:20:00Z: Closed WS-06.5 by validating published installability/execution path with `uvx --from google-workspace-mcp-advanced==1.0.1 google-workspace-mcp-advanced --help`.
- 2026-03-03T15:00:00Z: **WS-06.6 Post-release smoke validation executed in OpenCode** (MCP config: `uvx google-workspace-mcp-advanced==1.0.1 --transport stdio`).
- 2026-03-03T15:00:00Z: Smoke step 1 — `list_calendars` triggered auth. Credential file found on disk at `~/.config/google-workspace-mcp-advanced/credentials/david.helmus@hellofresh.com.json` (`[CRED_SOURCE] source=file_store found=True`). Token expired (`expiry: 2026-02-04`). Refresh failed: `RefreshError('invalid_grant: Bad Request')` — refresh token revoked/expired.
- 2026-03-03T15:00:00Z: Smoke step 2 — `get_credentials` returned `None` (expired + refresh failed). `initiate_auth_challenge` entered device flow (effective mode: `device` in stdio). Device flow failed: `invalid_client: Invalid client type` — OAuth client is Web application type, device grant not supported. This confirms AUTH-R2 is live.
- 2026-03-03T15:00:00Z: Smoke step 3 — Manual `start_google_auth` tool also failed with same `invalid_client` error (both auto and manual paths use shared `initiate_auth_challenge` — WS-01 parity confirmed).
- 2026-03-03T15:00:00Z: Smoke step 4 — Callback flow validated separately with `WORKSPACE_MCP_AUTH_FLOW=callback`: callback server started on `localhost:9890`, valid Google OAuth authorization URL generated. Callback flow is functional when explicitly selected.
- 2026-03-03T15:00:00Z: **Root cause**: `_get_effective_auth_flow_mode()` (`auth/google_auth.py:151`) returns `device` for `auto+stdio`, but the HelloFresh OAuth client (`684416038148-...`) is a "Web application" type that does not support device authorization grant. Either (a) the `auto` mode needs a device-flow probe/fallback-to-callback, or (b) users with Web OAuth clients must set `WORKSPACE_MCP_AUTH_FLOW=callback`.
- 2026-03-03T15:00:00Z: **Partial passes**: credential file loading (PASS), credential store path resolution (PASS), scope matching (PASS), callback flow initiation (PASS), error message clarity (PASS — `invalid_client` surfaced clearly). **Failures**: end-to-end auth completion in default stdio mode (FAIL — blocked by AUTH-R2).
- 2026-03-03T07:59:39Z: Expanded scope to include `AUTH-02` single-MCP multi-client architecture (informed by `gogcli` auth client pattern review). Dual-server tenant split is now documented as temporary workaround only; target design is one MCP with per-account/per-domain client routing and `(client,user)` credential/session isolation.
- 2026-03-03T08:13:37Z: Policy decisions locked: `selection_mode=mapped_only`, hard-fail on domain/client mismatch, and no cross-client fallback. Setup flow decision locked: auto-bootstrap `auth_clients.json` skeleton + explicit OAuth client import path for secrets.
- 2026-03-03T08:20:06Z: Additional policy decisions locked: explicit client override remains internal/admin-only (not user-facing in normal tool calls), and `complete_google_auth` contract is hybrid (`callback_url` primary, optional `code/state` fallback).
- 2026-03-03T08:26:45Z: Implemented AUTH-R2 mitigation in `auth/google_auth.py`: when `WORKSPACE_MCP_AUTH_FLOW=auto` and device flow returns `invalid_client`, auth now automatically falls back to callback flow (explicit `device` mode still hard-fails).
- 2026-03-03T08:26:45Z: Added regression coverage for fallback behavior in `tests/unit/auth/test_google_auth_flow_modes.py` (initiation and poll paths) and explicit-device no-fallback behavior. Targeted suite: `13 passed`.
- 2026-03-03T08:42:50Z: Implemented WS-07.1..WS-07.9 in code: added `auth/oauth_clients.py` resolver + bootstrap/import flows, client-aware auth challenge orchestration in `auth/google_auth.py`, client-scoped credential store paths with legacy read-through migration in `auth/credential_types/store.py`, and client-aware state/session persistence in `auth/oauth21_session_store.py`.
- 2026-03-03T08:42:50Z: Added setup/admin tools in `core/server.py`: `setup_google_auth_clients`, `import_google_auth_client`, and `complete_google_auth`.
- 2026-03-03T08:42:50Z: Added spec and tests for multi-client and completion flows: `specs/AUTH_MULTI_CLIENT_SINGLE_MCP_SPEC.md`, `tests/unit/auth/test_oauth_clients.py`, and extended auth/session/tool regression coverage.
- 2026-03-03T08:42:50Z: Full verification protocol is green after implementation (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` => `647 passed`, `3 skipped`).
- 2026-03-03T08:45:55Z: Closed WS-07.10 docs by publishing `docs/setup/MULTI_CLIENT_AUTH_SETUP.md` and updating `README.md`, `docs/INDEX.md`, `docs/setup/MCP_CLIENT_SETUP_GUIDE.md`, and `docs/setup/AUTHENTICATION_MODEL.md` with multi-client setup/operator guidance.
- 2026-03-03T08:48:40Z: Added unit coverage for admin import tool contract and re-ran full suite (`648 passed`, `3 skipped`) to refresh baseline after WS-07 test additions.
- 2026-03-03T09:04:53Z: Executed runtime prep for WS-07 using local tools against `~/.config/google-workspace-mcp-advanced`: `setup_google_auth_clients`, then imported two mapped clients (`private`, `enterprise`) with account/domain bindings via `import_google_auth_client`.
- 2026-03-03T09:04:53Z: Verified AUTH-R2 live in runtime (non-mocked): in `auto+stdio`, a Web-client `invalid_client` device-flow error now auto-falls back to callback flow and returns actionable OAuth URL (enterprise domain probe).
- 2026-03-03T09:04:53Z: Verified hard-fail mismatch policy live: forcing `hellofresh.com` user onto `private` client returns explicit no-fallback domain/client mismatch error.
- 2026-03-03T09:04:53Z: Discovered external tenant blocker `AUTH-R9`: mapped `private` OAuth client currently returns `deleted_client: The OAuth client was deleted`, preventing OP-74/OP-76 completion for private tenant until client JSON is replaced.
- 2026-03-03T09:07:57Z: Repaired `AUTH-R9` by re-importing `private` client mapping with known-good local credentials (from active OpenCode MCP environment), preserving `account_clients`/`domain_clients` hard bindings for `helmus.me`.
- 2026-03-03T09:07:57Z: Re-ran runtime routing probe: private lane now produces callback URL with `client_id=684416...`; enterprise lane produces callback URL with `client_id=499833...`; both in one MCP entry with `auto+stdio` fallback behavior intact.
- 2026-03-03T09:09:39Z: Final sanity check confirms `~/.config/google-workspace-mcp-advanced/auth_clients.json` is consistent (`selection_mode=mapped_only`, clients `private`/`enterprise`, account + domain mappings persisted) and runtime/docs are aligned to a single remaining closeout step: OP-74/OP-76 manual callback completion evidence in OpenCode.
- 2026-03-03T10:24:00Z: OpenCode runtime closeout completed: OP-74 PASS (single MCP entry authenticated both tenants with distinct clients and callback flow where needed) and OP-76 PASS (credentials persisted; `list_calendars` succeeded with no re-auth prompts for both tenants).
- 2026-03-03T10:24:00Z: Observed expected callback-state behavior: for enterprise lane, `complete_google_auth` returned `Invalid or expired OAuth state parameter` after browser redirect because callback server already consumed the state and persisted tokens. This is valid callback-server auto-completion behavior, not a regression.
- 2026-03-03T10:35:00Z: Recovered distribution gate after `release-pypi.yml` type-check failure (`22617048674`) by fixing `OAuth21SessionStore` typing/protocol mismatches; local quality gate revalidated (`ruff`, `format --check`, `pyright`, `pytest` => `648 passed`, `3 skipped`).
- 2026-03-03T10:36:00Z: Re-dispatched `Release PyPI` workflow from `main` (`22618871138`, head `28509fc`) and confirmed full success (`verify`, `build`, `publish`).

## Open External Dependencies
1. None for auth stabilization scope.

## Next Execution Slice
1. **Operational hardening (P2)**: optionally add a clearer user-facing note when manual `complete_google_auth` is called after callback-server auto-consumption.
2. **Roadmap handoff (P3)**: continue with post-auth backlog (`RM-05`..`RM-07`) under the main execution plan.
