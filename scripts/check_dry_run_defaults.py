#!/usr/bin/env python3
"""Check that selected mutating tools enforce dry_run default safety."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

# Phase-gated coverage: include mutators with rollout already implemented.
REQUIRED_DRY_RUN_TOOLS: dict[str, list[str]] = {
    "gcalendar/calendar_tools.py": ["create_event", "modify_event", "delete_event"],
    "gdrive/files.py": ["create_drive_file", "update_drive_file"],
    "gdrive/permissions.py": [
        "share_drive_file",
        "batch_share_drive_file",
        "update_drive_permission",
        "remove_drive_permission",
        "transfer_drive_ownership",
    ],
    "gdrive/sync_tools.py": [
        "link_local_file",
        "update_google_doc",
        "download_google_doc",
        "upload_folder",
        "mirror_drive_folder",
        "download_doc_tabs",
    ],
    "gmail/messages.py": ["send_gmail_message", "draft_gmail_message"],
    "gmail/labels.py": ["manage_gmail_label", "modify_gmail_message_labels", "batch_modify_gmail_message_labels"],
    "gdocs/writing.py": [
        "create_doc",
        "modify_doc_text",
        "find_and_replace_doc",
        "update_doc_headers_footers",
        "batch_update_doc",
        "insert_markdown",
    ],
    "gdocs/elements.py": ["insert_doc_elements", "insert_doc_image"],
    "gdocs/tables.py": ["create_table_with_data"],
    "gsheets/sheets_tools.py": [
        "modify_sheet_values",
        "format_sheet_range",
        "add_conditional_formatting",
        "update_conditional_formatting",
        "delete_conditional_formatting",
        "create_spreadsheet",
        "create_sheet",
    ],
    "gslides/slides_tools.py": ["create_presentation", "batch_update_presentation"],
    "gforms/forms_tools.py": ["create_form", "set_publish_settings"],
    "gtasks/tasks_tools.py": [
        "create_task_list",
        "update_task_list",
        "delete_task_list",
        "create_task",
        "update_task",
        "delete_task",
        "move_task",
        "clear_completed_tasks",
    ],
    "gchat/chat_tools.py": ["send_message"],
    "gappsscript/apps_script_tools.py": [
        "create_script_project",
        "update_script_content",
        "create_version",
        "create_deployment",
        "update_deployment",
        "delete_deployment",
        "run_script_function",
    ],
}


def _resolve_arg_default(node: ast.AST, arg_name: str) -> ast.AST | None:
    """Return default node for a named argument, if present."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None

    positional_args = [*node.args.posonlyargs, *node.args.args]
    positional_defaults = list(node.args.defaults)

    if positional_defaults:
        start_idx = len(positional_args) - len(positional_defaults)
        defaults_by_name: dict[str, ast.AST] = {}
        for idx, arg in enumerate(positional_args):
            default_idx = idx - start_idx
            if default_idx >= 0:
                defaults_by_name[arg.arg] = positional_defaults[default_idx]
        if arg_name in defaults_by_name:
            return defaults_by_name[arg_name]

    for kw_arg, kw_default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True):
        if kw_arg.arg == arg_name:
            return kw_default

    return None


def _is_true_default(default_node: ast.AST | None) -> bool:
    """Return True when default is effectively True (e.g., True, Body(True))."""
    if default_node is None:
        return False

    if isinstance(default_node, ast.Constant):
        return default_node.value is True

    if isinstance(default_node, ast.Call):
        func_name = ""
        if isinstance(default_node.func, ast.Name):
            func_name = default_node.func.id
        elif isinstance(default_node.func, ast.Attribute):
            func_name = default_node.func.attr

        if func_name == "Body":
            if default_node.args:
                first_arg = default_node.args[0]
                if isinstance(first_arg, ast.Constant) and first_arg.value is True:
                    return True
            for keyword in default_node.keywords:
                if keyword.arg == "default" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    return True

    return False


def _find_function(tree: ast.AST, function_name: str) -> ast.AST | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    return None


def find_dry_run_violations_for_file(file_path: Path, required_functions: list[str]) -> list[str]:
    """Return dry-run signature violations for one source file."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    violations: list[str] = []

    for function_name in required_functions:
        function_node = _find_function(tree, function_name)
        if function_node is None:
            violations.append(f"{file_path}: function '{function_name}' not found")
            continue

        dry_run_default = _resolve_arg_default(function_node, "dry_run")
        if dry_run_default is None:
            violations.append(
                f"{file_path}:{function_node.lineno} function '{function_name}' is missing dry_run parameter"
            )
            continue

        if not _is_true_default(dry_run_default):
            violations.append(
                f"{file_path}:{function_node.lineno} function '{function_name}' must default dry_run to True"
            )

    return violations


def check_root(repo_root: Path) -> list[str]:
    """Run checker against required rollout tool set."""
    violations: list[str] = []
    for relative_path, function_names in REQUIRED_DRY_RUN_TOOLS.items():
        file_path = repo_root / relative_path
        if not file_path.exists():
            violations.append(f"{file_path}: required module missing")
            continue
        violations.extend(find_dry_run_violations_for_file(file_path, function_names))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check selected mutators for dry_run default safety.")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path (default: current directory).",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    violations = check_root(repo_root)
    if violations:
        print("Dry-run default violations found:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Dry-run default check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
