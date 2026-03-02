# Gemini CLI MCP Setup

This guide configures `google-workspace-mcp-advanced` for Gemini CLI.

## Option A (Recommended): CLI Registration

Add the MCP server in user scope:

```bash
gemini mcp add -s user google-workspace \
  uvx google-workspace-mcp-advanced==1.0.0 --transport stdio
```

List configured MCP servers:

```bash
gemini mcp list
```

## Option B: Manual Settings JSON

Edit `~/.gemini/settings.json`:

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

## Trust Requirement

Gemini CLI only starts local stdio MCP servers in trusted folders.

- Trust current folder when prompted, or
- use Gemini trust controls documented by Gemini CLI.

## Verify

1. Restart Gemini CLI session.
2. Ask Gemini to list tools from `google-workspace`.
3. Run a read-only tool to verify access.

## Troubleshooting

- If server is not started, verify the folder trust state.
- If command fails, confirm `uv --version` and retry.
- If auth is incomplete, complete OAuth browser flow and re-test.

## Official References

- [Gemini CLI configuration](https://geminicli.com/docs/configuration)
- [Gemini CLI MCP servers](https://geminicli.com/docs/tools/mcp-server)
