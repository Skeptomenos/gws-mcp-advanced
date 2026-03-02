"""Protocol-level contract checks for tool registry metadata."""

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


def _get_dry_run_default(tool) -> bool | None:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    props = schema.get("properties", {})
    dry_run_prop = props.get("dry_run")
    if not isinstance(dry_run_prop, dict):
        return None
    default = dry_run_prop.get("default")
    return default if isinstance(default, bool) else None


@pytest.mark.asyncio
@pytest.mark.mcp_protocol
async def test_registry_contains_core_tools():
    required_tools = {
        "list_calendars",
        "get_events",
        "search_gmail_messages",
        "list_drive_items",
        "create_doc",
        "modify_sheet_values",
    }

    async with Client(_client_config()) as client:
        tools = await client.list_tools()

    names = {tool.name for tool in tools}
    missing = required_tools - names
    assert not missing, f"Missing expected tools: {sorted(missing)}"


@pytest.mark.asyncio
@pytest.mark.mcp_protocol
async def test_mutator_schemas_expose_dry_run_default_true():
    mutators = [
        "create_event",
        "send_gmail_message",
        "create_drive_file",
        "modify_sheet_values",
        "batch_update_presentation",
        "update_task_list",
    ]

    async with Client(_client_config()) as client:
        tools = await client.list_tools()

    tool_map = {tool.name: tool for tool in tools}
    missing = [name for name in mutators if name not in tool_map]
    assert not missing, f"Missing expected mutator tools: {missing}"

    invalid = [name for name in mutators if _get_dry_run_default(tool_map[name]) is not True]
    assert not invalid, f"Mutators without dry_run default=true in schema: {invalid}"
