# Cursor MCP Setup

This guide configures `google-workspace-mcp-advanced` for Cursor.

## Config File Location

Use one of these:

- Project scope: `.cursor/mcp.json`
- User scope: `~/.cursor/mcp.json`

## Add Server Entry

```json
{
  "mcpServers": {
    "google-workspace": {
      "type": "stdio",
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

1. Restart Cursor after editing MCP config.
2. Open Cursor agent/chat and request tools from `google-workspace`.
3. Execute a read-only tool call.

## Troubleshooting

- If no tools appear, validate JSON syntax and config path.
- If startup fails, confirm `uv` is installed and available in PATH.
- If auth is incomplete, restart flow and complete OAuth browser consent.

## Official References

- [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol)
