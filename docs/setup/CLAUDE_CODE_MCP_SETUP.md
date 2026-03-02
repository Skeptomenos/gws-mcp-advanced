# Claude Code MCP Setup

This guide configures `google-workspace-mcp-advanced` for Claude Code.

## Option A (Recommended): CLI Registration

Add the server in project scope:

```bash
claude mcp add \
  --scope project \
  --transport stdio \
  --env USER_GOOGLE_EMAIL=your.email@company.com \
  google-workspace \
  -- \
  uvx google-workspace-mcp-advanced==1.0.0 --transport stdio
```

List configured servers:

```bash
claude mcp list
```

## Option B: Commit Shared Config

Create/update `.mcp.json` in your repo:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["google-workspace-mcp-advanced==1.0.0", "--transport", "stdio"],
      "env": {
        "USER_GOOGLE_EMAIL": "your.email@company.com"
      }
    }
  }
}
```

## Verify

1. Restart Claude Code after config changes.
2. Ask Claude Code to list tools from `google-workspace`.
3. Run one read-only tool (for example, list calendars).

## Troubleshooting

- If the server does not appear, run `claude mcp list` and confirm scope.
- If auth fails, re-run and complete OAuth in browser.
- If command fails, verify `uv --version` and retry.

## Official References

- [Claude Code MCP docs](https://docs.anthropic.com/en/docs/claude-code/mcp)
