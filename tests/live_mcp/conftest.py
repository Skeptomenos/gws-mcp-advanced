"""Shared fixtures for live MCP integration lanes."""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class LiveMCPSettings:
    user_email: str
    artifact_prefix: str
    allow_write: bool


@pytest.fixture(scope="session")
def live_mcp_settings() -> LiveMCPSettings:
    if os.getenv("MCP_LIVE_TESTS") != "1":
        pytest.skip("Live MCP tests disabled (set MCP_LIVE_TESTS=1 to enable)")

    user_email = os.getenv("MCP_TEST_USER_EMAIL")
    if not user_email:
        pytest.skip("MCP_TEST_USER_EMAIL is required for live MCP tests")

    return LiveMCPSettings(
        user_email=user_email,
        artifact_prefix=os.getenv("MCP_TEST_PREFIX", "codex-it-"),
        allow_write=os.getenv("MCP_TEST_ALLOW_WRITE") == "1",
    )
