# ExecPlan: Authentication Stabilization (Production + Enterprise)

## Living Document Controls
- Status: `IN_IMPLEMENTATION_PENDING_HOST_VALIDATION`
- Last Updated (UTC): `2026-03-03T00:30:00Z`
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

## Goals
1. Make first-time auth and re-auth deterministic in stdio MCP hosts.
2. Ensure all auth persistence uses one directory model (with backward-compatible override support).
3. Keep callback flow secure and replay-safe while improving operational debuggability.
4. Add a fallback auth mode that does not require a localhost callback roundtrip.
5. Ship a new PyPI version with clear rollout, verification, and rollback guidance.

## Non-Goals
1. Rebuilding external OAuth provider integration architecture.
2. Introducing breaking changes to existing tool interfaces unless explicitly required.
3. Removing callback flow; callback remains supported.

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
- [ ] WS-06.6 Post-release smoke validation in MCP hosts.

## Risk Register

| ID | Risk | Impact | Mitigation | Status |
|---|---|---|---|---|
| AUTH-R1 | Regression in existing callback auth | High | Keep callback path, add parity tests, gate on full suite | Mitigated |
| AUTH-R2 | Device flow unsupported for current OAuth client type | High | Feature flag mode, clear runtime error, docs for client requirements | Open |
| AUTH-R3 | Session/state migration breaks existing installations | Medium | Backward-compatible env override path + migration tests | Mitigated |
| AUTH-R4 | Ambiguous auth errors reduce operator confidence | Medium | Structured error messages + diagnostics coverage | Mitigated |
| AUTH-R5 | Release drift between docs and code | Medium | Update docs in same PR and run release checklist | Partial |

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

## Open Questions
1. Do we require a dedicated `start_google_device_auth_status` tool, or is retry-on-next-call sufficient operationally?
2. Should we add explicit telemetry counters for credential source choice (session/file/refresh/device-complete) before release?

## Next Execution Slice
1. Execute manual MCP-hosted auth validation in OpenCode/Claude Code using `WORKSPACE_MCP_AUTH_FLOW=auto` (optional forced `callback` sanity run).
2. Capture and attach post-release smoke evidence, then close WS-06.6.
