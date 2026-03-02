"""Live markdown feature lane scaffolding."""

from __future__ import annotations

import pytest


@pytest.mark.live_mcp
@pytest.mark.live_write
def test_live_markdown_lane_requires_write_opt_in(live_mcp_settings):
    if not live_mcp_settings.allow_write:
        pytest.skip("Live write tests require MCP_TEST_ALLOW_WRITE=1")

    # Placeholder assertion for lane readiness.
    # Real markdown live-flow assertions will be added in Wave 4 expansion.
    assert live_mcp_settings.allow_write is True
