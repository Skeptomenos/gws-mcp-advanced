# Authentication Model

Audience: users and operators who run `google-workspace-mcp-advanced` in MCP clients.

This document explains how authentication works at runtime, beyond the quick setup steps.

## At a Glance

- Authentication is automatic for normal tool calls.
- First protected tool call triggers OAuth if credentials are missing.
- In `stdio`, default auth interaction is device flow (`WORKSPACE_MCP_AUTH_FLOW=auto`).
- In `streamable-http`, default auth interaction is callback flow.
- In `auto` mode, device-flow `invalid_client` falls back to callback flow automatically.
- Callback auth resolves one client, one flow, and one redirect policy before the browser challenge is created.
- Mapped `web` clients use registered redirect URIs only; malformed mapped profiles fail closed with repair guidance.
- Credentials are persisted and reused across restarts.
- Manual completion reuses persisted OAuth challenge metadata (including redirect URI) across restart.
- Session binding is used to prevent cross-account credential access.
- Optional single-MCP multi-client routing supports private + enterprise OAuth client separation.
- `AUTH_DIAGNOSTICS=1` emits auth decision and credential lookup diagnostics for one auth attempt.
- Mutating tools still require explicit `dry_run=False` to execute writes.

## Runtime Modes

| Mode | Transport | Identity Source | Typical Use |
|---|---|---|---|
| Standard local client mode | `stdio` | OAuth session + user context | Claude Code, OpenCode, Cursor, Gemini CLI |
| HTTP mode | `streamable-http` | Bearer token and/or session headers | Remote or proxied MCP deployments |
| Single-user mode | `stdio` (CLI flag) | Local credential store | Personal/local development only |
| Stateless mode | OAuth 2.1 HTTP | Token/session only (no file store fallback) | Controlled infra deployments |

## End-to-End Flow

1. A tool call enters middleware.
2. Auth middleware tries to resolve identity from:
   - bearer token (HTTP mode),
   - recent stdio session (stdio mode),
   - MCP session binding.
3. The tool decorator (`@require_google_service`) enforces service auth before tool logic runs.
4. If credentials are missing, expired without refresh, or missing required scopes:
   - auth challenge is created based on `WORKSPACE_MCP_AUTH_FLOW` after OAuth client and redirect policy are resolved.
5. In `stdio` default mode (`auto`):
    - the server starts/resumes Google device auth and returns verification URL + user code.
6. In callback mode:
    - the server returns OAuth URL and waits for browser redirect callback,
    - local `installed` auth may use sequential localhost callback fallback,
    - mapped `web` auth may bind only to registered localhost redirect ports.
7. After auth completes, credentials are stored and bound to session/user.
   - manual completion via `callback_url` or `authorization_code + state` reuses the stored challenge metadata.
8. Later calls reuse stored credentials and refresh tokens when needed.

## Auth Interaction Modes

| `WORKSPACE_MCP_AUTH_FLOW` | Behavior in `stdio` | Behavior in `streamable-http` | Recommended Use |
|---|---|---|---|
| `auto` (default) | Device flow | Callback flow | Most deployments |
| `device` | Device flow | Device flow | Callback-hostile agent runtimes |
| `callback` | Callback flow | Callback flow | Explicit browser callback preference |

## Callback Policy Resolution

- `installed` is the primary local/default auth path.
- Legacy env-only single-client local auth still behaves like `installed` for localhost callback fallback.
- Mapped `web` clients remain supported, but they must declare `redirect_uris` and may use only registered localhost callback ports.
- A mapped profile with `client_type=None` is invalid for callback-policy resolution and fails closed with repair guidance.
- A running local callback server may be reused only when the new auth attempt resolves to the identical redirect URI already being served.

## First-Time Authentication

1. Start the MCP server from your client.
2. Run any protected Google Workspace tool.
3. Complete the returned challenge:
   - device flow: open verification URL and enter code,
   - callback flow: open OAuth URL and complete browser consent.
4. Retry the tool call.

For most users, this is enough. You do not need to call auth tools manually.

## Credential and Session Persistence

- Primary config directory:
  - default: `~/.config/google-workspace-mcp-advanced`
  - override: `WORKSPACE_MCP_CONFIG_DIR`
- Legacy compatibility path:
  - `~/.config/gws-mcp-advanced` (auto-migrated/fallback-supported when `WORKSPACE_MCP_CONFIG_DIR` is not set)
- Legacy compatibility override:
  - `GOOGLE_MCP_CREDENTIALS_DIR` (takes precedence when set)
- Credential files are stored under:
  - `<config_dir>/credentials/`
- Session/auth state is also persisted so sessions can recover after restart.
- Multi-client setup additionally persists:
  - script OAuth client mappings (`script_clients`),
  - account/domain OAuth client mappings (`auth_clients.json`),
  - client-bound OAuth states,
  - client-aware pending device flow state.

Operationally, this means a restart usually does not require re-auth unless token scope or account context changed.

## Account Selection and Session Binding

- In normal client use, one MCP session is bound to one Google identity.
- Session binding is immutable for security (prevents rebinding a live session to a different account).
- In multi-client mode, session/auth persistence carries OAuth client context to prevent cross-client reuse.
- If an account mismatch happens, re-authenticate for the intended account/session.

## Single-MCP Multi-Client Routing

When configured, auth client selection uses:
1. internal/admin override,
2. script mapping (`script_clients`),
3. account mapping (`account_clients`),
4. domain mapping (`domain_clients`),
5. default client only in non-`mapped_only` modes.

`mapped_only` hard-fails if no mapping exists or if domain/client policy mismatches.
No cross-client fallback is attempted.

Setup guide:
- [Single-MCP Multi-Client Auth Setup](MULTI_CLIENT_AUTH_SETUP.md)

## OAuth Configuration Inputs

| Variable | Purpose | Required |
|---|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID used for legacy single-client flow | Yes for legacy single-client mode |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret used for legacy single-client flow | Yes for legacy single-client mode |
| `USER_GOOGLE_EMAIL` | Preferred target account hint for local client setups | Yes for standard client setup |
| `WORKSPACE_MCP_CONFIG_DIR` | Custom config/credential directory | No |
| `WORKSPACE_MCP_AUTH_FLOW` | Auth interaction mode (`auto`, `device`, `callback`) | No |
| `AUTH_DIAGNOSTICS` | Enables auth decision diagnostics when set to `1` | No |

## Security Controls and Flags

| Variable / Mode | Default | Purpose | Notes |
|---|---|---|---|
| `MCP_ENABLE_OAUTH21` | `false` | Enables OAuth 2.1-oriented behavior and provider integration | Needed for advanced HTTP auth patterns |
| `WORKSPACE_MCP_STATELESS_MODE` | `false` | Disables file-store fallback behavior | Requires OAuth 2.1 mode |
| `MCP_SINGLE_USER_MODE` / `--single-user` | off | Forces single-user local behavior | Best for personal local runs |
| `WORKSPACE_MCP_ALLOW_UNVERIFIED_JWT` | `false` | Break-glass compatibility path for unverified JWT identity extraction | Not recommended for normal operation |

## Manual Re-Authentication

Use manual re-authentication when:
- scopes changed,
- tokens were revoked,
- you switched Google accounts,
- the client session/account binding is stale.

Practical recovery sequence:
1. Restart MCP client.
2. Retry a protected tool.
3. Complete OAuth flow again.
4. Re-run the same tool call.

## Troubleshooting

### "Authentication required" repeats

- Confirm challenge completion:
  - device flow: verification completed with the same account and code not expired,
  - callback flow: callback URL opened and consent completed.
- Confirm `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` are set.
- If callback mode is used, confirm the started auth challenge used a redirect URI that is actually registered in Google Cloud.
- Manual completion uses the redirect URI persisted when the challenge started, not whatever callback setting is active now.
- If running in an MCP client with strict tool-call timeouts, prefer `WORKSPACE_MCP_AUTH_FLOW=auto` or `device`.

### Credentials exist but wrong account is used

- Re-auth with the intended account.
- Ensure your client is using the correct MCP server entry.
- Restart the client so a new MCP subprocess/session is created.

### Multi-client mapping/domain mismatch errors

- Check `auth_clients.json` under your config dir.
- Verify `script_clients`, `account_clients`, and `domain_clients` map the request to the intended client.
- Verify client `allowed_domains` includes the account domain.
- Use `import_google_auth_client` and re-run auth if mappings are incomplete.

### Mapped client is missing `client_type` or `redirect_uris`

- Re-import the original Google OAuth client JSON with `import_google_auth_client`.
- Avoid hand-editing mapped client profiles unless you also preserve `client_type` and, for `web`, the exact `redirect_uris`.

### "Another local callback auth challenge is active"

- Finish the currently running callback flow first.
- If you intentionally want reuse, the new challenge must resolve to the exact same redirect URI the local callback server is already serving.

### HTTP mode token/session confusion

- Verify bearer token belongs to the same Google account expected by the request.
- Verify session headers are not being mixed across users.

## Related Docs

- [MCP Client Setup Guide](MCP_CLIENT_SETUP_GUIDE.md)
- [Single-MCP Multi-Client Auth Setup](MULTI_CLIENT_AUTH_SETUP.md)
- [Migration Guide](MIGRATING_FROM_GWS_MCP_ADVANCED.md)
- [Claude Code Setup](CLAUDE_CODE_MCP_SETUP.md)
- [Cursor Setup](CURSOR_MCP_SETUP.md)
- [OpenCode Setup](OPENCODE_MCP_SETUP.md)
- [Gemini CLI Setup](GEMINI_CLI_MCP_SETUP.md)
