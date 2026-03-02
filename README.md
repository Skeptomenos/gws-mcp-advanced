# Google Workspace MCP Advanced

Production-ready MCP server for Google Workspace.

`google-workspace-mcp-advanced` gives MCP clients broad Google Workspace coverage with safe-by-default write operations, Markdown-to-Google-Docs support, and Drive sync workflows.

## Why This Project

- 10 service domains: Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides, Tasks, Search
- 100+ tools for read and write operations
- Dry-run defaults for mutating operations
- Strong Markdown rendering for Google Docs (kitchen-sink validated)
- Persistent OAuth sessions and resilient auth storage

## Quick Start

### 1. Install `uv`

```bash
# macOS (Homebrew)
brew install uv

# Linux/macOS (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

### 2. Run the MCP server from PyPI (recommended)

```bash
# Stable channel (latest release)
uvx google-workspace-mcp-advanced --transport stdio

# Pinned deterministic version (recommended for teams)
uvx google-workspace-mcp-advanced==1.0.0 --transport stdio
```

### 3. Add MCP client config

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

### 4. Use client-specific setup guides

- [Claude Code MCP setup](docs/setup/CLAUDE_CODE_MCP_SETUP.md)
- [Cursor MCP setup](docs/setup/CURSOR_MCP_SETUP.md)
- [OpenCode MCP setup](docs/setup/OPENCODE_MCP_SETUP.md)
- [Gemini CLI MCP setup](docs/setup/GEMINI_CLI_MCP_SETUP.md)

### 5. Authenticate on first run

1. Start the server from your MCP client.
2. Open the OAuth URL shown by the server.
3. Sign in and grant the requested scopes.
4. Credentials are saved in `~/.config/gws-mcp-advanced/credentials/`.

## Local Development Mode

Use repository-local execution when building or testing unreleased changes.

```json
{
  "mcpServers": {
    "google-workspace-dev": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/google-workspace-mcp-advanced",
        "google-workspace-mcp-advanced",
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

## Service Coverage

| Service | Example Capabilities |
|---|---|
| Gmail | search, read, draft, send, labels, filters |
| Drive | search, read, upload, permissions, ownership transfer |
| Calendar | list/create/modify/delete events |
| Docs | create/update docs, markdown insertion, table and image handling |
| Sheets | read/write ranges, formatting, conditional formatting |
| Chat | list spaces, read/send messages |
| Forms | create forms, read responses, update publish settings |
| Slides | create presentations, batch updates |
| Tasks | task lists and task lifecycle management |
| Search | programmable search endpoint support |

## Safety Model

- Mutating tools default to `dry_run=True`.
- You must pass `dry_run=False` to execute real changes.
- This reduces accidental writes during assistant experimentation.

## Common Runtime Commands

```bash
# Run locally from repo
uv run google-workspace-mcp-advanced --transport stdio

# HTTP transport
uv run google-workspace-mcp-advanced --transport streamable-http

# Single-user mode
uv run google-workspace-mcp-advanced --single-user

# Load specific service groups only
uv run google-workspace-mcp-advanced --tools gmail drive calendar
```

## Required Environment Variables

| Variable | Required | Description |
|---|---|---|
| `USER_GOOGLE_EMAIL` | Yes | Target Google account email |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | OAuth client secret |
| `WORKSPACE_MCP_CONFIG_DIR` | No | Config/credential directory override |

## Documentation

- User docs: [docs/INDEX.md](docs/INDEX.md)
- Client setup hub: [docs/setup/MCP_CLIENT_SETUP_GUIDE.md](docs/setup/MCP_CLIENT_SETUP_GUIDE.md)
- Claude Code setup: [docs/setup/CLAUDE_CODE_MCP_SETUP.md](docs/setup/CLAUDE_CODE_MCP_SETUP.md)
- Cursor setup: [docs/setup/CURSOR_MCP_SETUP.md](docs/setup/CURSOR_MCP_SETUP.md)
- OpenCode setup: [docs/setup/OPENCODE_MCP_SETUP.md](docs/setup/OPENCODE_MCP_SETUP.md)
- Gemini CLI setup: [docs/setup/GEMINI_CLI_MCP_SETUP.md](docs/setup/GEMINI_CLI_MCP_SETUP.md)
- Distribution/release guide: [docs/DISTRIBUTION_RELEASE.md](docs/DISTRIBUTION_RELEASE.md)
- Comparison with upstream: [docs/COMPARISON.md](docs/COMPARISON.md)

Contributor docs live in `AGENTS.md` and `agent-docs/`.
