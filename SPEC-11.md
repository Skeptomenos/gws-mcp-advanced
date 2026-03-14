# SPEC-11: Deterministic OAuth Callback and Auth Policy Stabilization

**Issue:** #11  
**Status:** Phase 1 complete and verified  
**Author:** OpenCode  
**Last updated:** 2026-03-14  
**Supersedes:** the desktop-only implementation strategy in `issue-11.md`

## 0. Implementation Checkpoint (2026-03-14)

This section is an operational checkpoint so Phase 1 work can resume safely after context compaction.

### Completed locally

- **Task 1 implemented:**
  - `auth/google_auth.py` now includes `_resolve_callback_port_policy()`.
  - Mapped `client_type=None` fails closed with repair guidance.
  - Mapped `web` clients without `redirect_uris` fail closed with repair guidance.
  - Mapped `web` localhost redirect URIs now resolve preferred callback ports and disable sequential fallback.
  - `installed` and legacy env-derived local auth still allow sequential fallback.
- **Task 2 implemented:**
  - `auth/oauth_callback_server.py` now includes pure helper seams for callback binding and reuse checks:
    - `_build_redirect_uri()`
    - `_is_port_available()`
    - `_validate_running_server_reuse()`
    - `_resolve_callback_bind_port()`
  - `start_oauth_callback_server()` now accepts `allow_sequential_fallback`.
  - Running singleton callback servers are only reused when the current request allows the exact running redirect URI.
- **Task 4 partially implemented:**
  - `auth/diagnostics.py` now includes `log_resolved_auth_decision(...)`.
  - `auth/google_auth.py` now emits auth-decision diagnostics during callback/device planning and credential resolution.
- **Focused regression coverage added/updated:**
  - `tests/unit/auth/test_google_auth_flow_modes.py`
  - `tests/unit/auth/test_oauth_callback_server.py`
  - `tests/unit/auth/test_auth_runtime_paths.py`

### Completed after verification

- **Task 3 completed:**
  - `core/server.py` loads pending OAuth-state metadata by `state`.
  - Manual `authorization_code + state` completion builds its callback URL from the stored `redirect_uri` instead of current runtime config.
  - Legacy callback handling passes the stored redirect URI into `handle_auth_callback()` when state metadata is available.
  - Explicit `callback_url` completion remains supported; if stored state metadata is unavailable for that path, redirect handling falls back to the callback URL's own base URI.
  - Restart/persistence coverage now confirms stored OAuth-state metadata remains the source of truth across completion paths.
- **Task 4 completed:**
  - Diagnostics coverage now confirms auth-decision logging is emitted under `AUTH_DIAGNOSTICS=1`.
- **Task 5 completed:**
  - Updated:
    - `docs/setup/MULTI_CLIENT_AUTH_SETUP.md`
    - `docs/setup/AUTHENTICATION_MODEL.md`
    - `docs/RELEASE_NOTES.md`
- **Task 6 completed:**
  - Lint, format check, targeted auth coverage, pyright, and full pytest all passed.

### Verified

```bash
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_oauth_callback_server.py tests/unit/auth/test_auth_runtime_paths.py -q
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_oauth_callback_server.py tests/unit/auth/test_auth_runtime_paths.py tests/unit/auth/test_oauth_state_persistence.py -q
uv run ruff check .
uv run ruff format --check .
uv run pyright --project pyrightconfig.json
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py tests/unit/auth/test_oauth_callback_server.py tests/unit/auth/test_auth_runtime_paths.py tests/unit/auth/test_oauth_state_persistence.py tests/unit/auth/test_oauth_clients.py -v
uv run pytest

# Results:
# focused auth regression suite: 54 passed
# targeted Phase 1 auth suite: 59 passed
# full pytest: 755 passed, 3 skipped
```

### Remaining before Phase 2

- Phase 1 is done.
- Phase 2 can now focus on policy/state extraction and longer-term architecture cleanup without reopening the callback reliability bugfix.

### Continue-from-here note

- Preserve unrelated local worktree changes while continuing; `uv.lock` was already modified outside this spec slice.
- Use this checkpoint as the new baseline if Phase 2 work starts in a fresh session.

---

## 1. Context

Issue #11 found a real auth reliability bug, but the original implementation plan in `issue-11.md`
misdiagnosed the problem and proposed removing `web` client support entirely. That would be a product
de-scope, not a targeted bug fix.

This repository already documents and partially supports multiple auth topologies:

- local `stdio` auth for CLI/agent runtimes
- callback auth for browser-based completion
- mapped multi-client auth via `auth_clients.json`
- `streamable-http` / provider-oriented deployments

The correct fix is:

1. keep `installed` clients as the primary path for local/default auth
2. keep `web` clients supported where callback semantics require them
3. make the client/flow/redirect decision deterministic before sending the user to Google
4. fail closed on invalid `web` configurations instead of silently falling back to unregistered ports
5. make auth completion reuse the exact redirect/client context that the challenge started with

This spec defines an executable Phase 1 and Phase 2 plan that fixes the live bugs and then extracts
the policy/state seams needed to keep auth supportable.

---

## 2. Product Decision

### Supported client types

- `installed`
  - primary for local/default `stdio` auth
  - sequential localhost callback fallback remains allowed
  - legacy env-only local setups remain supported

- `web`
  - fully supported for mapped callback flows and remote/proxied callback deployments
  - must use registered redirect URIs only
  - must fail with a clear repair message when required redirect metadata is missing

### Clarification on "installed primary, web fallback"

This does **not** mean: "try installed first, then retry the same auth transaction as web if it fails."

It means:

- local/default product preference is `installed`
- `web` remains a supported secondary path in the product matrix
- a single auth transaction must resolve one client, one flow, and one redirect policy before the
  browser challenge is created

### Policy for mapped clients with missing `client_type`

- Phase 1 must distinguish legacy env-derived local auth from mapped multi-client profiles.
- A mapped profile loaded from `auth_clients.json` with `client_type=None` is invalid for callback
  policy resolution.
- Required behavior: fail the auth attempt with repair guidance to re-import the original Google
  OAuth client JSON or add `client_type` explicitly.
- Do not silently default mapped `client_type=None` to `web` or `installed`.
- This validation happens when the mapped client is selected for auth / redirect-policy resolution,
  not during generic config load for unrelated commands.

### Concurrent local callback policy

- Phase 1 keeps the existing singleton local callback server.
- Multiple pending OAuth states may coexist in storage.
- A second callback challenge may reuse the running local callback server only if the resolved
  redirect URI is both allowed for the new request and identical to the URI already being served.
- Otherwise fail early with an explicit "another local callback auth challenge is active" style
  error. Do not tear down or rebind the running callback server automatically in Phase 1.

### Explicit non-decisions

- Do not remove `web` support in Phase 1 or Phase 2.
- Do not silently reinterpret malformed `web` config as `installed`.
- Do not use provider/runtime failure as the long-term mechanism for deciding auth policy.

---

## 3. User Stories

1. As a local `stdio` user with `installed` credentials, I can authenticate reliably even when the
   first localhost callback port is occupied.
2. As a multi-client operator using a mapped `web` client, I can complete callback auth only on
   redirect URIs that are actually registered for that client.
3. As a user finishing auth manually, I can complete a started auth challenge after restart without
   current redirect config causing `redirect_uri_mismatch`.
4. As support or an operator, I can inspect one auth attempt and understand which client, flow,
   redirect URI, and fallback policy were chosen.

---

## 4. Data Contracts and Examples

### 4.1 Valid `installed` client entry

```json
{
  "oauth_clients": {
    "local-default": {
      "client_id": "local-client-id.apps.googleusercontent.com",
      "client_secret": "local-client-secret",
      "client_type": "installed"
    }
  }
}
```

### 4.2 Valid `web` client entry

```json
{
  "oauth_clients": {
    "work-callback": {
      "client_id": "work-client-id.apps.googleusercontent.com",
      "client_secret": "work-client-secret",
      "client_type": "web",
      "redirect_uris": [
        "http://localhost:9876/oauth2callback",
        "http://localhost:9877/oauth2callback"
      ]
    }
  }
}
```

### 4.3 Invalid `web` client entry

```json
{
  "oauth_clients": {
    "work-callback": {
      "client_id": "work-client-id.apps.googleusercontent.com",
      "client_secret": "work-client-secret",
      "client_type": "web"
    }
  }
}
```

Required behavior for the invalid example:

- do not treat this as `installed`
- do not use sequential localhost fallback
- fail with a repair-oriented message that tells the operator to add `redirect_uris` or re-import the
  original Google OAuth client JSON

### 4.4 Invalid mapped client entry with missing `client_type`

```json
{
  "oauth_clients": {
    "legacy-handwritten": {
      "client_id": "legacy-client-id.apps.googleusercontent.com",
      "client_secret": "legacy-client-secret",
      "redirect_uris": [
        "http://localhost:9876/oauth2callback"
      ]
    }
  }
}
```

Required behavior for the invalid example:

- do not default this mapped entry to `web` or `installed`
- do not allow callback policy resolution to guess based on missing metadata
- fail with a repair-oriented message that tells the operator to re-import the original Google OAuth
  client JSON or add `client_type` explicitly
- continue to support legacy env-only config as a separate path; this rule applies to mapped
  multi-client entries only

### 4.5 Persisted OAuth challenge state

Phase 1 continues to use the existing OAuth state store, but this state becomes authoritative for one
auth transaction. At minimum, these fields must remain consistent between start and completion:

```json
{
  "state": "opaque-state-token",
  "oauth_client_key": "work-callback",
  "expected_user_email": "alice@example.com",
  "code_verifier": "pkce-verifier",
  "redirect_uri": "http://localhost:9876/oauth2callback",
  "session_id": "optional-session-id"
}
```

### 4.6 Phase 2 typed contracts

Phase 2 introduces explicit typed seams so policy is no longer implied by scattered conditionals.

```python
from typing import Literal


@dataclass(frozen=True)
class ResolvedAuthPlan:
    user_google_email: str
    transport_mode: Literal["stdio", "streamable-http", "provider"]
    selected_flow: Literal["device", "callback"]
    oauth_client: OAuthClientSelection | None
    selection_reason: str
    preferred_redirect_ports: tuple[int, ...]
    allow_sequential_fallback: bool
    requires_explicit_redirect_uri: bool


@dataclass(frozen=True)
class AuthChallengeContext:
    state: str
    user_google_email: str
    oauth_client_key: str | None
    expected_user_email: str | None
    redirect_uri: str
    code_verifier: str | None
    session_id: str | None
```

---

## 5. Constraints and Guardrails

### 5.1 Hard constraints

- Do not remove `web` support.
- Do not reject valid imported `web` OAuth JSON in Phase 1.
- Do not default missing `client_type` to `installed` for mapped multi-client entries.
- Do not add new auth environment flags in Phase 1.
- Do not add `WORKSPACE_MCP_OAUTH_CALLBACK_PORT` in Phase 1.
- Do not widen the public tool surface in Phase 2.
- Do not start a local callback server from provider/HTTP code paths as an implicit fallback.
- Every behavior change starts with a failing test.

### 5.2 Architecture constraints

- Phase 1 stays inside the current seams:
  - `auth/google_auth.py`
  - `auth/oauth_callback_server.py`
  - `core/server.py`
  - `auth/oauth21_session_store.py`
  - `auth/diagnostics.py`
- Phase 2 extracts pure policy/state modules but keeps the existing tool surface stable.
- New plan/state structures use dataclasses.

### 5.3 Documentation constraints

- Docs must explain why the behavior exists, not just list file changes.
- Operator repair guidance must be explicit for invalid `web` client metadata.
- `import_google_auth_client` remains the preferred setup path because it captures redirect metadata.

### 5.4 Validation and failure-scope constraints

- Valid imported Google OAuth client JSON must remain accepted in Phase 1.
- Hand-written mapped entries are not rejected during generic config load for unrelated commands.
- Missing `client_type` or required `redirect_uris` on a mapped profile must fail when that profile is
  selected for auth / redirect-policy resolution.
- The failure must be scoped to the attempted auth operation and must include repair guidance.

### 5.5 Concurrent callback constraints

- Phase 1 keeps a singleton local callback server; this is an explicit constraint, not an accidental
  implementation detail.
- A running callback server may be reused only when the resolved redirect URI is identical and allowed
  for the new request.
- Incompatible overlapping callback starts must fail early instead of stealing, rebinding, or silently
  reusing the wrong server.

---

## 6. Target Acceptance Criteria

1. For any auth attempt, the system can explain which client, which flow, which redirect URI, and why.
2. Mapped `web` clients never use unregistered localhost callback ports.
3. `installed` and legacy local flows still work with sequential localhost fallback.
4. Manual completion reuses the redirect URI selected when the auth challenge started.
5. Callback completion and manual completion use the same persisted challenge context.
6. A running callback server is only reused when its redirect URI is valid for the current auth request.
7. Invalid hand-written `web` config fails with a repair-oriented error instead of being silently coerced.
8. Mapped entries with `client_type=None` fail with repair guidance instead of being silently defaulted.
9. Incompatible concurrent callback attempts fail early instead of reusing or rebinding a disallowed
   running server.
10. By the end of Phase 2, flow and redirect decisions are owned by small typed policy modules.

---

## 7. Known Failures This Spec Must Fix

1. `complete_google_auth()` currently rebuilds the authorization response from current redirect config
   instead of the redirect URI persisted with the auth state.
2. Callback-server reuse can return an already-running redirect URI without validating that it is allowed
   for the current `web` client.
3. Mapped `web` clients with missing `redirect_uris` can drift into sequential localhost fallback.
4. Redirect and flow policy are split across `auth/google_auth.py`, `auth/oauth_callback_server.py`,
   config helpers, and manual-completion code paths.
5. Mapped clients with `client_type=None` are currently ambiguous and can behave like `web` in one path
   and merely "not installed" in another.
6. Overlapping callback auth attempts can currently reuse the singleton callback server without proving
   they are compatible.

---

## 8. Decision Flow

```text
[Resolve auth client + transport]
              |
              v
[Resolve callback policy]
   |- installed or legacy local -> sequential localhost fallback allowed
   |- mapped web + localhost redirect_uris -> preferred registered ports only
   |- mapped client missing client_type -> explicit repair error
   |- mapped web missing redirect_uris -> explicit repair error
   |- remote/proxy/provider path -> explicit configured callback/provider behavior
              |
              v
[Create challenge and persist redirect/client context]
              |
              v
[Complete auth using persisted context, not current runtime config]
```

---

## 9. Phase 1 - Hotfix

**Objective:** Fix the live callback correctness bugs with minimal blast radius.

**Expected blast radius:** redirect selection, callback-server binding/reuse, manual completion,
and auth diagnostics for mapped `web` clients.

### Task 1: Add callback-port policy tests and a single policy helper

**Files:**
- Modify: `tests/unit/auth/test_google_auth_flow_modes.py`
- Modify: `auth/google_auth.py`

**Implementation:**
- Add failing tests for a helper such as `_resolve_callback_port_policy()`.
- Cover these cases:
  - mapped client with `client_type=None` -> explicit error with repair guidance
  - mapped `web` client without `redirect_uris` -> explicit error
  - mapped `web` client with localhost `redirect_uris` -> returns preferred ports and disables
    sequential fallback
  - `installed` client without `redirect_uris` -> sequential fallback allowed
  - legacy env-only client -> sequential fallback allowed
- Implement `_resolve_callback_port_policy()` close to `_extract_ports_from_redirect_uris()`.
- Make the helper distinguish mapped profiles from legacy env-derived config using resolved client
  metadata such as source / selection mode, not by guessing from missing `client_type`.
- Use the helper inside `_start_callback_auth_challenge()`.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py -v
```

**Definition of done:**
- Callback-port policy is resolved in one helper.
- The helper returns both `preferred_ports` and `allow_sequential_fallback`.
- Invalid mapped metadata fails explicitly instead of drifting into implicit defaults.

### Task 2: Make callback-server binding fail closed and validate server reuse

**Files:**
- Create: `tests/unit/auth/test_oauth_callback_server.py`
- Modify: `auth/oauth_callback_server.py`
- Modify: `auth/google_auth.py`

**Implementation:**
- Add failing tests for these scenarios:
  - registered port occupied and fallback disabled -> fail with explicit error
  - first registered port occupied, second registered port free -> use the second registered port
  - fallback enabled -> sequential port scan still works
  - an already-running callback server is only reused if its redirect URI is allowed by the current
    request; otherwise fail closed with a repair message
- a second callback start with an incompatible running server fails early instead of stealing or
     silently rebinding the singleton callback server
- Add the smallest pure helper necessary to unit test reuse and bind-policy logic without requiring
  live sockets or uvicorn threads. Example helper names here are illustrative, not mandatory.
- Update `start_oauth_callback_server()` to accept `allow_sequential_fallback: bool = True`.
- Before reusing `_minimal_oauth_server`, validate the existing redirect URI against the current port
  policy.
- Thread the policy through `resolve_oauth_redirect_uri_for_auth_flow()`.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_oauth_callback_server.py -v
uv run pytest tests/unit/auth/test_google_auth_flow_modes.py -v
```

**Definition of done:**
- `web` clients never silently reuse a callback server running on a disallowed port.
- Preferred-port scanning tries all registered ports before any sequential fallback.
- Incompatible overlapping callback starts fail early instead of reusing or rebinding the wrong
  callback server.

### Task 3: Make the auth challenge immutable across start and completion

**Files:**
- Modify: `core/server.py`
- Modify: `auth/google_auth.py`
- Modify: `auth/oauth21_session_store.py`
- Modify: `tests/unit/auth/test_auth_runtime_paths.py`
- Modify: `tests/unit/auth/test_oauth_state_persistence.py`

**Implementation:**
- Add failing tests for these scenarios:
  - `complete_google_auth(authorization_code=..., state=...)` rebuilds the callback URL from the
    redirect URI stored with that OAuth state, not from current config
  - callback completion still succeeds when the stored redirect URI differs from current runtime
    redirect config
  - stored OAuth state remains the source of truth for `oauth_client_key`, expected user, and
    `redirect_uri` within one auth transaction
- Add the smallest helper necessary to read pending OAuth-state metadata without forcing
  `core/server.py` to recompute redirect context.
- In `core/server.py`, when only `authorization_code` and `state` are provided, build the callback URL
  from the stored redirect URI.
- In `core/server.py`, when stored OAuth-state metadata is available, pass that same stored redirect
  URI into `handle_auth_callback()` instead of recomputing it from current runtime config.
- If stored OAuth-state metadata for manual completion cannot be loaded, fail cleanly instead of
  silently falling back to current redirect config.
- Keep `handle_auth_callback()` using the stored redirect URI first.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_auth_runtime_paths.py -v
uv run pytest tests/unit/auth/test_oauth_state_persistence.py -v
```

**Definition of done:**
- Manual completion and callback completion both use the redirect URI chosen when the challenge started.
- Auth completion no longer depends on current redirect config after a challenge has been issued.
- The synthesized callback URL and the `redirect_uri` argument passed into callback handling come from
  the same stored challenge context when available.

### Task 4: Add operator-visible diagnostics for the resolved auth decision

**Files:**
- Modify: `auth/diagnostics.py`
- Modify: `auth/google_auth.py`
- Modify: `tests/unit/auth/test_auth_runtime_paths.py`

**Implementation:**
- Extend diagnostics with a helper such as `log_resolved_auth_decision(...)`.
- Log at least:
  - selected client key
  - client type
  - source / selection mode
  - selected flow
  - redirect URI or preferred redirect ports
  - fallback policy
- Keep diagnostics opt-in under existing `AUTH_DIAGNOSTICS=1` behavior.
- Add targeted tests using `caplog`.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_auth_runtime_paths.py -v
```

**Definition of done:**
- One auth attempt can be explained without reading source.

### Task 5: Update Phase 1 docs and release notes

**Files:**
- Modify: `docs/setup/MULTI_CLIENT_AUTH_SETUP.md`
- Modify: `docs/setup/AUTHENTICATION_MODEL.md`
- Modify: `docs/RELEASE_NOTES.md`

**Implementation:**
- Update `auth_clients.json` examples so callback-safe `web` clients include `client_type` and
  `redirect_uris`.
- Add a note that `import_google_auth_client` is the preferred setup path.
- Add troubleshooting guidance for deterministic callback failures and manual completion.
- Add a release note that mapped `web` callback flows now fail closed instead of falling back to
  unregistered ports.

**Verification:**
- Read all changed docs in full after editing.
- Confirm examples match actual field names already supported by `auth/oauth_clients.py`.

### Task 6: Run Phase 1 verification and prepare release guidance

**Verification:**

```bash
uv run pytest \
  tests/unit/auth/test_google_auth_flow_modes.py \
  tests/unit/auth/test_oauth_callback_server.py \
  tests/unit/auth/test_auth_runtime_paths.py \
  tests/unit/auth/test_oauth_state_persistence.py \
  tests/unit/auth/test_oauth_clients.py -v

uv run ruff check .
uv run ruff format --check .
uv run pytest
```

**Release guidance:**
- Tell operators using hand-written `auth_clients.json` entries to add `client_type` and
  `redirect_uris`, or re-import the full Google OAuth client JSON.
- Do not add a new callback-port env var in this phase.

**Phase 1 exit criteria:**
- Issue #11 is fixed.
- The current auth transaction is deterministic even when manual completion is used.
- Blast radius remains limited to redirect/callback behavior for mapped `web` clients plus improved
  diagnostics.

---

## 10. Phase 2 - Stabilization

**Objective:** Extract the auth decision logic into small, typed, testable modules so runtime behavior
is deterministic by construction instead of by scattered conditionals.

### Task 7: Introduce a typed `ResolvedAuthPlan`

**Files:**
- Create: `auth/auth_plan.py`
- Modify: `auth/google_auth.py`
- Create: `tests/unit/auth/test_auth_plan.py`

**Implementation:**
- Create the frozen `ResolvedAuthPlan` dataclass defined in Section 4.6.
- Use `Literal` or equivalent constrained value types for transport / flow fields instead of freeform
  strings.
- Do not duplicate `client_type` outside `oauth_client`.
- Do not store challenge-instance `redirect_uri` on the plan; that belongs in challenge context.
- Replace ad-hoc tuple returns and local variables in `auth/google_auth.py` where practical.
- Keep the first extraction narrow and do not change public tool signatures.

**Verification:**

```bash
uv run pytest tests/unit/auth/test_auth_plan.py -v
```

**Definition of done:**
- One object represents the final auth policy decision for a challenge without duplicating runtime
  challenge state.

### Task 8: Extract flow-selection rules into `auth/flow_policy.py`

**Files:**
- Create: `auth/flow_policy.py`
- Modify: `auth/google_auth.py`
- Create: `tests/unit/auth/test_flow_policy.py`
- Modify: `tests/unit/auth/test_google_auth_flow_modes.py`

**Implementation:**
- Move flow-selection rules out of `auth/google_auth.py` into a pure policy module.
- Cover at least:
  - `installed` + `stdio` -> device preferred
  - mapped `web` + `stdio` -> callback/manual, not device
  - provider / HTTP transport -> explicit provider path
  - no provider-error-driven selection in the final Phase 2 behavior

**Verification:**

```bash
uv run pytest tests/unit/auth/test_flow_policy.py tests/unit/auth/test_google_auth_flow_modes.py -v
```

**Definition of done:**
- Flow selection is owned by one pure module.

### Task 9: Extract redirect rules into `auth/redirect_policy.py`

**Files:**
- Create: `auth/redirect_policy.py`
- Modify: `auth/google_auth.py`
- Modify: `auth/oauth_callback_server.py`
- Create: `tests/unit/auth/test_redirect_policy.py`

**Implementation:**
- Move redirect parsing and redirect-policy resolution out of `auth/google_auth.py`.
- The policy module must answer:
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
- Redirect correctness is governed by one pure policy module plus persisted challenge state.

### Task 10: Create a typed challenge facade around OAuth state persistence

**Files:**
- Create: `auth/challenge_store.py`
- Modify: `auth/oauth21_session_store.py`
- Modify: `auth/google_auth.py`
- Modify: `core/server.py`
- Create: `tests/unit/auth/test_challenge_store.py`

**Implementation:**
- Introduce the `AuthChallengeContext` dataclass defined in Section 4.6.
- Add a facade that serializes/deserializes this structure while reusing the existing storage layer.
- Move raw OAuth-state dict handling out of `core/server.py` and as much of `auth/google_auth.py` as
  possible.

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
- Add internal integration tests with monkeypatched/stubbed Google interactions. Do not depend on live
  Google auth.
- Cover at minimum:
  - `web` vs `installed`
  - `stdio` vs provider / HTTP path
  - callback vs device vs manual completion
  - mapped-only vs legacy env fallback
  - mapped `client_type=None` fails with repair guidance
  - occupied callback port
  - concurrent callback starts against the singleton local callback server
  - wrong-account callback
  - restart / reload with pending OAuth state

**Verification:**

```bash
uv run pytest tests/integration/auth/test_auth_matrix.py -v
```

**Definition of done:**
- The repo has a repeatable auth regression matrix that protects the extracted architecture.

### Task 12: Update architecture docs after extraction lands

**Files:**
- Modify: `auth/ARCHITECTURE.md`
- Modify: `docs/setup/AUTHENTICATION_MODEL.md`

**Implementation:**
- Document `ResolvedAuthPlan`, flow policy, redirect policy, and challenge-store boundaries.
- Add a short support matrix explaining which auth topology is supported in `stdio` vs provider / HTTP
  mode.

**Verification:**
- Re-read both docs after editing.
- Ensure described modules match actual extracted file names.

### Phase 2 full verification

```bash
uv run pytest \
  tests/unit/auth/test_auth_plan.py \
  tests/unit/auth/test_flow_policy.py \
  tests/unit/auth/test_redirect_policy.py \
  tests/unit/auth/test_challenge_store.py \
  tests/integration/auth/test_auth_matrix.py -v

uv run ruff check .
uv run ruff format --check .
uv run pytest
```

**Phase 2 exit criteria:**
- Flow and redirect behavior are controlled by small pure modules.
- Challenge persistence is explicit and typed.
- The auth matrix exists and passes.

---

## 11. Sad Path Coverage

This spec is incomplete if these cases are not covered by tests and docs:

- mapped `web` client missing `redirect_uris`
- mapped client missing `client_type`
- mapped `web` client with multiple registered localhost redirect URIs
- registered port occupied and fallback disabled
- callback server already running on a disallowed port
- concurrent callback starts for different users or clients against the singleton local callback server
- current runtime redirect config changes between start and completion
- restart with pending OAuth state
- wrong-account callback
- explicit `callback_url` completion path remains supported
- `installed` client with no `redirect_uris`
- legacy env-only client with callback flow

---

## 12. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Existing hand-written `web` configs start failing where they previously failed later and less clearly | Medium | Fail closed with explicit repair guidance; update docs and release notes |
| Manual completion fix reveals hidden assumptions in tests or tooling | Medium | Add focused tests first; keep challenge state authoritative |
| Policy extraction drifts into a large refactor | Medium | Keep Phase 1 minimal and Phase 2 modules narrow; no public tool changes |
| Future contributors reintroduce error-driven fallback | Medium | Add flow-policy tests and an integration auth matrix in Phase 2 |

---

## 13. Delivery Order and PR Slicing

1. Phase 1 PR A: callback-port policy helper, mapped-metadata validation, and callback-server
   fail-closed behavior
2. Phase 1 PR B: immutable challenge context, manual completion hardening, diagnostics, and release
   guidance
3. Phase 2 extraction PR A: typed contracts only (`ResolvedAuthPlan`, `AuthChallengeContext`), with
   minimal or no behavior change
4. Phase 2 extraction PR B: `redirect_policy.py` plus callback-server integration
5. Phase 2 extraction PR C: `flow_policy.py`
6. Phase 2 extraction PR D: `challenge_store.py`, integration auth matrix, and architecture docs

Prefer mergeable PRs, but do not force artificial splits that duplicate churn across the same auth
path. Combining adjacent Phase 2 slices is acceptable if it reduces risk and keeps reviewable seams.

---

## 14. Open Questions and Fixed Defaults

This spec now fixes the following defaults so Phase 1 is not blocked by policy ambiguity:

- mapped `client_type=None` fails at auth-resolution time with repair guidance
- manual `authorization_code + state` completion must use stored redirect metadata for both the
  synthesized callback URL and the redirect URI passed into callback handling
- a running callback server is reusable only for an identical allowed redirect URI; incompatible
  overlap fails early
- malformed mapped callback config fails during auth / redirect-policy resolution, not during generic
  config loading for unrelated commands

If implementation uncovers a conflicting code path that cannot honor those defaults safely, stop and
update this spec instead of improvising.

Deferred follow-up questions that do **not** block this spec:

- whether Phase 3 should split stdio/local auth orchestration from provider/HTTP orchestration
- whether a dedicated support/debug command should expose resolved auth decisions directly

---

## 15. Final Verification Checklist

- Phase 1 fixes the live redirect/callback correctness bugs without removing `web` support.
- Phase 2 introduces explicit policy/state seams and a repeatable auth regression matrix.
- `installed` remains the primary local/default path.
- `web` remains supported where callback semantics require it.
- Invalid `web` config fails early with repair guidance.
- Full repo verification passes after each phase:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
