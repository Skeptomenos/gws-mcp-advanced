"""Protocol-level MCP handshake smoke tests over stdio transport."""

from __future__ import annotations

import os

import pytest
from fastmcp import Client


def _client_config() -> dict:
    user_email = os.getenv("USER_GOOGLE_EMAIL", "david@helmus.me")
    return {
        "mcpServers": {
            "gws-mcp-advanced": {
                "command": "uv",
                "args": ["run", "python", "main.py", "--transport", "stdio"],
                "cwd": ".",
                "env": {"USER_GOOGLE_EMAIL": user_email},
            }
        }
    }


@pytest.mark.asyncio
@pytest.mark.mcp_protocol
async def test_stdio_handshake_lists_tools():
    """Server should initialize over stdio and expose the tool registry."""
    async with Client(_client_config()) as client:
        tools = await client.list_tools()

    assert tools, "MCP tool registry is empty"
    assert len(tools) >= 50, f"Expected at least 50 tools, got {len(tools)}"
