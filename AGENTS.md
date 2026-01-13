# Agent Operational Guide (AGENTS.md)

## Project Overview

**gws-mcp-advanced** - High-performance MCP server for Google Workspace integration.
Provides 50+ async tools for Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides, Tasks, and Search.
This is an advanced fork of `google_workspace_mcp` with integrated `drive-synapsis` features.

## Verification Protocol (Definition of Done)

Before marking a task as complete, you MUST run these commands in order to match the CI pipeline:

1. **Linting**: `uv run ruff check .` (Must return no errors)
2. **Formatting**: `uv run ruff format .` (Must not modify files)
3. **Testing**: `uv run pytest` (Must pass with exit code 0)

## Build, Lint, & Test Commands

### Installation
```bash
# Install with dev dependencies using uv (recommended)
uv pip install -e ".[dev]"
```

### Running the Server
```bash
# STDIO mode (default for MCP clients)
python main.py

# HTTP mode
python main.py --transport streamable-http

# Single-user mode (bypasses session mapping)
python main.py --single-user
```

> [!TIP]
> **Picking up code changes**: MCP servers are long-running processes. To apply code changes within an active session, you must restart the server.
> 1. Kill the running process (Ctrl+C in terminal or reload plugin in UI).
> 2. The next tool call will automatically spawn a new process with the updated code.

### Linting & Formatting
```bash
# Run ruff linter & formatter
uv run ruff check .
uv run ruff format .

# Auto-fix linting issues
uv run ruff check --fix .
```

### Testing
```bash
# Run all tests (Fastest)
uv run pytest

# Run tests with coverage (Matches CI)
uv run pytest tests/ --cov=.

# Run single test file
uv run pytest tests/test_oauth_state_persistence.py

# Run single test function (Recommended for debugging)
uv run pytest tests/test_oauth_state_persistence.py::TestOAuthStatePersistence::test_store_oauth_state_persists_to_disk

# Run with verbose output
uv run pytest -vs
```

### Type Checking
*Note: Pyright is run in CI but is currently permissive (continue-on-error).*
```bash
# Install pyright (not in dev-dependencies)
pip install pyright

# Run type verification
pyright --verifytypes gws-mcp-advanced
```

## Code Style Guidelines

### Formatting
- **Line length**: 120 characters (configured in pyproject.toml).
- **Quotes**: Always use **double quotes** for strings.
- **Target**: Python 3.10+ (use `|` for unions, `match` statements where appropriate).

### Imports
Group imports in this order, separated by blank lines:
1. Standard library
2. Third-party packages
3. Local modules

```python
import asyncio
import logging
from typing import Optional, List

from googleapiclient.errors import HttpError

from auth.service_decorator import require_google_service
from core.server import server
```

### Naming Conventions
- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Loggers**: `logger = logging.getLogger(__name__)` (defined at module level)

### Type Hints
**MANDATORY**: Always use explicit type hints for function signatures and complex variables.
Avoid `Any` unless absolutely necessary for dynamic Google API responses.

### Async & Performance
All MCP tools MUST be async. Wrap blocking Google API calls in `asyncio.to_thread()`:

```python
# CORRECT: Offload blocking I/O to a thread
result = await asyncio.to_thread(service.files().list(q=query).execute)

# WRONG: Blocking the event loop
result = service.files().list(q=query).execute()
```

### Error Handling
1. Use custom error types from `core/errors.py` for domain-specific failures.
2. Use `@handle_http_errors` decorator for standard Google API error mapping.
3. Never use empty `except:` blocks.
4. Log errors with `logger.error(..., exc_info=True)` when appropriate.

## Core Patterns

### MCP Tool Structure
All tools should follow this standard decorator stack:

```python
@server.tool()
@handle_http_errors("tool_name", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def tool_name(
    service,                          # Injected by require_google_service
    user_google_email: str,           # Required for session mapping
    param1: str,
) -> str:
    """
    Clear description of the tool's purpose.

    Args:
        user_google_email: The user's Google email address. Required.
        param1: Purpose of param1.
    """
    return "Result"
```

### Search & Aliases
`SearchManager` (`core/managers.py`) caches search results with A-Z aliases.
Always use `resolve_file_id_or_alias()` when a tool accepts a file ID to support these aliases.

### File Sync
Sync tools (`gdrive/sync_tools.py`) use `SyncManager`.
**Safety first**: Always default `dry_run=True` for any tool that modifies local or remote files.

## Environment & Security

| Variable | Description | Default |
|----------|-------------|---------|
| `USER_GOOGLE_EMAIL` | Target Google account email | Required |
| `WORKSPACE_MCP_CONFIG_DIR` | Directory for credentials | `~/.config/google-workspace-mcp` |

**Security Rules**:
1. **No Hardcoded Secrets**: Use environment variables or the embedded OAuth flow.
2. **Credential Privacy**: Never log OAuth tokens or client secrets.
3. **Internal Only**: This server is designed for secure, per-user authentication.
