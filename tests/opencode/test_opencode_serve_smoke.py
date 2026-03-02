"""Smoke checks for local OpenCode server CLI availability."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.live_mcp
def test_opencode_serve_smoke_script_runs():
    if shutil.which("opencode") is None:
        pytest.skip("opencode CLI not installed")

    script_path = Path("scripts/opencode_serve_smoke.sh")
    assert script_path.exists(), f"Missing script: {script_path}"

    completed = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PASS" in completed.stdout
