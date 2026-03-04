"""
Google Apps Script MCP Integration.

This module provides MCP tools for interacting with the Apps Script API.
"""

from .apps_script_tools import (
    create_deployment,
    create_script_project,
    create_version,
    delete_deployment,
    delete_script_project,
    get_script_content,
    get_script_metrics,
    get_script_project,
    get_version,
    list_deployments,
    list_script_processes,
    list_script_projects,
    list_versions,
    run_script_function,
    update_deployment,
    update_script_content,
)

__all__ = [
    "create_deployment",
    "create_script_project",
    "create_version",
    "delete_deployment",
    "delete_script_project",
    "get_script_content",
    "get_script_metrics",
    "get_script_project",
    "get_version",
    "list_deployments",
    "list_script_processes",
    "list_script_projects",
    "list_versions",
    "run_script_function",
    "update_deployment",
    "update_script_content",
]
