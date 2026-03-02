#!/usr/bin/env python3
"""Check MCP tool decorator order consistency."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

TOOL_MODULE_DIRS = [
    "gcalendar",
    "gchat",
    "gdocs",
    "gdrive",
    "gforms",
    "gmail",
    "gsearch",
    "gsheets",
    "gslides",
    "gtasks",
]


def _decorator_name(node: ast.AST) -> str:
    """Return a normalized decorator name for matching."""
    if isinstance(node, ast.Call):
        node = node.func

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST | None = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    return ""


def find_decorator_order_violations_for_file(file_path: Path) -> list[str]:
    """Return decorator-order violations for one file."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue

        decorator_names = [_decorator_name(decorator) for decorator in node.decorator_list]
        if not {"server.tool", "handle_http_errors", "require_google_service"}.issubset(decorator_names):
            continue

        server_index = decorator_names.index("server.tool")
        handle_index = decorator_names.index("handle_http_errors")
        require_index = decorator_names.index("require_google_service")

        if not (server_index < handle_index < require_index):
            violations.append(
                f"{file_path}:{node.lineno} function '{node.name}' has invalid decorator order; "
                "expected @server.tool -> @handle_http_errors -> @require_google_service"
            )

    return violations


def _collect_default_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for module_dir in TOOL_MODULE_DIRS:
        dir_path = repo_root / module_dir
        if not dir_path.exists():
            continue
        files.extend(sorted(dir_path.rglob("*.py")))
    return files


def check_paths(paths: list[Path]) -> list[str]:
    """Run decorator checks for all provided paths."""
    violations: list[str] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            violations.extend(find_decorator_order_violations_for_file(path))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check MCP tool decorator order consistency.")
    parser.add_argument(
        "files",
        nargs="*",
        help="Optional explicit Python files to check. If omitted, checks all tool modules.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path for default module scanning (default: current directory).",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    if args.files:
        paths = [Path(file_path).resolve() for file_path in args.files]
    else:
        paths = _collect_default_files(repo_root)

    violations = check_paths(paths)
    if violations:
        print("Decorator order violations found:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Decorator order check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
