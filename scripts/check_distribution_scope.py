"""Distribution scope guard for uvx-first packaging references."""

from __future__ import annotations

import json
from pathlib import Path

import tomllib

EXPECTED_PACKAGE = "google-workspace-mcp-advanced"


def _read_project_version(pyproject_path: Path) -> str:
    data = tomllib.loads(_read_text(pyproject_path))
    version = str(data.get("project", {}).get("version", "")).strip()
    if not version:
        raise ValueError(f"{pyproject_path}: project.version is empty")
    return version


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_package_name(package_json_path: Path) -> list[str]:
    errors: list[str] = []
    package_data = json.loads(_read_text(package_json_path))
    package_name = package_data.get("name")
    if package_name != EXPECTED_PACKAGE:
        errors.append(
            f"{package_json_path}: expected name {EXPECTED_PACKAGE!r}, found {package_name!r}",
        )
    return errors


def _check_readme(readme_path: Path, expected_version: str) -> list[str]:
    errors: list[str] = []
    readme = _read_text(readme_path)

    required_snippets = (
        "uvx google-workspace-mcp-advanced --transport stdio",
        f"uvx google-workspace-mcp-advanced=={expected_version} --transport stdio",
    )
    for snippet in required_snippets:
        if snippet not in readme:
            errors.append(f"{readme_path}: missing required snippet: {snippet!r}")

    disallowed_scoped = "npx -y @skeptomenos/gws-mcp-advanced"
    if disallowed_scoped in readme:
        errors.append(f"{readme_path}: found disallowed deprecated npx usage: {disallowed_scoped!r}")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    package_json_path = repo_root / "package.json"
    readme_path = repo_root / "README.md"
    pyproject_path = repo_root / "pyproject.toml"

    errors: list[str] = []
    expected_version = ""
    if not package_json_path.exists():
        errors.append(f"missing required file: {package_json_path}")
    else:
        errors.extend(_check_package_name(package_json_path))

    if not pyproject_path.exists():
        errors.append(f"missing required file: {pyproject_path}")
    else:
        try:
            expected_version = _read_project_version(pyproject_path)
        except ValueError as exc:
            errors.append(str(exc))

    if not readme_path.exists():
        errors.append(f"missing required file: {readme_path}")
    else:
        if expected_version:
            errors.extend(_check_readme(readme_path, expected_version))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("distribution scope check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
