# Authentication Model

Audience: users and operators who run `google-workspace-mcp-advanced` in MCP clients.

This document explains how authentication works at runtime, beyond the quick setup steps.

## At a Glance

- Authentication is automatic for normal tool calls.
- First protected tool call triggers OAuth if credentials are missing.
- In `stdio`, default auth interaction is device flow (`WORKSPACE_MCP_AUTH_FLOW=auto`).
- In `streamable-http`, default auth interaction is callback flow.
- Credentials are persisted and reused across restarts.
- Session binding is used to prevent cross-account credential access.
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
   - auth challenge is created based on `WORKSPACE_MCP_AUTH_FLOW`.
5. In `stdio` default mode (`auto`):
   - the server starts/resumes Google device auth and returns verification URL + user code.
6. In callback mode:
   - the server returns OAuth URL and waits for browser redirect callback.
7. After auth completes, credentials are stored and bound to session/user.
8. Later calls reuse stored credentials and refresh tokens when needed.

## Auth Interaction Modes

| `WORKSPACE_MCP_AUTH_FLOW` | Behavior in `stdio` | Behavior in `streamable-http` | Recommended Use |
|---|---|---|---|
| `auto` (default) | Device flow | Callback flow | Most deployments |
| `device` | Device flow | Device flow | Callback-hostile agent runtimes |
| `callback` | Callback flow | Callback flow | Explicit browser callback preference |

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
  - default: `~/.config/gws-mcp-advanced`
  - override: `WORKSPACE_MCP_CONFIG_DIR`
- Legacy compatibility override:
  - `GOOGLE_MCP_CREDENTIALS_DIR` (takes precedence when set)
- Credential files are stored under:
  - `<config_dir>/credentials/`
- Session/auth state is also persisted so sessions can recover after restart.

Operationally, this means a restart usually does not require re-auth unless token scope or account context changed.

## Account Selection and Session Binding

- In normal client use, one MCP session is bound to one Google identity.
- Session binding is immutable for security (prevents rebinding a live session to a different account).
- If an account mismatch happens, re-authenticate for the intended account/session.

## OAuth Configuration Inputs

| Variable | Purpose | Required |
|---|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID used for Google consent flow | Yes |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret | Yes |
| `USER_GOOGLE_EMAIL` | Preferred target account hint for local client setups | Yes for standard client setup |
| `WORKSPACE_MCP_CONFIG_DIR` | Custom config/credential directory | No |
| `WORKSPACE_MCP_AUTH_FLOW` | Auth interaction mode (`auto`, `device`, `callback`) | No |

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
- If callback mode is used, confirm callback URL registered in Google Cloud matches runtime configuration.
- If running in an MCP client with strict tool-call timeouts, prefer `WORKSPACE_MCP_AUTH_FLOW=auto` or `device`.

### Credentials exist but wrong account is used

- Re-auth with the intended account.
- Ensure your client is using the correct MCP server entry.
- Restart the client so a new MCP subprocess/session is created.

### HTTP mode token/session confusion

- Verify bearer token belongs to the same Google account expected by the request.
- Verify session headers are not being mixed across users.

## Related Docs

- [MCP Client Setup Guide](MCP_CLIENT_SETUP_GUIDE.md)
- [Claude Code Setup](CLAUDE_CODE_MCP_SETUP.md)
- [Cursor Setup](CURSOR_MCP_SETUP.md)
- [OpenCode Setup](OPENCODE_MCP_SETUP.md)
- [Gemini CLI Setup](GEMINI_CLI_MCP_SETUP.md)
