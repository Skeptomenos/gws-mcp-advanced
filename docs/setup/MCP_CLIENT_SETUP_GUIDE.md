# MCP Client Setup Guide

Audience: Users.

This guide explains how to connect `gws-mcp-advanced` from common MCP clients.

## Stable Team Setup (Recommended)
Use the published npm package with pinned versions for production teams.

```json
{
  "mcpServers": {
    "gws-mcp-advanced": {
      "command": "npx",
      "args": ["-y", "@skeptomenos/gws-mcp-advanced@1.0.0", "--transport", "stdio"],
      "env": {
        "USER_GOOGLE_EMAIL": "your.email@company.com"
      }
    }
  }
}
```

## Local Development Setup
Use repository-local execution while developing or testing unreleased changes.

```json
{
  "mcpServers": {
    "gws-mcp-advanced-dev": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced",
        "gws-mcp-advanced",
        "--transport",
        "stdio"
      ],
      "env": {
        "USER_GOOGLE_EMAIL": "your.email@company.com"
      }
    }
  }
}
```

## OpenCode
1. Configure an MCP server entry using one of the snippets above.
2. Restart OpenCode after config or code changes.
3. Ask OpenCode to list tools for `gws-mcp-advanced` to confirm registration.

## Gemini CLI
Gemini CLI can use MCP servers through your CLI/client MCP config. Use the same server entries above.

## Claude Code / Other TUIs (Cursor, Cline, Windsurf)
Use the same `mcpServers` structure if the client supports standard MCP config JSON. For client-specific config file locations, use the client docs and paste the same server block.

## Required Environment Variables
- `USER_GOOGLE_EMAIL` (required)
- `WORKSPACE_MCP_CONFIG_DIR` (optional)
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` (required for OAuth flow)

## Notes
- Prefer pinned npm versions (`@x.y.z`) for team stability.
- Keep a separate local-dev MCP entry to avoid mixing unreleased code into production workflows.
