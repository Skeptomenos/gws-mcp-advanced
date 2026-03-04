"""Google Apps Script MCP tools."""

import json
import logging
from typing import Any, TypeVar

from googleapiclient.errors import HttpError
from pydantic import BaseModel, ValidationError

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors
from gappsscript.apps_script_manager import AppsScriptManager
from gappsscript.models import (
    CreateScriptProjectPayload,
    DeploymentMutationPayload,
    MetricsFilter,
    MetricsGranularity,
    RunFunctionPayload,
    ScriptProcessFilter,
    UpdateScriptContentPayload,
    UserProcessFilter,
)

logger = logging.getLogger(__name__)
FilterModelT = TypeVar("FilterModelT", bound=BaseModel)


def _parse_optional_filter_json(
    raw_json: str | None,
    model_type: type[FilterModelT],
    param_name: str,
) -> dict[str, Any] | None:
    if raw_json is None:
        return None

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{param_name} must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{param_name} must be a JSON object.")

    try:
        validated = model_type.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid {param_name}: {exc}") from exc

    # Use JSON mode so Enum values are serialized to raw API strings.
    return validated.model_dump(by_alias=True, exclude_none=True, mode="json")


def _parse_json_list(raw_json: str, param_name: str) -> list[Any]:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{param_name} must be valid JSON.") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"{param_name} must be a JSON list.")
    return parsed


def _normalize_script_files_payload(files_payload: list[Any]) -> list[dict[str, Any]]:
    """
    Normalize file payloads to writable Apps Script fields only.

    Accepts raw objects from `get_script_content` (which include read-only metadata)
    and strips them down to `{name, type, source}` for update calls.
    """
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(files_payload):
        if not isinstance(item, dict):
            raise ValueError(f"files_json[{index}] must be an object.")

        missing = [key for key in ("name", "type", "source") if key not in item]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"files_json[{index}] is missing required keys: {missing_text}.")

        normalized.append(
            {
                "name": item["name"],
                "type": item["type"],
                "source": item["source"],
            }
        )
    return normalized


def _extract_execution_api_access(content: dict[str, Any]) -> str | None:
    """Best-effort extraction of appsscript.json execution API access mode."""
    files = content.get("files", [])
    for script_file in files:
        if script_file.get("name") != "appsscript" or script_file.get("type") != "JSON":
            continue
        source = script_file.get("source", "")
        if not isinstance(source, str):
            return None
        try:
            manifest = json.loads(source)
        except json.JSONDecodeError:
            return None
        execution_api = manifest.get("executionApi")
        if isinstance(execution_api, dict):
            access = execution_api.get("access")
            if isinstance(access, str) and access.strip():
                return access.strip()
        return None
    return None


@server.tool()
@handle_http_errors("get_script_project", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_projects_read")
async def get_script_project(
    service,
    user_google_email: str,
    script_id: str,
) -> str:
    """
    Get metadata for an Apps Script project.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.

    Returns:
        str: Formatted Apps Script project metadata.
    """
    logger.info("[get_script_project] Invoked for script_id='%s'", script_id)
    manager = AppsScriptManager(service)
    project = await manager.get_script_project(script_id)

    return (
        "Apps Script Project:\n"
        f"- Script ID: {project.script_id}\n"
        f"- Title: {project.title or 'Untitled'}\n"
        f"- Parent ID: {project.parent_id or 'None'}\n"
        f"- Created: {project.create_time or 'Unknown'}\n"
        f"- Updated: {project.update_time or 'Unknown'}"
    )


@server.tool()
@handle_http_errors("list_script_projects", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def list_script_projects(
    service,
    user_google_email: str,
    page_size: int = 50,
    page_token: str | None = None,
) -> str:
    """
    List standalone Apps Script projects from Google Drive.

    Limitation: container-bound scripts are excluded by design because this tool
    is Drive-backed and only lists files of mimeType `application/vnd.google-apps.script`.

    Args:
        user_google_email: The user's Google email address. Required.
        page_size: Number of results to return. Defaults to 50.
        page_token: Optional pagination token.

    Returns:
        str: Formatted standalone Apps Script Drive file list.
    """
    logger.info(
        "[list_script_projects] Invoked with page_size=%s, page_token_present=%s",
        page_size,
        page_token is not None,
    )
    manager = AppsScriptManager(service)
    result = await manager.list_script_projects(page_size=page_size, page_token=page_token)
    files = result.get("files", [])
    next_page_token = result.get("nextPageToken")

    limitation = (
        "Limitation: only standalone Apps Script projects are listed (container-bound scripts are not included)."
    )

    if not files:
        empty_message = f"No standalone Apps Script projects found for {user_google_email}.\n{limitation}"
        if next_page_token:
            empty_message += f"\nNext Page Token: {next_page_token}"
        return empty_message

    lines = [f"Found {len(files)} standalone Apps Script project(s) for {user_google_email}:", limitation]
    for item in files:
        lines.append(
            f'- Name: "{item.get("name", "Untitled")}" '
            f"(ID: {item.get('id', 'N/A')}, Modified: {item.get('modifiedTime', 'N/A')}) "
            f"Link: {item.get('webViewLink', '#')}"
        )

    if next_page_token:
        lines.append(f"Next Page Token: {next_page_token}")

    return "\n".join(lines)


@server.tool()
@handle_http_errors("delete_script_project", service_type="drive")
@require_google_service("drive", "drive_file")
async def delete_script_project(
    service,
    user_google_email: str,
    script_id: str,
    dry_run: bool = True,
) -> str:
    """
    Delete (trash) a standalone Apps Script project by Drive file ID.

    Limitation: only standalone script files are supported. Container-bound scripts
    are not addressable via this Drive-backed deletion path.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: Apps Script Drive file ID.
        dry_run: Preview deletion without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or deletion.
    """
    logger.info("[delete_script_project] Invoked for script_id='%s' (dry_run=%s)", script_id, dry_run)
    manager = AppsScriptManager(service)
    metadata = await manager.get_drive_script_metadata(script_id)

    limitation = (
        "Limitation: this tool only supports standalone Apps Script Drive files; container-bound scripts are excluded."
    )

    if dry_run:
        return (
            "DRY RUN: Would move standalone Apps Script project to trash.\n"
            f"- Name: {metadata.get('name', 'Untitled')}\n"
            f"- Script ID: {metadata.get('id', script_id)}\n"
            f"- Link: {metadata.get('webViewLink', '#')}\n"
            f"{limitation}"
        )

    deleted = await manager.delete_script_project(script_id)
    return (
        "Successfully moved standalone Apps Script project to trash.\n"
        f"- Name: {deleted.get('name', metadata.get('name', 'Untitled'))}\n"
        f"- Script ID: {deleted.get('id', script_id)}\n"
        f"- Trashed: {deleted.get('trashed', True)}\n"
        f"- Link: {deleted.get('webViewLink', metadata.get('webViewLink', '#'))}\n"
        f"{limitation}"
    )


@server.tool()
@handle_http_errors("get_script_content", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_projects_read")
async def get_script_content(
    service,
    user_google_email: str,
    script_id: str,
    version_number: int | None = None,
) -> str:
    """
    Get Apps Script project content, optionally pinned to a version.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        version_number: Optional script version number.

    Returns:
        str: Script files and metadata.
    """
    logger.info(
        "[get_script_content] Invoked for script_id='%s' (version_number=%s)",
        script_id,
        version_number,
    )
    manager = AppsScriptManager(service)
    content = await manager.get_script_content(script_id=script_id, version_number=version_number)
    files = content.get("files", [])
    resolved_version = content.get("scriptVersion", {}).get("versionNumber")

    lines = [
        "Apps Script Content:",
        f"- Script ID: {content.get('scriptId', script_id)}",
        f"- Version: {resolved_version if resolved_version is not None else (version_number or 'Latest')}",
        f"- Files: {len(files)}",
    ]

    if not files:
        return "\n".join(lines)

    for script_file in files:
        lines.append(
            f"\nFile: {script_file.get('name', 'Unnamed')} "
            f"(type: {script_file.get('type', 'UNKNOWN')})\n{script_file.get('source', '')}"
        )

    return "\n".join(lines)


@server.tool()
@handle_http_errors("list_deployments", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_deployments_read")
async def list_deployments(
    service,
    user_google_email: str,
    script_id: str,
    page_size: int = 50,
    page_token: str | None = None,
) -> str:
    """
    List deployments for an Apps Script project.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        page_size: Number of results to return. Defaults to 50.
        page_token: Optional pagination token.

    Returns:
        str: Deployment list summary.
    """
    logger.info(
        "[list_deployments] Invoked for script_id='%s' (page_size=%s, page_token_present=%s)",
        script_id,
        page_size,
        page_token is not None,
    )
    manager = AppsScriptManager(service)
    response = await manager.list_deployments(script_id=script_id, page_size=page_size, page_token=page_token)
    deployments = response.get("deployments", [])
    next_page_token = response.get("nextPageToken")

    if not deployments:
        message = f"No deployments found for script '{script_id}'."
        if next_page_token:
            message += f"\nNext Page Token: {next_page_token}"
        return message

    lines = [f"Found {len(deployments)} deployment(s) for script '{script_id}':"]
    for deployment in deployments:
        config = deployment.get("deploymentConfig", {})
        lines.append(
            f"- Deployment ID: {deployment.get('deploymentId', 'N/A')} "
            f"(Version: {config.get('versionNumber', 'N/A')}, "
            f"Description: {config.get('description', 'None')}, "
            f"Updated: {deployment.get('updateTime', 'N/A')})"
        )

    if next_page_token:
        lines.append(f"Next Page Token: {next_page_token}")
    return "\n".join(lines)


@server.tool()
@handle_http_errors("list_versions", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_projects_read")
async def list_versions(
    service,
    user_google_email: str,
    script_id: str,
    page_size: int = 50,
    page_token: str | None = None,
) -> str:
    """
    List versions for an Apps Script project.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        page_size: Number of results to return. Defaults to 50.
        page_token: Optional pagination token.

    Returns:
        str: Version list summary.
    """
    logger.info(
        "[list_versions] Invoked for script_id='%s' (page_size=%s, page_token_present=%s)",
        script_id,
        page_size,
        page_token is not None,
    )
    manager = AppsScriptManager(service)
    response = await manager.list_versions(script_id=script_id, page_size=page_size, page_token=page_token)
    versions = response.get("versions", [])
    next_page_token = response.get("nextPageToken")

    if not versions:
        message = f"No versions found for script '{script_id}'."
        if next_page_token:
            message += f"\nNext Page Token: {next_page_token}"
        return message

    lines = [f"Found {len(versions)} version(s) for script '{script_id}':"]
    for version in versions:
        lines.append(
            f"- Version: {version.get('versionNumber', 'N/A')} "
            f"(Description: {version.get('description', 'None')}, "
            f"Created: {version.get('createTime', 'N/A')})"
        )

    if next_page_token:
        lines.append(f"Next Page Token: {next_page_token}")
    return "\n".join(lines)


@server.tool()
@handle_http_errors("get_version", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_projects_read")
async def get_version(
    service,
    user_google_email: str,
    script_id: str,
    version_number: int,
) -> str:
    """
    Get metadata for a specific Apps Script version.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        version_number: Script version number.

    Returns:
        str: Version metadata.
    """
    logger.info("[get_version] Invoked for script_id='%s', version_number=%s", script_id, version_number)
    manager = AppsScriptManager(service)
    version = await manager.get_version(script_id=script_id, version_number=version_number)

    return (
        "Apps Script Version:\n"
        f"- Script ID: {script_id}\n"
        f"- Version Number: {version.get('versionNumber', version_number)}\n"
        f"- Description: {version.get('description', 'None')}\n"
        f"- Created: {version.get('createTime', 'Unknown')}"
    )


@server.tool()
@handle_http_errors("list_script_processes", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_processes")
async def list_script_processes(
    service,
    user_google_email: str,
    script_id: str | None = None,
    script_process_filter_json: str | None = None,
    user_process_filter_json: str | None = None,
    page_size: int = 50,
    page_token: str | None = None,
) -> str:
    """
    List Apps Script processes.

    If `script_id` is provided, uses script-specific process listing.
    Otherwise, uses user-wide process listing.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: Optional script ID for script-specific listing.
        script_process_filter_json: Optional JSON object for script process filter.
        user_process_filter_json: Optional JSON object for user process filter.
        page_size: Number of results to return. Defaults to 50.
        page_token: Optional pagination token.

    Returns:
        str: Process list summary.
    """
    logger.info(
        "[list_script_processes] Invoked (script_id=%s, page_size=%s, page_token_present=%s)",
        script_id,
        page_size,
        page_token is not None,
    )
    manager = AppsScriptManager(service)
    script_filter = _parse_optional_filter_json(
        script_process_filter_json,
        ScriptProcessFilter,
        "script_process_filter_json",
    )
    user_filter = _parse_optional_filter_json(
        user_process_filter_json,
        UserProcessFilter,
        "user_process_filter_json",
    )

    response = await manager.list_script_processes(
        script_id=script_id,
        script_process_filter=script_filter,
        user_process_filter=user_filter,
        page_size=page_size,
        page_token=page_token,
    )

    processes = response.get("processes", [])
    next_page_token = response.get("nextPageToken")
    mode = f"script '{script_id}'" if script_id else f"user '{user_google_email}'"

    if not processes:
        message = f"No processes found for {mode}."
        if next_page_token:
            message += f"\nNext Page Token: {next_page_token}"
        return message

    lines = [f"Found {len(processes)} process(es) for {mode}:"]
    for process in processes:
        lines.append(
            f"- Process ID: {process.get('processId', 'N/A')} "
            f"(Function: {process.get('functionName', 'N/A')}, "
            f"Type: {process.get('processType', 'N/A')}, "
            f"Status: {process.get('processStatus', 'N/A')}, "
            f"Started: {process.get('startTime', 'N/A')})"
        )

    if next_page_token:
        lines.append(f"Next Page Token: {next_page_token}")
    return "\n".join(lines)


@server.tool()
@handle_http_errors("get_script_metrics", is_read_only=True, service_type="appscript")
@require_google_service("appscript", "script_metrics")
async def get_script_metrics(
    service,
    user_google_email: str,
    script_id: str,
    metrics_granularity: str = "DAILY",
    metrics_filter_json: str | None = None,
) -> str:
    """
    Get Apps Script metrics for a script.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        metrics_granularity: Metrics granularity (`DAILY` or `WEEKLY`).
        metrics_filter_json: Optional JSON object for metrics filter.

    Returns:
        str: Metrics summary.
    """
    logger.info(
        "[get_script_metrics] Invoked for script_id='%s' (metrics_granularity=%s)",
        script_id,
        metrics_granularity,
    )
    manager = AppsScriptManager(service)
    validated_granularity = MetricsGranularity(metrics_granularity)
    metrics_filter = _parse_optional_filter_json(metrics_filter_json, MetricsFilter, "metrics_filter_json")

    response = await manager.get_script_metrics(
        script_id=script_id,
        metrics_granularity=validated_granularity.value,
        metrics_filter=metrics_filter,
    )

    return (
        "Apps Script Metrics:\n"
        f"- Script ID: {script_id}\n"
        f"- Granularity: {validated_granularity.value}\n"
        f"- Data: {json.dumps(response, sort_keys=True)}"
    )


@server.tool()
@handle_http_errors("create_script_project", service_type="appscript")
@require_google_service("appscript", "script_projects")
async def create_script_project(
    service,
    user_google_email: str,
    title: str,
    parent_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """
    Create a new Apps Script project.

    Args:
        user_google_email: The user's Google email address. Required.
        title: Script project title.
        parent_id: Optional parent Drive file ID.
        dry_run: Preview creation without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or creation.
    """
    payload = CreateScriptProjectPayload.model_validate({"title": title, "parentId": parent_id})
    logger.info("[create_script_project] Invoked (dry_run=%s, parent_id_present=%s)", dry_run, parent_id is not None)

    if dry_run:
        return (
            "DRY RUN: Would create Apps Script project.\n"
            f"- Title: {payload.title}\n"
            f"- Parent ID: {payload.parent_id or 'None'}"
        )

    manager = AppsScriptManager(service)
    created = await manager.create_script_project(title=payload.title, parent_id=payload.parent_id)
    script_id = created.get("scriptId", "N/A")
    return (
        "Successfully created Apps Script project.\n"
        f"- Script ID: {script_id}\n"
        f"- Title: {created.get('title', payload.title)}\n"
        f"- Parent ID: {created.get('parentId', payload.parent_id or 'None')}\n"
        f"- Link: https://script.google.com/d/{script_id}/edit"
    )


@server.tool()
@handle_http_errors("update_script_content", service_type="appscript")
@require_google_service("appscript", "script_projects")
async def update_script_content(
    service,
    user_google_email: str,
    script_id: str,
    files_json: str,
    dry_run: bool = True,
) -> str:
    """
    Update Apps Script project files.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        files_json: JSON list of file objects (`name`, `type`, `source`).
        dry_run: Preview content update without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or update.
    """
    files_payload = _parse_json_list(files_json, "files_json")
    normalized_files = _normalize_script_files_payload(files_payload)
    validated_payload = UpdateScriptContentPayload.model_validate({"files": normalized_files})
    file_names = [file.name for file in validated_payload.files]
    logger.info(
        "[update_script_content] Invoked for script_id='%s' (files=%s, dry_run=%s)", script_id, len(file_names), dry_run
    )

    if dry_run:
        return (
            "DRY RUN: Would update Apps Script content.\n"
            f"- Script ID: {script_id}\n"
            f"- Files: {len(file_names)}\n"
            f"- File Names: {', '.join(file_names)}"
        )

    manager = AppsScriptManager(service)
    updated = await manager.update_script_content(
        script_id=script_id,
        files=[file.model_dump(by_alias=True) for file in validated_payload.files],
    )
    return (
        "Successfully updated Apps Script content.\n"
        f"- Script ID: {updated.get('scriptId', script_id)}\n"
        f"- Files: {len(updated.get('files', []))}\n"
        f"- Link: https://script.google.com/d/{updated.get('scriptId', script_id)}/edit"
    )


@server.tool()
@handle_http_errors("create_version", service_type="appscript")
@require_google_service("appscript", "script_projects")
async def create_version(
    service,
    user_google_email: str,
    script_id: str,
    description: str | None = None,
    dry_run: bool = True,
) -> str:
    """
    Create a new version for an Apps Script project.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        description: Optional version description.
        dry_run: Preview version creation without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or version creation.
    """
    logger.info("[create_version] Invoked for script_id='%s' (dry_run=%s)", script_id, dry_run)

    if dry_run:
        return (
            "DRY RUN: Would create Apps Script version.\n"
            f"- Script ID: {script_id}\n"
            f"- Description: {description or 'None'}"
        )

    manager = AppsScriptManager(service)
    version = await manager.create_version(script_id=script_id, description=description)
    return (
        "Successfully created Apps Script version.\n"
        f"- Script ID: {script_id}\n"
        f"- Version Number: {version.get('versionNumber', 'N/A')}\n"
        f"- Description: {version.get('description', description or 'None')}\n"
        f"- Created: {version.get('createTime', 'Unknown')}"
    )


@server.tool()
@handle_http_errors("create_deployment", service_type="appscript")
@require_google_service("appscript", "script_deployments")
async def create_deployment(
    service,
    user_google_email: str,
    script_id: str,
    description: str,
    version_number: int,
    dry_run: bool = True,
) -> str:
    """
    Create an Apps Script deployment.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        description: Deployment description.
        version_number: Version number for deployment (must be >= 1).
        dry_run: Preview deployment creation without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or deployment creation.
    """
    payload = DeploymentMutationPayload.model_validate({"description": description, "versionNumber": version_number})
    logger.info(
        "[create_deployment] Invoked for script_id='%s' (version_number=%s, dry_run=%s)",
        script_id,
        payload.version_number,
        dry_run,
    )

    if dry_run:
        return (
            "DRY RUN: Would create Apps Script deployment.\n"
            f"- Script ID: {script_id}\n"
            f"- Description: {payload.description}\n"
            f"- Version Number: {payload.version_number}"
        )

    manager = AppsScriptManager(service)
    deployment = await manager.create_deployment(
        script_id=script_id,
        description=payload.description,
        version_number=payload.version_number,
    )
    deployment_config = deployment.get("deploymentConfig", {})
    return (
        "Successfully created Apps Script deployment.\n"
        f"- Script ID: {script_id}\n"
        f"- Deployment ID: {deployment.get('deploymentId', 'N/A')}\n"
        f"- Version Number: {deployment_config.get('versionNumber', payload.version_number)}\n"
        f"- Description: {deployment_config.get('description', payload.description)}"
    )


@server.tool()
@handle_http_errors("update_deployment", service_type="appscript")
@require_google_service("appscript", "script_deployments")
async def update_deployment(
    service,
    user_google_email: str,
    script_id: str,
    deployment_id: str,
    description: str,
    version_number: int | None = None,
    dry_run: bool = True,
) -> str:
    """
    Update an Apps Script deployment.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        deployment_id: The deployment ID to update.
        description: Updated deployment description.
        version_number: Optional target version number.
        dry_run: Preview deployment update without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or update.
    """
    payload = DeploymentMutationPayload.model_validate({"description": description, "versionNumber": version_number})
    manager = AppsScriptManager(service)
    current = await manager.get_deployment(script_id=script_id, deployment_id=deployment_id)
    current_config = current.get("deploymentConfig", {})
    logger.info(
        "[update_deployment] Invoked for script_id='%s', deployment_id='%s' (dry_run=%s)",
        script_id,
        deployment_id,
        dry_run,
    )

    target_version = (
        payload.version_number if payload.version_number is not None else current_config.get("versionNumber")
    )
    if dry_run:
        return (
            "DRY RUN: Would update Apps Script deployment.\n"
            f"- Script ID: {script_id}\n"
            f"- Deployment ID: {deployment_id}\n"
            f"- Current Description: {current_config.get('description', 'None')}\n"
            f"- New Description: {payload.description}\n"
            f"- Target Version Number: {target_version or 'Unknown'}"
        )

    updated = await manager.update_deployment(
        script_id=script_id,
        deployment_id=deployment_id,
        description=payload.description,
        version_number=payload.version_number,
    )
    updated_config = updated.get("deploymentConfig", {})
    return (
        "Successfully updated Apps Script deployment.\n"
        f"- Script ID: {script_id}\n"
        f"- Deployment ID: {updated.get('deploymentId', deployment_id)}\n"
        f"- Version Number: {updated_config.get('versionNumber', target_version or 'N/A')}\n"
        f"- Description: {updated_config.get('description', payload.description)}"
    )


@server.tool()
@handle_http_errors("delete_deployment", service_type="appscript")
@require_google_service("appscript", "script_deployments")
async def delete_deployment(
    service,
    user_google_email: str,
    script_id: str,
    deployment_id: str,
    dry_run: bool = True,
) -> str:
    """
    Delete an Apps Script deployment.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        deployment_id: The deployment ID to delete.
        dry_run: Preview deletion without mutation. Defaults to True.

    Returns:
        str: Confirmation of preview or deletion.
    """
    manager = AppsScriptManager(service)
    current = await manager.get_deployment(script_id=script_id, deployment_id=deployment_id)
    logger.info(
        "[delete_deployment] Invoked for script_id='%s', deployment_id='%s' (dry_run=%s)",
        script_id,
        deployment_id,
        dry_run,
    )
    if dry_run:
        return (
            "DRY RUN: Would delete Apps Script deployment.\n"
            f"- Script ID: {script_id}\n"
            f"- Deployment ID: {deployment_id}\n"
            f"- Description: {current.get('deploymentConfig', {}).get('description', 'None')}"
        )

    await manager.delete_deployment(script_id=script_id, deployment_id=deployment_id)
    return f"Successfully deleted Apps Script deployment.\n- Script ID: {script_id}\n- Deployment ID: {deployment_id}"


@server.tool()
@handle_http_errors("run_script_function", service_type="appscript")
@require_google_service("appscript", "script_projects")
async def run_script_function(
    service,
    user_google_email: str,
    script_id: str,
    function_name: str,
    parameters_json: str | None = None,
    dev_mode: bool = False,
    dry_run: bool = True,
) -> str:
    """
    Execute a function in an Apps Script project.

    Args:
        user_google_email: The user's Google email address. Required.
        script_id: The Apps Script project ID.
        function_name: Target function name.
        parameters_json: Optional JSON list of function parameters.
        dev_mode: Whether to run in development mode. Defaults to False.
        dry_run: Preview execution without calling API. Defaults to True.

    Returns:
        str: Execution preview or result.
    """
    parameters = _parse_json_list(parameters_json, "parameters_json") if parameters_json is not None else None
    payload = RunFunctionPayload.model_validate(
        {
            "functionName": function_name,
            "parameters": parameters,
            "devMode": dev_mode,
        }
    )
    param_count = len(payload.parameters or [])
    logger.info(
        "[run_script_function] Invoked for script_id='%s', function='%s' (param_count=%s, dry_run=%s, dev_mode=%s)",
        script_id,
        payload.function_name,
        param_count,
        dry_run,
        payload.dev_mode,
    )

    if dry_run:
        return (
            "DRY RUN: Would execute Apps Script function.\n"
            f"- Script ID: {script_id}\n"
            f"- Function: {payload.function_name}\n"
            f"- Parameters: {param_count}\n"
            f"- Dev Mode: {payload.dev_mode}"
        )

    manager = AppsScriptManager(service)
    execution_api_access: str | None = None
    try:
        script_content = await manager.get_script_content(script_id=script_id)
        execution_api_access = _extract_execution_api_access(script_content)
    except Exception:
        # Preflight metadata is best effort and should not block execution attempts.
        execution_api_access = None

    execution_target_id = script_id
    resolved_deployment_id: str | None = None
    if not payload.dev_mode:
        try:
            resolved_deployment_id = await manager.get_execution_api_deployment_id(script_id=script_id)
        except Exception:
            resolved_deployment_id = None
        if resolved_deployment_id:
            execution_target_id = resolved_deployment_id

    try:
        execution = await manager.run_script_function(
            script_id=execution_target_id,
            function_name=payload.function_name,
            parameters=payload.parameters,
            dev_mode=payload.dev_mode,
        )
    except HttpError as error:
        status = getattr(getattr(error, "resp", None), "status", None)
        if status in (403, 404):
            reason = error._get_reason() if hasattr(error, "_get_reason") else str(error)
            access_text = execution_api_access if execution_api_access is not None else "NOT_SET"
            return (
                "Apps Script execution failed (precondition).\n"
                f"- Script ID: {script_id}\n"
                f"- Function: {payload.function_name}\n"
                f"- HTTP Status: {status}\n"
                f"- API Reason: {reason}\n"
                f"- Manifest executionApi.access: {access_text}\n"
                f"- Execution target: {execution_target_id}\n"
                "Next Steps:\n"
                "1. Ensure appsscript.json has executionApi.access (usually `MYSELF`).\n"
                "2. Create a new version and deployment after manifest/code updates.\n"
                "3. Open the script in Apps Script editor and run a function once to complete consent.\n"
                "4. Retry with dev_mode=True for owner testing, then dev_mode=False for deployed execution."
            )
        raise

    if "error" in execution:
        error = execution.get("error", {})
        return (
            "Apps Script execution failed.\n"
            f"- Script ID: {script_id}\n"
            f"- Function: {payload.function_name}\n"
            f"- Message: {error.get('message', 'Unknown error')}\n"
            f"- Details: {json.dumps(error.get('details', []), sort_keys=True)}"
        )

    return (
        "Apps Script execution succeeded.\n"
        f"- Script ID: {script_id}\n"
        f"- Function: {payload.function_name}\n"
        f"- Response: {json.dumps(execution.get('response', {}), sort_keys=True)}"
    )
