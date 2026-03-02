# OpenCode MCP Setup

This guide configures `google-workspace-mcp-advanced` for OpenCode.

## Config File Location

Use one of these OpenCode config files:

- Project config: `opencode.json` or `opencode.jsonc`
- Global config: `~/.config/opencode/opencode.json`

## Add MCP Entry

```json
{
  "mcp": {
    "google-workspace": {
      "type": "local",
      "enabled": true,
      "command": [
        "uvx",
        "google-workspace-mcp-advanced==1.0.0",
        "--transport",
        "stdio"
      ],
      "environment": {
        "USER_GOOGLE_EMAIL": "your.email@company.com"
      }
    }
  }
}
```

## Verify

1. Restart OpenCode after config changes.
2. Ask OpenCode to list tools from `google-workspace`.
3. Execute one read-only tool call.

## Troubleshooting

- If server is missing, confirm config file path and JSON validity.
- If process launch fails, test the command directly in terminal:

```bash
uvx google-workspace-mcp-advanced==1.0.0 --transport stdio
```

## Official References

- [OpenCode MCP servers](https://opencode.ai/docs/mcp-servers)
- [OpenCode configuration](https://opencode.ai/docs/config)
