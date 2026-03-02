"""Smoke check wrapper for OpenCode SDK lane script."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.live_mcp
def test_opencode_sdk_smoke_script_runs():
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    if shutil.which("opencode") is None:
        pytest.skip("opencode CLI not installed")

    script_path = Path("scripts/opencode_sdk_smoke.mjs")
    assert script_path.exists(), f"Missing script: {script_path}"

    completed = subprocess.run(
        ["node", str(script_path), "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "dry-run" in completed.stdout.lower()


@pytest.mark.live_mcp
def test_opencode_sdk_smoke_script_live_mode():
    if os.getenv("OPENCODE_SMOKE_LIVE") != "1":
        pytest.skip("Set OPENCODE_SMOKE_LIVE=1 to run live opencode serve lifecycle smoke")
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    if shutil.which("opencode") is None:
        pytest.skip("opencode CLI not installed")

    script_path = Path("scripts/opencode_sdk_smoke.mjs")
    assert script_path.exists(), f"Missing script: {script_path}"

    completed = subprocess.run(
        ["node", str(script_path), "--live"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PASS" in completed.stdout
