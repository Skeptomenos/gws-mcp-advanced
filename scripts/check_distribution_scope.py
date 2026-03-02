"""Distribution scope guard for npm/npx packaging references."""

from __future__ import annotations

import json
from pathlib import Path

EXPECTED_SCOPE = "@skeptomenos/gws-mcp-advanced"
README_REQUIRED_SNIPPETS = (
    "npx -y @skeptomenos/gws-mcp-advanced",
    "npx -y @skeptomenos/gws-mcp-advanced@next",
    "npx -y @skeptomenos/gws-mcp-advanced@1.0.0",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_package_name(package_json_path: Path) -> list[str]:
    errors: list[str] = []
    package_data = json.loads(_read_text(package_json_path))
    package_name = package_data.get("name")
    if package_name != EXPECTED_SCOPE:
        errors.append(
            f"{package_json_path}: expected name {EXPECTED_SCOPE!r}, found {package_name!r}",
        )
    return errors


def _check_readme(readme_path: Path) -> list[str]:
    errors: list[str] = []
    readme = _read_text(readme_path)

    for snippet in README_REQUIRED_SNIPPETS:
        if snippet not in readme:
            errors.append(f"{readme_path}: missing required snippet: {snippet!r}")

    disallowed_unscoped = "npx -y gws-mcp-advanced"
    if disallowed_unscoped in readme:
        errors.append(f"{readme_path}: found disallowed unscoped npx usage: {disallowed_unscoped!r}")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    package_json_path = repo_root / "package.json"
    readme_path = repo_root / "README.md"

    errors: list[str] = []
    if not package_json_path.exists():
        errors.append(f"missing required file: {package_json_path}")
    else:
        errors.extend(_check_package_name(package_json_path))

    if not readme_path.exists():
        errors.append(f"missing required file: {readme_path}")
    else:
        errors.extend(_check_readme(readme_path))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("distribution scope check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
