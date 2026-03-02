"""Live MCP smoke checks (guarded by environment opt-in)."""

from __future__ import annotations

import pytest

from .helpers import build_artifact_name


@pytest.mark.live_mcp
def test_live_settings_and_artifact_prefix(live_mcp_settings):
    assert "@" in live_mcp_settings.user_email
    artifact_name = build_artifact_name(live_mcp_settings.artifact_prefix, "smoke")
    assert artifact_name.startswith(live_mcp_settings.artifact_prefix)
