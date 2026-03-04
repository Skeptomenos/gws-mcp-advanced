"""
Apps Script manager layer.

This module contains business logic for Apps Script operations.
"""

import asyncio
import re
from typing import Any

from gappsscript.models import ScriptProject

_SCRIPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_DEPLOYMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_FUNCTION_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SCRIPT_MIME_TYPE = "application/vnd.google-apps.script"
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000


class AppsScriptManager:
    """Manager for Apps Script API operations."""

    def __init__(self, service: Any):
        self.service = service

    @staticmethod
    def _validate_script_id(script_id: str) -> str:
        normalized = script_id.strip()
        if not normalized:
            raise ValueError("script_id is required and cannot be empty.")
        if not _SCRIPT_ID_PATTERN.fullmatch(normalized):
            raise ValueError("script_id contains invalid characters.")
        return normalized

    @staticmethod
    def _validate_page_size(page_size: int) -> int:
        if page_size < 1:
            raise ValueError("page_size must be >= 1.")
        if page_size > MAX_PAGE_SIZE:
            raise ValueError(f"page_size cannot exceed {MAX_PAGE_SIZE}.")
        return page_size

    @staticmethod
    def _validate_version_number(version_number: int) -> int:
        if version_number < 1:
            raise ValueError("version_number must be >= 1.")
        return version_number

    @staticmethod
    def _validate_deployment_id(deployment_id: str) -> str:
        normalized = deployment_id.strip()
        if not normalized:
            raise ValueError("deployment_id is required and cannot be empty.")
        if not _DEPLOYMENT_ID_PATTERN.fullmatch(normalized):
            raise ValueError("deployment_id contains invalid characters.")
        return normalized

    @staticmethod
    def _validate_function_name(function_name: str) -> str:
        normalized = function_name.strip()
        if not normalized:
            raise ValueError("function_name is required and cannot be empty.")
        if not _FUNCTION_NAME_PATTERN.fullmatch(normalized):
            raise ValueError("function_name is invalid. Use letters, numbers, and underscores only.")
        return normalized

    @staticmethod
    def _expand_process_filter(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Map validated filter payload keys into Apps Script API query kwargs."""
        expanded: dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            expanded[f"{prefix}_{key}"] = value
        return expanded

    async def get_script_project(self, script_id: str) -> ScriptProject:
        """Fetch script project metadata by ID."""
        validated_script_id = self._validate_script_id(script_id)
        response = await asyncio.to_thread(self.service.projects().get(scriptId=validated_script_id).execute)
        return ScriptProject.model_validate(response)

    async def get_script_content(self, script_id: str, version_number: int | None = None) -> dict[str, Any]:
        """Fetch script project content, optionally pinned to a version."""
        validated_script_id = self._validate_script_id(script_id)
        request_params: dict[str, Any] = {"scriptId": validated_script_id}
        if version_number is not None:
            request_params["versionNumber"] = self._validate_version_number(version_number)
        return await asyncio.to_thread(self.service.projects().getContent(**request_params).execute)

    async def create_script_project(self, title: str, parent_id: str | None = None) -> dict[str, Any]:
        """Create an Apps Script project."""
        payload: dict[str, Any] = {"title": title}
        if parent_id:
            payload["parentId"] = parent_id
        return await asyncio.to_thread(self.service.projects().create(body=payload).execute)

    async def update_script_content(self, script_id: str, files: list[dict[str, Any]]) -> dict[str, Any]:
        """Update full script content."""
        validated_script_id = self._validate_script_id(script_id)
        return await asyncio.to_thread(
            self.service.projects().updateContent(scriptId=validated_script_id, body={"files": files}).execute
        )

    async def list_deployments(
        self,
        script_id: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List deployments for a script project."""
        validated_script_id = self._validate_script_id(script_id)
        validated_page_size = self._validate_page_size(page_size)
        request_params: dict[str, Any] = {"scriptId": validated_script_id, "pageSize": validated_page_size}
        if page_token:
            request_params["pageToken"] = page_token
        return await asyncio.to_thread(self.service.projects().deployments().list(**request_params).execute)

    async def get_execution_api_deployment_id(self, script_id: str) -> str | None:
        """
        Resolve an EXECUTION_API deployment ID for a script, if present.

        This supports Script API executions where deployment IDs are more reliable
        than project IDs for non-dev invocation paths.
        """
        response = await self.list_deployments(script_id=script_id, page_size=MAX_PAGE_SIZE)
        deployments = response.get("deployments", []) if isinstance(response, dict) else []
        if not isinstance(deployments, list):
            return None

        execution_deployments: list[dict[str, Any]] = []
        for deployment in deployments:
            if not isinstance(deployment, dict):
                continue
            entry_points = deployment.get("entryPoints", [])
            if not isinstance(entry_points, list):
                continue
            if any(
                isinstance(entry_point, dict) and entry_point.get("entryPointType") == "EXECUTION_API"
                for entry_point in entry_points
            ):
                execution_deployments.append(deployment)

        if not execution_deployments:
            return None

        execution_deployments.sort(key=lambda item: str(item.get("updateTime", "")), reverse=True)
        deployment_id = execution_deployments[0].get("deploymentId")
        return deployment_id if isinstance(deployment_id, str) and deployment_id else None

    async def list_versions(
        self,
        script_id: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List versions for a script project."""
        validated_script_id = self._validate_script_id(script_id)
        validated_page_size = self._validate_page_size(page_size)
        request_params: dict[str, Any] = {"scriptId": validated_script_id, "pageSize": validated_page_size}
        if page_token:
            request_params["pageToken"] = page_token
        return await asyncio.to_thread(self.service.projects().versions().list(**request_params).execute)

    async def get_version(self, script_id: str, version_number: int) -> dict[str, Any]:
        """Fetch metadata for a specific script version."""
        validated_script_id = self._validate_script_id(script_id)
        validated_version_number = self._validate_version_number(version_number)
        return await asyncio.to_thread(
            self.service.projects()
            .versions()
            .get(scriptId=validated_script_id, versionNumber=validated_version_number)
            .execute
        )

    async def create_version(self, script_id: str, description: str | None = None) -> dict[str, Any]:
        """Create a new script version."""
        validated_script_id = self._validate_script_id(script_id)
        payload: dict[str, Any] = {}
        if description:
            payload["description"] = description
        return await asyncio.to_thread(
            self.service.projects().versions().create(scriptId=validated_script_id, body=payload).execute
        )

    async def list_script_processes(
        self,
        script_id: str | None = None,
        script_process_filter: dict[str, Any] | None = None,
        user_process_filter: dict[str, Any] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """
        List script processes using script-specific or user-wide API path.

        Rules:
        - If `script_id` is provided: uses `processes.listScriptProcesses` and only accepts `script_process_filter`.
        - If `script_id` is omitted: uses `processes.list` and only accepts `user_process_filter`.
        """
        validated_page_size = self._validate_page_size(page_size)

        if script_id:
            validated_script_id = self._validate_script_id(script_id)
            if user_process_filter is not None:
                raise ValueError("user_process_filter_json is not allowed when script_id is provided.")

            request_params: dict[str, Any] = {
                "scriptId": validated_script_id,
                "pageSize": validated_page_size,
            }
            if page_token:
                request_params["pageToken"] = page_token
            if script_process_filter:
                request_params.update(self._expand_process_filter("scriptProcessFilter", script_process_filter))
            return await asyncio.to_thread(self.service.processes().listScriptProcesses(**request_params).execute)

        if script_process_filter is not None:
            raise ValueError("script_process_filter_json requires script_id.")

        request_params = {"pageSize": validated_page_size}
        if page_token:
            request_params["pageToken"] = page_token
        if user_process_filter:
            request_params.update(self._expand_process_filter("userProcessFilter", user_process_filter))
        return await asyncio.to_thread(self.service.processes().list(**request_params).execute)

    async def run_script_function(
        self,
        script_id: str,
        function_name: str,
        parameters: list[object] | None = None,
        dev_mode: bool = False,
    ) -> dict[str, Any]:
        """Run a function in an Apps Script project."""
        validated_script_id = self._validate_script_id(script_id)
        validated_function_name = self._validate_function_name(function_name)

        body: dict[str, Any] = {"function": validated_function_name, "devMode": dev_mode}
        if parameters is not None:
            body["parameters"] = parameters
        return await asyncio.to_thread(self.service.scripts().run(scriptId=validated_script_id, body=body).execute)

    async def get_script_metrics(
        self,
        script_id: str,
        metrics_granularity: str,
        metrics_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch execution metrics for a script project."""
        validated_script_id = self._validate_script_id(script_id)
        request_params: dict[str, Any] = {
            "scriptId": validated_script_id,
            "metricsGranularity": metrics_granularity,
        }
        if metrics_filter:
            request_params["metricsFilter"] = metrics_filter
        return await asyncio.to_thread(self.service.projects().getMetrics(**request_params).execute)

    async def create_deployment(
        self,
        script_id: str,
        description: str,
        version_number: int,
    ) -> dict[str, Any]:
        """Create a deployment for a script project."""
        validated_script_id = self._validate_script_id(script_id)
        payload: dict[str, Any] = {"description": description, "manifestFileName": "appsscript"}
        payload["versionNumber"] = self._validate_version_number(version_number)
        return await asyncio.to_thread(
            self.service.projects().deployments().create(scriptId=validated_script_id, body=payload).execute
        )

    async def get_deployment(self, script_id: str, deployment_id: str) -> dict[str, Any]:
        """Get deployment metadata."""
        validated_script_id = self._validate_script_id(script_id)
        validated_deployment_id = self._validate_deployment_id(deployment_id)
        return await asyncio.to_thread(
            self.service.projects()
            .deployments()
            .get(scriptId=validated_script_id, deploymentId=validated_deployment_id)
            .execute
        )

    async def update_deployment(
        self,
        script_id: str,
        deployment_id: str,
        description: str,
        version_number: int | None = None,
    ) -> dict[str, Any]:
        """Update deployment configuration."""
        validated_script_id = self._validate_script_id(script_id)
        validated_deployment_id = self._validate_deployment_id(deployment_id)

        current = await self.get_deployment(validated_script_id, validated_deployment_id)
        current_config = current.get("deploymentConfig", {})
        deployment_config: dict[str, Any] = {
            "description": description,
            "manifestFileName": current_config.get("manifestFileName", "appsscript"),
        }
        deployment_config["versionNumber"] = (
            self._validate_version_number(version_number)
            if version_number is not None
            else self._validate_version_number(current_config.get("versionNumber", 1))
        )
        body = {"deploymentConfig": deployment_config}
        return await asyncio.to_thread(
            self.service.projects()
            .deployments()
            .update(
                scriptId=validated_script_id,
                deploymentId=validated_deployment_id,
                body=body,
            )
            .execute
        )

    async def delete_deployment(self, script_id: str, deployment_id: str) -> dict[str, Any]:
        """Delete a deployment."""
        validated_script_id = self._validate_script_id(script_id)
        validated_deployment_id = self._validate_deployment_id(deployment_id)
        return await asyncio.to_thread(
            self.service.projects()
            .deployments()
            .delete(scriptId=validated_script_id, deploymentId=validated_deployment_id)
            .execute
        )

    async def list_script_projects(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """
        List standalone Apps Script projects from Drive files.

        This endpoint is Drive-backed and only returns standalone script files
        (`application/vnd.google-apps.script`), not container-bound scripts.
        """
        validated_page_size = self._validate_page_size(page_size)
        query = f"mimeType='{SCRIPT_MIME_TYPE}' and trashed=false"
        request_params: dict[str, Any] = {
            "q": query,
            "pageSize": validated_page_size,
            "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, createdTime, webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if page_token:
            request_params["pageToken"] = page_token

        return await asyncio.to_thread(self.service.files().list(**request_params).execute)

    async def get_drive_script_metadata(self, script_id: str) -> dict[str, Any]:
        """
        Get Drive metadata for a standalone Apps Script file and enforce MIME type.
        """
        validated_script_id = self._validate_script_id(script_id)
        metadata = await asyncio.to_thread(
            self.service.files()
            .get(
                fileId=validated_script_id,
                fields="id, name, mimeType, webViewLink, trashed",
                supportsAllDrives=True,
            )
            .execute
        )
        if metadata.get("mimeType") != SCRIPT_MIME_TYPE:
            raise ValueError(
                "The provided script_id is not a standalone Apps Script Drive file. "
                "Container-bound scripts are not supported by this tool."
            )
        return metadata

    async def delete_script_project(
        self,
        script_id: str,
    ) -> dict[str, Any]:
        """
        Move a standalone Apps Script Drive file to trash.
        """
        validated_script_id = self._validate_script_id(script_id)
        return await asyncio.to_thread(
            self.service.files()
            .update(
                fileId=validated_script_id,
                body={"trashed": True},
                fields="id, name, trashed, webViewLink",
                supportsAllDrives=True,
            )
            .execute
        )
