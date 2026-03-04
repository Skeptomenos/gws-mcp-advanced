"""Unit tests for Apps Script service wiring and APPS-05 policy locks."""

import ast
from pathlib import Path

from auth.scopes import (
    DRIVE_FILE_SCOPE,
    DRIVE_READONLY_SCOPE,
    SCRIPT_DEPLOYMENTS_READONLY_SCOPE,
    SCRIPT_DEPLOYMENTS_SCOPE,
    SCRIPT_METRICS_SCOPE,
    SCRIPT_PROCESSES_SCOPE,
    SCRIPT_PROJECTS_READONLY_SCOPE,
    SCRIPT_PROJECTS_SCOPE,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAIN_PATH = PROJECT_ROOT / "main.py"
FASTMCP_SERVER_PATH = PROJECT_ROOT / "fastmcp_server.py"
APPS_SCRIPT_TOOLS_PATH = PROJECT_ROOT / "gappsscript" / "apps_script_tools.py"


def _parse_python_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _extract_main_tools_choices(tree: ast.Module) -> list[str]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument":
            continue

        has_tools_flag = any(
            isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value == "--tools" for arg in node.args
        )
        if not has_tools_flag:
            continue

        for keyword in node.keywords:
            if keyword.arg != "choices" or not isinstance(keyword.value, ast.List):
                continue
            choices: list[str] = []
            for element in keyword.value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    choices.append(element.value)
            return choices

    raise AssertionError("Could not find --tools choices in main.py")


def _extract_fastmcp_all_services(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != "all_services":
            continue
        if not isinstance(node.value, ast.List):
            continue

        services: list[str] = []
        for element in node.value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                services.append(element.value)
        return services

    raise AssertionError("Could not find all_services list in fastmcp_server.py")


def _extract_require_google_service_args(tree: ast.Module, function_name: str) -> tuple[str, str]:
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if node.name != function_name:
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Name):
                continue
            if decorator.func.id != "require_google_service":
                continue
            if len(decorator.args) < 2:
                raise AssertionError(f"@require_google_service on {function_name} is missing required arguments.")

            service_type = decorator.args[0]
            scope_alias = decorator.args[1]
            if (
                not isinstance(service_type, ast.Constant)
                or not isinstance(service_type.value, str)
                or not isinstance(scope_alias, ast.Constant)
                or not isinstance(scope_alias.value, str)
            ):
                raise AssertionError(f"@require_google_service args for {function_name} must be string constants.")
            return service_type.value, scope_alias.value

    raise AssertionError(f"Could not find @require_google_service on {function_name}")


def test_scopes_map_includes_appscript():
    from auth.scopes import APPS_SCRIPT_SCOPES, TOOL_SCOPES_MAP

    assert "appscript" in TOOL_SCOPES_MAP
    assert TOOL_SCOPES_MAP["appscript"] == APPS_SCRIPT_SCOPES
    assert set(APPS_SCRIPT_SCOPES) == {
        SCRIPT_PROJECTS_SCOPE,
        SCRIPT_PROJECTS_READONLY_SCOPE,
        SCRIPT_DEPLOYMENTS_SCOPE,
        SCRIPT_DEPLOYMENTS_READONLY_SCOPE,
        SCRIPT_PROCESSES_SCOPE,
        SCRIPT_METRICS_SCOPE,
        DRIVE_READONLY_SCOPE,
        DRIVE_FILE_SCOPE,
    }


def test_appscript_tool_scope_alias_matrix_matches_policy_lock():
    tree = _parse_python_file(APPS_SCRIPT_TOOLS_PATH)

    expected = {
        "get_script_project": ("appscript", "script_projects_read"),
        "list_script_projects": ("drive", "drive_read"),
        "delete_script_project": ("drive", "drive_file"),
        "get_script_content": ("appscript", "script_projects_read"),
        "list_deployments": ("appscript", "script_deployments_read"),
        "list_versions": ("appscript", "script_projects_read"),
        "get_version": ("appscript", "script_projects_read"),
        "list_script_processes": ("appscript", "script_processes"),
        "get_script_metrics": ("appscript", "script_metrics"),
        "create_script_project": ("appscript", "script_projects"),
        "update_script_content": ("appscript", "script_projects"),
        "create_version": ("appscript", "script_projects"),
        "run_script_function": ("appscript", "script_projects"),
        "create_deployment": ("appscript", "script_deployments"),
        "update_deployment": ("appscript", "script_deployments"),
        "delete_deployment": ("appscript", "script_deployments"),
    }
    for function_name, matrix_entry in expected.items():
        assert _extract_require_google_service_args(tree, function_name) == matrix_entry


def test_get_scopes_for_tools_appscript_is_least_privilege():
    from auth.scopes import BASE_SCOPES, get_scopes_for_tools

    scopes = set(get_scopes_for_tools(["appscript"]))
    assert scopes == set(BASE_SCOPES) | {
        SCRIPT_PROJECTS_SCOPE,
        SCRIPT_PROJECTS_READONLY_SCOPE,
        SCRIPT_DEPLOYMENTS_SCOPE,
        SCRIPT_DEPLOYMENTS_READONLY_SCOPE,
        SCRIPT_PROCESSES_SCOPE,
        SCRIPT_METRICS_SCOPE,
        DRIVE_READONLY_SCOPE,
        DRIVE_FILE_SCOPE,
    }


def test_service_decorator_includes_appscript():
    from auth.service_decorator import SCOPE_GROUPS, SERVICE_CONFIGS

    assert SERVICE_CONFIGS["appscript"] == {"service": "script", "version": "v1"}
    assert SCOPE_GROUPS["script_projects"] == SCRIPT_PROJECTS_SCOPE
    assert SCOPE_GROUPS["script_projects_read"] == SCRIPT_PROJECTS_READONLY_SCOPE
    assert SCOPE_GROUPS["script_deployments"] == SCRIPT_DEPLOYMENTS_SCOPE
    assert SCOPE_GROUPS["script_deployments_read"] == SCRIPT_DEPLOYMENTS_READONLY_SCOPE
    assert SCOPE_GROUPS["script_processes"] == SCRIPT_PROCESSES_SCOPE
    assert SCOPE_GROUPS["script_metrics"] == SCRIPT_METRICS_SCOPE


def test_api_enablement_maps_appscript_service():
    from core.api_enablement import API_ENABLEMENT_LINKS, INTERNAL_SERVICE_TO_API, SERVICE_NAME_TO_API

    assert API_ENABLEMENT_LINKS["script.googleapis.com"].endswith("apiid=script.googleapis.com")
    assert SERVICE_NAME_TO_API["Google Apps Script"] == "script.googleapis.com"
    assert INTERNAL_SERVICE_TO_API["appscript"] == "script.googleapis.com"
    assert INTERNAL_SERVICE_TO_API["script"] == "script.googleapis.com"


def test_main_tools_choices_include_appscript():
    tree = _parse_python_file(MAIN_PATH)
    choices = _extract_main_tools_choices(tree)

    assert "appscript" in choices


def test_fastmcp_server_services_include_appscript():
    tree = _parse_python_file(FASTMCP_SERVER_PATH)
    all_services = _extract_fastmcp_all_services(tree)

    assert "appscript" in all_services
