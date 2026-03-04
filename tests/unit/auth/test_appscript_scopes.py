"""Unit tests for Apps Script scope policy locks (APPS-05)."""

from auth.scopes import (
    BASE_SCOPES,
    DRIVE_FILE_SCOPE,
    DRIVE_READONLY_SCOPE,
    DRIVE_SCOPE,
    SCRIPT_DEPLOYMENTS_READONLY_SCOPE,
    SCRIPT_DEPLOYMENTS_SCOPE,
    SCRIPT_METRICS_SCOPE,
    SCRIPT_PROCESSES_SCOPE,
    SCRIPT_PROJECTS_READONLY_SCOPE,
    SCRIPT_PROJECTS_SCOPE,
    get_scopes_for_tools,
)


def test_appscript_scope_set_is_locked_to_current_tool_surface():
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


def test_appscript_scope_set_excludes_future_script_mutation_scopes():
    scopes = set(get_scopes_for_tools(["appscript"]))

    assert SCRIPT_PROJECTS_SCOPE in scopes
    assert SCRIPT_DEPLOYMENTS_SCOPE in scopes
    assert SCRIPT_DEPLOYMENTS_READONLY_SCOPE in scopes
    assert SCRIPT_PROCESSES_SCOPE in scopes
    assert SCRIPT_METRICS_SCOPE in scopes


def test_appscript_scope_set_does_not_include_full_drive_scope_unless_drive_service_enabled():
    appscript_only_scopes = set(get_scopes_for_tools(["appscript"]))
    appscript_and_drive_scopes = set(get_scopes_for_tools(["appscript", "drive"]))

    assert DRIVE_SCOPE not in appscript_only_scopes
    assert DRIVE_SCOPE in appscript_and_drive_scopes
