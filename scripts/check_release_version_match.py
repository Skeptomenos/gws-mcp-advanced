"""Ensure npm and Python package versions remain coupled."""

from __future__ import annotations

import json
from pathlib import Path

import tomllib


def _read_python_version(pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return str(data.get("project", {}).get("version", "")).strip()


def _read_npm_version(package_json_path: Path) -> str:
    data = json.loads(package_json_path.read_text(encoding="utf-8"))
    return str(data.get("version", "")).strip()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject_path = repo_root / "pyproject.toml"
    package_json_path = repo_root / "package.json"

    errors: list[str] = []
    if not pyproject_path.exists():
        errors.append(f"missing required file: {pyproject_path}")
    if not package_json_path.exists():
        errors.append(f"missing required file: {package_json_path}")

    if errors:
        for error in errors:
            print(error)
        return 1

    python_version = _read_python_version(pyproject_path)
    npm_version = _read_npm_version(package_json_path)

    if not python_version:
        errors.append(f"{pyproject_path}: project.version is empty")
    if not npm_version:
        errors.append(f"{package_json_path}: version is empty")
    if python_version and npm_version and python_version != npm_version:
        errors.append(
            "version mismatch: "
            f"pyproject.toml project.version={python_version!r} != package.json version={npm_version!r}",
        )

    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"release version coupling check passed ({python_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
