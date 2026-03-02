"""Smoke tests for the npm launcher entrypoint."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _node_bin() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required for launcher smoke tests")
    return node


def _launcher_path() -> Path:
    return Path(__file__).resolve().parents[3] / "bin" / "google-workspace-mcp-advanced.cjs"


def _package_version() -> str:
    package_json = Path(__file__).resolve().parents[3] / "package.json"
    package_data = json.loads(package_json.read_text(encoding="utf-8"))
    return str(package_data["version"])


def test_launcher_uses_uvx_when_available(tmp_path: Path) -> None:
    version = _package_version()
    log_path = tmp_path / "uvx.log"
    uvx_path = tmp_path / "uvx"
    _write_executable(
        uvx_path,
        f"""#!/bin/bash
if [[ "$1" == "--version" ]]; then
  exit 0
fi
echo "$@" > "{log_path}"
exit 0
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"

    result = subprocess.run(
        [_node_bin(), str(_launcher_path()), "--transport", "stdio"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    args = log_path.read_text(encoding="utf-8")
    assert f"--from google-workspace-mcp-advanced=={version} google-workspace-mcp-advanced --transport stdio" in args


def test_launcher_falls_back_to_uv_tool_run(tmp_path: Path) -> None:
    version = _package_version()
    log_path = tmp_path / "uv.log"
    uv_path = tmp_path / "uv"
    _write_executable(
        uv_path,
        f"""#!/bin/bash
if [[ "$1" == "--version" ]]; then
  exit 0
fi
echo "$@" > "{log_path}"
exit 0
""",
    )

    env = os.environ.copy()
    env["PATH"] = str(tmp_path)

    result = subprocess.run(
        [_node_bin(), str(_launcher_path()), "--transport", "stdio"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    args = log_path.read_text(encoding="utf-8")
    assert (
        f"tool run --from google-workspace-mcp-advanced=={version} google-workspace-mcp-advanced --transport stdio"
        in args
    )


def test_launcher_fails_without_uv_runtime(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)

    result = subprocess.run(
        [_node_bin(), str(_launcher_path()), "--transport", "stdio"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing required runtime" in result.stderr
