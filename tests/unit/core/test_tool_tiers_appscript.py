"""Unit tests for Apps Script tier wiring."""

from core.tool_tier_loader import ToolTierLoader, resolve_tools_from_tier


def test_appscript_tiers_are_defined_in_tool_tiers_config():
    loader = ToolTierLoader()

    assert "appscript" in loader.get_available_services()

    core_tools = loader.get_tools_for_tier("core", ["appscript"])
    extended_tools = loader.get_tools_for_tier("extended", ["appscript"])
    complete_tools = loader.get_tools_for_tier("complete", ["appscript"])

    assert core_tools == [
        "get_script_project",
        "list_script_projects",
        "get_script_content",
        "create_script_project",
        "update_script_content",
    ]
    assert extended_tools == [
        "create_deployment",
        "update_deployment",
        "delete_deployment",
        "create_version",
        "run_script_function",
        "delete_script_project",
        "list_deployments",
        "list_versions",
        "get_version",
        "list_script_processes",
        "get_script_metrics",
    ]
    assert complete_tools == []


def test_tier_resolution_for_appscript_service_only():
    core_tools, core_services = resolve_tools_from_tier("core", ["appscript"])
    extended_tools, extended_services = resolve_tools_from_tier("extended", ["appscript"])

    assert core_services == ["appscript"]
    assert set(core_tools) == {
        "get_script_project",
        "list_script_projects",
        "get_script_content",
        "create_script_project",
        "update_script_content",
    }

    assert extended_services == ["appscript"]
    assert set(extended_tools) == {
        "get_script_project",
        "list_script_projects",
        "get_script_content",
        "create_script_project",
        "update_script_content",
        "create_deployment",
        "update_deployment",
        "delete_deployment",
        "create_version",
        "run_script_function",
        "delete_script_project",
        "list_deployments",
        "list_versions",
        "get_version",
        "list_script_processes",
        "get_script_metrics",
    }
