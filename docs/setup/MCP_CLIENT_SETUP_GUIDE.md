# MCP Client Setup Guide

Audience: users and team operators.

This page is the entry point for client-specific MCP setup.

## Prerequisite (All Clients)

Install `uv` first because this project is distributed through `uvx`.

```bash
# macOS (Homebrew)
brew install uv

# Windows (winget)
winget install --id=astral-sh.uv -e

# Windows (PowerShell installer)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

## Choose Your Client

- [Claude Code Setup](CLAUDE_CODE_MCP_SETUP.md)
- [Cursor Setup](CURSOR_MCP_SETUP.md)
- [OpenCode Setup](OPENCODE_MCP_SETUP.md)
- [Gemini CLI Setup](GEMINI_CLI_MCP_SETUP.md)

## Common Environment Variables

| Variable | Required | Description |
|---|---|---|
| `USER_GOOGLE_EMAIL` | Yes | Google account used by this MCP instance |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes for legacy single-client mode | OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes for legacy single-client mode | OAuth client secret |
| `WORKSPACE_MCP_CONFIG_DIR` | No | Override credential/config directory |
| `WORKSPACE_MCP_AUTH_FLOW` | No | `auto` (default), `device`, or `callback` |

## Authentication Notes

1. Start the MCP server from your client.
2. Trigger any protected Google tool call.
3. In `stdio` mode, complete device auth using the verification URL + user code returned by the tool.
4. In `streamable-http` mode, open the OAuth callback URL and complete consent.
5. Re-run the tool call to finalize auth and confirm connectivity.
6. For architecture, mode behavior, and security flags, see [Authentication Model](AUTHENTICATION_MODEL.md).
7. If you are upgrading from the legacy package/path, use [Migration Guide](MIGRATING_FROM_GWS_MCP_ADVANCED.md).

## Multi-Client (Enterprise + Private) Setup

If one MCP instance must route two tenants to different OAuth clients, follow:

- [Single-MCP Multi-Client Auth Setup](MULTI_CLIENT_AUTH_SETUP.md)

## Service-Specific Setup

- [Apps Script Setup](APPS_SCRIPT_SETUP.md) for Script API enablement, tool coverage, and runtime limitations.

This flow uses `auth_clients.json` plus admin setup tools:
1. `setup_google_auth_clients`
2. `import_google_auth_client`
3. `start_google_auth` + `complete_google_auth` (when callback completion is needed manually)

## Best Practices

- Use pinned versions in stable team configs (`==x.y.z`).
- Keep separate stable and local-dev MCP entries.
- For OpenCode, use the `mcp` top-level key and avoid unsupported fields like `cwd`.
- Restart your client after config changes.
