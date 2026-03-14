# Auth Reliability Remediation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Google Workspace auth deterministic, supportable, and testable across stdio and provider entrypoints by shipping a narrow Phase 1 hotfix first, then extracting explicit auth-policy/state seams, then simplifying the long-lived auth architecture.

**Architecture:** Work in three phases. Phase 1 stays inside the existing seams (`auth/google_auth.py`, `auth/oauth_callback_server.py`, `core/server.py`, `auth/oauth21_session_store.py`, `auth/diagnostics.py`) to stop wrong runtime behavior with minimal blast radius. Phase 2 introduces dataclass-based policy/state modules (`ResolvedAuthPlan`, flow policy, redirect policy, challenge helpers) and a broader auth matrix without changing the public tool surface. Phase 3 separates stdio auth from HTTP/provider auth, removes error-driven fallback as steady-state behavior, and shrinks `auth/google_auth.py` into a thin facade.

**Tech Stack:** Python 3.11, dataclasses, FastAPI/Uvicorn callback server, `google-auth-oauthlib`, `pytest`, `ruff`

---

## Why this is a three-phase plan

- Issue #11 is real, but it is only one symptom. The auth system is fragile because client selection, flow selection, redirect resolution, callback handling, state persistence, session binding, and provider branching are still tangled inside `auth/google_auth.py`.
- A single giant refactor is too risky for a live auth subsystem. The safest path is: stop incorrect runtime behavior now, then extract explicit policy/state seams, then simplify the remaining topology and legacy branches once tests cover the matrix.
- The hotfix should be small enough to ship quickly. The long-term fix should be explicit enough that the next auth bug does not reopen the same design problem.

## Phase sizing, feasibility, and risk

- **Phase 1 - Hotfix:** high feasibility, medium risk, roughly 0.5-1 day. This is the smallest change set that fixes the current correctness issue and hardens the active callback/manual-completion path.
- **Phase 2 - Stabilization:** high feasibility, medium risk, roughly 2-3 days. This is mostly extraction of pure decision logic plus broader tests.
- **Phase 3 - Simplification:** medium feasibility, higher risk, roughly 2-4 days. This changes auth orchestration boundaries and should not start until the Phase 2 matrix is green.

## Global guardrails

- Do not add new auth environment flags in Phase 1.
- Do not change device-flow defaults for legacy env-only or `installed` clients in Phase 1 unless a failing regression proves it is necessary.
- Do not synthesize redirect URIs in multiple places. By the end of Phase 2, redirect choice should come from one policy module plus persisted challenge state.
- Use dataclasses for new auth plan/state types so the new code matches `auth/oauth_clients.py` and `auth/oauth21_session_store.py` conventions.
- Every behavior change starts with a failing test.
- Split delivery by phase. Phase 1 must be mergeable without waiting on Phase 2 or Phase 3.
- Keep operator-visible error messages explicit and repair-oriented.
- Delete dead branches once they are replaced. Do not leave breadcrumbs in the code.

## Target acceptance criteria

1. For any auth attempt, the system can say which client, which flow, which redirect URI, and why.
2. Mapped `web` clients never use unregistered localhost callback ports.
3. Start and completion reuse the same persisted redirect URI and client context.
4. Manual `complete_google_auth` remains a first-class stdio path rather than a fragile fallback.
5. Diagnostics make auth decisions supportable without source diving.
6. By the end of Phase 2, flow selection is capability-driven rather than provider-error-driven.
7. By the end of Phase 3, stdio auth and HTTP/provider auth have explicit topology boundaries in code, tests, and docs.

## Delivery order

1. Phase 1 PR A: deterministic redirect policy and callback-server fail-closed rules.
2. Phase 1 PR B: challenge immutability, manual completion hardening, and auth-decision diagnostics.
3. Phase 1 docs/release notes PR, unless it fits cleanly into PR B.
4. Phase 2 extraction PRs.
5. Phase 3 simplification PRs.

## Phase 1 - Hotfix: deterministic redirect and immutable challenge context

**Objective:** Fix the live reliability issue without a wide refactor. After this phase, mapped multi-client `web` clients must either use a registered localhost redirect port or fail with a clear operator-facing error. The manual completion path must also reuse the redirect URI chosen when the challenge started.

### Task 1: Add callback-port policy tests and a single policy helper

**Files:**
- Modify: `tests/unit/auth/test_google_auth_flow_modes.py`
- Modify: `auth/google_auth.py`

**Implementation:**
- Add failing tests around a dedicated helper such as `_resolve_callback_port_policy()`.
- Cover these cases:
  - mapped `web` client without `redirect_uris` -> explicit error
  - mapped `web` client with registered localhost `redirect_uris` -> returns preferred ports and disables sequential fallback
  - `installed` client without `redirect_uris` -> sequential fallback still allowed
  - legacy env-only client -> sequential fallback still allowed
- Implement `_resolve_callback_port_policy()` close to `_extract_ports_from_redirect_uris()` in `auth/google_auth.py` and use it inside `_start_callback_auth_challenge()`.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py -k "callback_port_policy" -v
```

**Definition of done:**
- Callback-port policy is decided in one helper instead of being spread across `_start_callback_auth_challenge()`.
- The helper returns both `preferred_ports` and `allow_sequential_fallback`.

### Task 2: Make callback-server binding fail closed and validate server reuse

**Files:**
- Create: `tests/unit/auth/test_oauth_callback_server.py`
- Modify: `auth/oauth_callback_server.py`
- Modify: `auth/google_auth.py`

**Implementation:**
- Add failing callback-server tests for these scenarios:
  - registered port occupied and fallback disabled -> fail with explicit error
  - first registered port occupied, second registered port free -> use the second registered port, not the sequential scanner
  - fallback enabled -> sequential port scan still works
  - an already-running callback server is only reused if its port is allowed by the current request; otherwise fail closed with a repair message
- Update `start_oauth_callback_server()` to accept `allow_sequential_fallback: bool = True`.
- Before reusing `_minimal_oauth_server`, validate `_current_oauth_server_redirect_uri` against the current port policy.
- Thread the policy through `resolve_oauth_redirect_uri_for_auth_flow()` in `auth/google_auth.py`.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_oauth_callback_server.py -v
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py -k "callback" -v
```

**Definition of done:**
- `web` clients never silently reuse a callback server running on a disallowed port.
- Preferred-port scanning tries all registered ports before any sequential fallback.

### Task 3: Make the auth challenge immutable across start and completion

**Files:**
- Modify: `core/server.py`
- Modify: `auth/google_auth.py`
- Modify: `auth/oauth21_session_store.py`
- Modify: `tests/unit/auth/test_auth_runtime_paths.py`
- Modify: `tests/unit/auth/test_oauth_state_persistence.py`

**Implementation:**
- Add failing tests for these scenarios:
  - `complete_google_auth(authorization_code=..., state=...)` rebuilds the authorization response from the redirect URI stored with that OAuth state, not from current config
  - callback completion still succeeds when the stored redirect URI differs from `get_oauth_redirect_uri_for_current_mode()`
  - stored OAuth state remains the source of truth for `oauth_client_key`, expected user, and redirect URI within one auth transaction
- Add the smallest helper necessary to read pending OAuth-state metadata without forcing `core/server.py` to recompute redirect context.
- In `core/server.py`, when only `authorization_code` and `state` are provided, build the callback URL from the stored redirect URI.
- Keep `handle_auth_callback()` using the stored redirect URI first and avoid re-deriving redirect/client context from current process config when persisted state already has authoritative values.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_auth_runtime_paths.py -k "complete_google_auth or redirect" -v
uv run pytest tests/unit/auth/test_oauth_state_persistence.py -v
```

**Definition of done:**
- Manual completion and callback completion both use the redirect URI chosen when the challenge started.
- Auth behavior no longer depends on current redirect config after a challenge is issued.

### Task 4: Add operator-visible diagnostics for the resolved auth decision

**Files:**
- Modify: `auth/diagnostics.py`
- Modify: `auth/google_auth.py`
- Modify: `tests/unit/auth/test_auth_runtime_paths.py`

**Implementation:**
- Extend diagnostics with a focused helper such as `log_resolved_auth_decision(...)`.
- Log at least:
  - selected client key
  - client type
  - source / selection mode
  - selected flow
  - redirect URI or preferred redirect ports
  - fallback policy
- Add targeted tests using `caplog` so the new diagnostics are locked in.
- Keep diagnostics opt-in under the existing `AUTH_DIAGNOSTICS=1` behavior.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_auth_runtime_paths.py -k "diagnostic or resolved_auth" -v
```

**Definition of done:**
- Support can inspect one auth attempt and understand why the system chose that client/flow/redirect behavior.

### Task 5: Update Phase 1 docs and release notes

**Files:**
- Modify: `docs/setup/MULTI_CLIENT_AUTH_SETUP.md`
- Modify: `docs/setup/AUTHENTICATION_MODEL.md`
- Modify: `docs/RELEASE_NOTES.md`

**Implementation:**
- Update the example `auth_clients.json` entry so callback-safe `web` clients include `client_type` and `redirect_uris`.
- Add a note that `import_google_auth_client` is the preferred path because it captures redirect metadata automatically.
- Add troubleshooting guidance for deterministic callback failures and manual completion.
- Add a release note that mapped multi-client `web` callback flows now fail closed instead of falling back to unregistered ports.

**Verification:**
- Read all changed docs in full after editing.
- Confirm the examples match actual field names already supported by `auth/oauth_clients.py`.

### Task 6: Run Phase 1 verification and prepare release guidance

**Files:**
- No source changes expected

**Verification:**

```bash
uv run pytest \
  tests/unit/auth/test_google_auth_flow_modes.py \
  tests/unit/auth/test_oauth_callback_server.py \
  tests/unit/auth/test_auth_runtime_paths.py \
  tests/unit/auth/test_oauth_state_persistence.py \
  tests/unit/auth/test_oauth_clients.py -v

uv run ruff check .
uv run ruff format .
uv run pytest
```

**Release guidance:**
- Tell operators using hand-written `auth_clients.json` entries to add `client_type` and `redirect_uris`, or re-import the full Google OAuth client JSON.
- Do not add `WORKSPACE_MCP_OAUTH_CALLBACK_PORT` in this phase.

**Phase 1 exit criteria:**
- Issue #11 is fixed.
- The current auth transaction is deterministic even when manual completion is used.
- The blast radius remains limited to redirect/callback behavior for mapped `web` clients plus improved diagnostics.

## Phase 2 - Stabilization: explicit policy and state seams

**Objective:** Extract the auth decision logic into small, typed, testable modules so runtime behavior is deterministic by construction rather than by scattered conditionals.

### Task 7: Introduce a typed `ResolvedAuthPlan`

**Files:**
- Create: `auth/auth_plan.py`
- Modify: `auth/google_auth.py`
- Create: `tests/unit/auth/test_auth_plan.py`

**Implementation:**
- Create a frozen dataclass for the resolved auth decision. The first version should be small and explicit.

```python
@dataclass(frozen=True)
class ResolvedAuthPlan:
    user_google_email: str
    transport_mode: str
    selected_flow: str
    oauth_client: OAuthClientSelection | None
    client_type: str | None
    selection_reason: str
    preferred_redirect_ports: tuple[int, ...]
    allow_sequential_fallback: bool
    redirect_uri: str | None
```

- Replace raw tuple returns and ad-hoc locals in `auth/google_auth.py` with this object where practical.
- Keep the first extraction narrow: do not change public tool signatures in this task.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_auth_plan.py -v
```

**Definition of done:**
- One object represents the final auth decision for a challenge.

### Task 8: Extract flow-selection rules into `auth/flow_policy.py`

**Files:**
- Create: `auth/flow_policy.py`
- Modify: `auth/google_auth.py`
- Create: `tests/unit/auth/test_flow_policy.py`
- Modify: `tests/unit/auth/test_google_auth_flow_modes.py`

**Implementation:**
- Move flow-selection rules out of `auth/google_auth.py` into a pure policy module.
- Cover at least:
  - `installed` + stdio -> device preferred
  - mapped `web` + stdio -> callback/manual, not device
  - provider / HTTP transport -> explicit provider path
  - no provider-error-driven selection in the final Phase 2 behavior
- Preserve public behavior only where tests require it, then tighten the policy so `auto` becomes deterministic rather than heuristic.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_flow_policy.py tests/unit/auth/test_google_auth_flow_modes.py -v
```

**Definition of done:**
- Flow selection is owned by one pure module instead of being inferred from provider failures inside the orchestrator.

### Task 9: Extract redirect rules into `auth/redirect_policy.py`

**Files:**
- Create: `auth/redirect_policy.py`
- Modify: `auth/google_auth.py`
- Modify: `auth/oauth_callback_server.py`
- Create: `tests/unit/auth/test_redirect_policy.py`

**Implementation:**
- Move redirect parsing and redirect-policy resolution out of `auth/google_auth.py`.
- The policy module should answer:
  - whether callback is allowed
  - which registered ports are preferred
  - whether sequential fallback is allowed
  - whether a concrete redirect URI is mandatory for the current client/transport
- Keep callback-server code focused on binding and reuse, not client-type policy.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_redirect_policy.py tests/unit/auth/test_oauth_callback_server.py -v
```

**Definition of done:**
- Redirect correctness is governed by one pure policy module plus the persisted challenge state.

### Task 10: Create a typed challenge facade around OAuth state persistence

**Files:**
- Create: `auth/challenge_store.py`
- Modify: `auth/oauth21_session_store.py`
- Modify: `auth/google_auth.py`
- Modify: `core/server.py`
- Create: `tests/unit/auth/test_challenge_store.py`

**Implementation:**
- Introduce a small dataclass for persisted auth challenge context.

```python
@dataclass(frozen=True)
class AuthChallengeContext:
    state: str
    user_google_email: str
    oauth_client_key: str | None
    redirect_uri: str
    code_verifier: str | None
    session_id: str | None
```

- Add a facade that serializes/deserializes this structure while reusing the existing `OAuth21SessionStore` storage layer.
- Move raw OAuth-state dict handling out of `core/server.py` and as much of `auth/google_auth.py` as possible.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_challenge_store.py tests/unit/auth/test_oauth_state_persistence.py -v
```

**Definition of done:**
- Challenge persistence becomes an explicit boundary instead of a collection of raw dictionaries.

### Task 11: Add an internal auth matrix under `tests/integration/`

**Files:**
- Create: `tests/integration/auth/test_auth_matrix.py`
- Modify: `tests/unit/auth/test_auth_runtime_paths.py` if shared helpers are needed

**Implementation:**
- Add internal integration tests with monkeypatched/stubbed Google interactions. Do not depend on live Google auth.
- Cover the minimum matrix:
  - `web` vs `installed`
  - stdio vs provider / HTTP path
  - callback vs device vs manual completion
  - mapped-only vs legacy env fallback
  - occupied callback port
  - wrong-account callback
  - restart / reload with pending OAuth state

**Verification:**

```bash
uv run pytest tests/integration/auth/test_auth_matrix.py -v
```

**Definition of done:**
- The repo has a repeatable auth regression matrix that protects the architecture change from future drift.

### Task 12: Update architecture docs after the extraction lands

**Files:**
- Modify: `auth/ARCHITECTURE.md`
- Modify: `docs/setup/AUTHENTICATION_MODEL.md`

**Implementation:**
- Document `ResolvedAuthPlan`, flow policy, redirect policy, and challenge-store boundaries.
- Add a short support matrix that explains which auth topology is supported in stdio vs provider / HTTP mode.

**Verification:**
- Re-read both docs after editing.
- Ensure the described modules match the actual extracted file names.

**Phase 2 exit criteria:**
- Flow and redirect behavior are controlled by small pure modules.
- Challenge persistence is explicit and typed.
- The auth matrix exists and passes.

## Phase 3 - Simplification: separate topologies and delete legacy knots

**Objective:** Make the architecture honest. Stdio/local-agent auth and HTTP/provider auth should stop pretending to be one dynamic runtime tree.

### Task 13: Split stdio orchestration from provider / HTTP orchestration

**Files:**
- Create: `auth/stdio_auth.py`
- Create: `auth/http_auth.py`
- Modify: `auth/google_auth.py`
- Modify: `core/server.py`
- Modify: `auth/service_decorator.py`
- Modify: `auth/external_oauth_provider.py`
- Create: `tests/integration/auth/test_topology_boundaries.py`

**Implementation:**
- Move stdio-oriented auth challenge start/completion, local callback use, and manual completion handling into `auth/stdio_auth.py`.
- Move provider / HTTP orchestration into `auth/http_auth.py` and make it the only place that bridges to provider-specific behavior.
- Keep `auth/google_auth.py` as a compatibility facade during the transition, but make it delegate immediately instead of owning the full decision tree.
- Add integration coverage proving:
  - stdio auth can complete manually without provider configuration
  - provider / HTTP auth does not start the local callback server as an implicit fallback

**Verification:**

```bash
uv run pytest tests/integration/auth/test_topology_boundaries.py -v
```

**Definition of done:**
- The top-level auth architecture reflects two explicit topologies instead of one giant conditional tree.

### Task 14: Remove error-driven fallback and ambiguous runtime branches

**Files:**
- Modify: `auth/flow_policy.py`
- Modify: `auth/google_auth.py`
- Modify: `auth/oauth_clients.py`
- Modify: `tests/unit/auth/test_flow_policy.py`
- Modify: `tests/integration/auth/test_auth_matrix.py`

**Implementation:**
- Remove any remaining steady-state logic that treats provider errors such as `invalid_client` as a normal way to decide auth flow.
- Make `auto` mean deterministic capability-based selection only.
- Remove ambiguous runtime branches that re-resolve client/redirect context after a challenge is already persisted.
- Preserve explicit upgrade or repair messages where old behavior is no longer supported.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_flow_policy.py tests/integration/auth/test_auth_matrix.py -v
```

**Definition of done:**
- Auth flow selection is deterministic before any request is sent to Google.

### Task 15: Shrink `auth/google_auth.py`, update docs, and delete dead code

**Files:**
- Modify: `auth/google_auth.py`
- Modify: `auth/ARCHITECTURE.md`
- Modify: `docs/setup/AUTHENTICATION_MODEL.md`
- Modify: `docs/RELEASE_NOTES.md`

**Implementation:**
- Remove dead helpers and compatibility branches that became unnecessary after Tasks 13 and 14.
- Update docs so the supported boundaries are explicit:
  - stdio auth
  - provider / HTTP auth
  - multi-client mode
  - legacy compatibility mode
- Document any remaining migration path for operators still using legacy layouts.

**Verification:**

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

**Phase 3 exit criteria:**
- `auth/google_auth.py` is a thin facade rather than the main policy engine.
- The auth topology is explicit in code, tests, and docs.
- Remaining compatibility behavior is deliberate, narrow, and documented.

## What not to do

- Do not patch issue #11 by adding yet another env flag.
- Do not leave redirect selection split across config helpers, callback-server code, and manual completion logic.
- Do not preserve provider-error-driven flow fallback as the long-term architecture.
- Do not introduce a large refactor in Phase 1.
- Do not add new types in deprecated shims such as `auth/oauth_types.py`.

## Final verification checklist

- Phase 1 ships independently and closes the live redirect/callback correctness gap.
- Phase 2 introduces explicit policy/state seams plus a real auth matrix.
- Phase 3 separates stdio and provider / HTTP auth and removes the remaining design knots.
- Full repo verification passes after each phase:

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```
