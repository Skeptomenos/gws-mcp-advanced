"""
Unit tests for Apps Script manager and tool behavior.
"""

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError
from httplib2 import Response

from gappsscript.apps_script_manager import AppsScriptManager


def _get_innermost_tool_function(tool_name: str):
    from gappsscript import apps_script_tools

    function = getattr(apps_script_tools, tool_name).fn
    while hasattr(function, "__wrapped__"):
        function = function.__wrapped__
    return function


class TestAppsScriptManager:
    """Tests for manager-layer validation and API orchestration."""

    @pytest.mark.asyncio
    async def test_get_script_project_returns_validated_model(self):
        service = MagicMock()
        service.projects.return_value.get.return_value.execute.return_value = {
            "scriptId": "abc123",
            "title": "My Script",
            "parentId": "parent123",
            "createTime": "2026-03-01T12:00:00Z",
            "updateTime": "2026-03-02T12:00:00Z",
        }

        manager = AppsScriptManager(service)
        project = await manager.get_script_project("  abc123  ")

        service.projects.return_value.get.assert_called_once_with(scriptId="abc123")
        assert project.script_id == "abc123"
        assert project.title == "My Script"
        assert project.parent_id == "parent123"

    def test_validate_script_id_rejects_empty(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            AppsScriptManager._validate_script_id("   ")

    def test_validate_script_id_rejects_invalid_characters(self):
        with pytest.raises(ValueError, match="invalid characters"):
            AppsScriptManager._validate_script_id("bad/script/id")

    def test_validate_page_size_rejects_out_of_range(self):
        with pytest.raises(ValueError, match=">= 1"):
            AppsScriptManager._validate_page_size(0)
        with pytest.raises(ValueError, match="cannot exceed"):
            AppsScriptManager._validate_page_size(1001)

    @pytest.mark.asyncio
    async def test_list_script_projects_builds_drive_query(self):
        service = MagicMock()
        service.files.return_value.list.return_value.execute.return_value = {"files": []}
        manager = AppsScriptManager(service)

        await manager.list_script_projects(page_size=25, page_token="token123")

        service.files.return_value.list.assert_called_once()
        kwargs = service.files.return_value.list.call_args.kwargs
        assert kwargs["q"] == "mimeType='application/vnd.google-apps.script' and trashed=false"
        assert kwargs["pageSize"] == 25
        assert kwargs["pageToken"] == "token123"
        assert kwargs["supportsAllDrives"] is True
        assert kwargs["includeItemsFromAllDrives"] is True

    @pytest.mark.asyncio
    async def test_get_drive_script_metadata_rejects_non_script_files(self):
        service = MagicMock()
        service.files.return_value.get.return_value.execute.return_value = {
            "id": "abc123",
            "name": "Not Script",
            "mimeType": "application/pdf",
        }
        manager = AppsScriptManager(service)

        with pytest.raises(ValueError, match="not a standalone Apps Script Drive file"):
            await manager.get_drive_script_metadata("abc123")

    @pytest.mark.asyncio
    async def test_get_script_content_passes_optional_version(self):
        service = MagicMock()
        service.projects.return_value.getContent.return_value.execute.return_value = {"scriptId": "abc123", "files": []}
        manager = AppsScriptManager(service)

        await manager.get_script_content("abc123", version_number=7)

        service.projects.return_value.getContent.assert_called_once_with(scriptId="abc123", versionNumber=7)

    @pytest.mark.asyncio
    async def test_list_deployments_and_versions_pass_pagination(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.list.return_value.execute.return_value = {
            "deployments": []
        }
        service.projects.return_value.versions.return_value.list.return_value.execute.return_value = {"versions": []}
        manager = AppsScriptManager(service)

        await manager.list_deployments("abc123", page_size=10, page_token="dep-token")
        await manager.list_versions("abc123", page_size=20, page_token="ver-token")

        service.projects.return_value.deployments.return_value.list.assert_called_once_with(
            scriptId="abc123",
            pageSize=10,
            pageToken="dep-token",
        )
        service.projects.return_value.versions.return_value.list.assert_called_once_with(
            scriptId="abc123",
            pageSize=20,
            pageToken="ver-token",
        )

    @pytest.mark.asyncio
    async def test_get_version_uses_validated_version_number(self):
        service = MagicMock()
        service.projects.return_value.versions.return_value.get.return_value.execute.return_value = {"versionNumber": 3}
        manager = AppsScriptManager(service)

        await manager.get_version("abc123", version_number=3)

        service.projects.return_value.versions.return_value.get.assert_called_once_with(
            scriptId="abc123",
            versionNumber=3,
        )

    @pytest.mark.asyncio
    async def test_list_script_processes_uses_script_specific_api_path(self):
        service = MagicMock()
        service.processes.return_value.listScriptProcesses.return_value.execute.return_value = {"processes": []}
        manager = AppsScriptManager(service)

        await manager.list_script_processes(
            script_id="abc123",
            script_process_filter={"deploymentId": "dep1"},
            page_size=25,
            page_token="tok",
        )

        service.processes.return_value.listScriptProcesses.assert_called_once_with(
            scriptId="abc123",
            scriptProcessFilter_deploymentId="dep1",
            pageSize=25,
            pageToken="tok",
        )
        service.processes.return_value.list.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_script_processes_uses_user_api_path_without_script_id(self):
        service = MagicMock()
        service.processes.return_value.list.return_value.execute.return_value = {"processes": []}
        manager = AppsScriptManager(service)

        await manager.list_script_processes(
            script_id=None,
            user_process_filter={"scriptId": "abc123"},
            page_size=10,
            page_token="tok",
        )

        service.processes.return_value.list.assert_called_once_with(
            userProcessFilter_scriptId="abc123",
            pageSize=10,
            pageToken="tok",
        )
        service.processes.return_value.listScriptProcesses.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_script_processes_maps_repeated_and_access_level_filters(self):
        service = MagicMock()
        service.processes.return_value.listScriptProcesses.return_value.execute.return_value = {"processes": []}
        manager = AppsScriptManager(service)

        await manager.list_script_processes(
            script_id="abc123",
            script_process_filter={
                "statuses": ["COMPLETED", "FAILED"],
                "types": ["TRIGGER"],
                "userAccessLevels": ["OWNER"],
            },
            page_size=5,
        )

        service.processes.return_value.listScriptProcesses.assert_called_once_with(
            scriptId="abc123",
            pageSize=5,
            scriptProcessFilter_statuses=["COMPLETED", "FAILED"],
            scriptProcessFilter_types=["TRIGGER"],
            scriptProcessFilter_userAccessLevels=["OWNER"],
        )

    @pytest.mark.asyncio
    async def test_list_script_processes_rejects_script_filter_without_script_id(self):
        service = MagicMock()
        manager = AppsScriptManager(service)

        with pytest.raises(ValueError, match="requires script_id"):
            await manager.list_script_processes(script_process_filter={"deploymentId": "dep1"})

    @pytest.mark.asyncio
    async def test_get_script_metrics_passes_filter_and_granularity(self):
        service = MagicMock()
        service.projects.return_value.getMetrics.return_value.execute.return_value = {"metrics": []}
        manager = AppsScriptManager(service)

        await manager.get_script_metrics(
            script_id="abc123",
            metrics_granularity="DAILY",
            metrics_filter={"deploymentId": "dep1"},
        )

        service.projects.return_value.getMetrics.assert_called_once_with(
            scriptId="abc123",
            metricsGranularity="DAILY",
            metricsFilter={"deploymentId": "dep1"},
        )

    @pytest.mark.asyncio
    async def test_create_script_project_calls_projects_create(self):
        service = MagicMock()
        service.projects.return_value.create.return_value.execute.return_value = {"scriptId": "script1"}
        manager = AppsScriptManager(service)

        await manager.create_script_project(title="New Script", parent_id="parent1")

        service.projects.return_value.create.assert_called_once_with(
            body={"title": "New Script", "parentId": "parent1"},
        )

    @pytest.mark.asyncio
    async def test_update_script_content_calls_update_content(self):
        service = MagicMock()
        service.projects.return_value.updateContent.return_value.execute.return_value = {
            "scriptId": "script1",
            "files": [],
        }
        manager = AppsScriptManager(service)

        await manager.update_script_content(
            script_id="script1",
            files=[{"name": "appsscript", "type": "JSON", "source": "{}"}],
        )

        service.projects.return_value.updateContent.assert_called_once_with(
            scriptId="script1",
            body={"files": [{"name": "appsscript", "type": "JSON", "source": "{}"}]},
        )

    @pytest.mark.asyncio
    async def test_create_version_calls_versions_create(self):
        service = MagicMock()
        service.projects.return_value.versions.return_value.create.return_value.execute.return_value = {
            "versionNumber": 2
        }
        manager = AppsScriptManager(service)

        await manager.create_version(script_id="script1", description="Stable")

        service.projects.return_value.versions.return_value.create.assert_called_once_with(
            scriptId="script1",
            body={"description": "Stable"},
        )

    @pytest.mark.asyncio
    async def test_run_script_function_calls_scripts_run(self):
        service = MagicMock()
        service.scripts.return_value.run.return_value.execute.return_value = {"response": {"result": "ok"}}
        manager = AppsScriptManager(service)

        await manager.run_script_function(
            script_id="script1",
            function_name="syncNow",
            parameters=["alpha"],
            dev_mode=True,
        )

        service.scripts.return_value.run.assert_called_once_with(
            scriptId="script1",
            body={"function": "syncNow", "parameters": ["alpha"], "devMode": True},
        )

    @pytest.mark.asyncio
    async def test_create_deployment_uses_flat_payload_fields(self):
        service = MagicMock()
        deployments = service.projects.return_value.deployments.return_value
        deployments.create.return_value.execute.return_value = {"deploymentId": "dep1"}
        manager = AppsScriptManager(service)

        await manager.create_deployment(
            script_id="script1",
            description="Prod",
            version_number=7,
        )

        deployments.create.assert_called_once_with(
            scriptId="script1",
            body={
                "description": "Prod",
                "manifestFileName": "appsscript",
                "versionNumber": 7,
            },
        )

    @pytest.mark.asyncio
    async def test_update_deployment_preserves_manifest_file_name(self):
        service = MagicMock()
        deployments = service.projects.return_value.deployments.return_value
        deployments.get.return_value.execute.return_value = {
            "deploymentId": "dep1",
            "deploymentConfig": {
                "description": "Old",
                "versionNumber": 3,
                "manifestFileName": "appsscript",
            },
        }
        deployments.update.return_value.execute.return_value = {"deploymentId": "dep1"}
        manager = AppsScriptManager(service)

        await manager.update_deployment(
            script_id="script1",
            deployment_id="dep1",
            description="New",
        )

        deployments.update.assert_called_once_with(
            scriptId="script1",
            deploymentId="dep1",
            body={
                "deploymentConfig": {
                    "description": "New",
                    "manifestFileName": "appsscript",
                    "versionNumber": 3,
                }
            },
        )


class TestGetScriptProjectTool:
    """Tests for tool-level formatting and registration."""

    @pytest.mark.asyncio
    async def test_get_script_project_formats_response(self):
        service = MagicMock()
        service.projects.return_value.get.return_value.execute.return_value = {
            "scriptId": "abc123",
            "title": "My Script",
            "parentId": "parent123",
            "createTime": "2026-03-01T12:00:00Z",
            "updateTime": "2026-03-02T12:00:00Z",
        }

        get_script_project = _get_innermost_tool_function("get_script_project")
        result = await get_script_project(service, "david@example.com", "abc123")

        assert "Apps Script Project:" in result
        assert "Script ID: abc123" in result
        assert "Title: My Script" in result
        assert "Parent ID: parent123" in result

    def test_tool_is_registered(self):
        from gappsscript import get_script_project

        assert hasattr(get_script_project, "name")
        assert get_script_project.name == "get_script_project"


class TestListScriptProjectsTool:
    """Tests for Drive-backed standalone script listing."""

    @pytest.mark.asyncio
    async def test_list_script_projects_formats_results_and_limitation(self):
        service = MagicMock()
        service.files.return_value.list.return_value.execute.return_value = {
            "files": [
                {
                    "id": "script1",
                    "name": "Standalone Script",
                    "modifiedTime": "2026-03-03T12:00:00Z",
                    "webViewLink": "https://example.com/script1",
                }
            ],
            "nextPageToken": "next123",
        }

        list_script_projects = _get_innermost_tool_function("list_script_projects")
        result = await list_script_projects(service, "david@example.com", page_size=10, page_token=None)

        assert "Found 1 standalone Apps Script project(s)" in result
        assert "Standalone Script" in result
        assert "container-bound scripts are not included" in result
        assert "Next Page Token: next123" in result


class TestDeleteScriptProjectTool:
    """Tests for Drive-backed standalone script deletion."""

    @pytest.mark.asyncio
    async def test_delete_script_project_dry_run_skips_mutation(self):
        service = MagicMock()
        service.files.return_value.get.return_value.execute.return_value = {
            "id": "script1",
            "name": "Standalone Script",
            "mimeType": "application/vnd.google-apps.script",
            "webViewLink": "https://example.com/script1",
        }

        delete_script_project = _get_innermost_tool_function("delete_script_project")
        result = await delete_script_project(service, "david@example.com", "script1", dry_run=True)

        assert result.startswith("DRY RUN:")
        assert "Standalone Script" in result
        assert "container-bound scripts are excluded" in result
        service.files.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_script_project_executes_mutation_when_explicit(self):
        service = MagicMock()
        service.files.return_value.get.return_value.execute.return_value = {
            "id": "script1",
            "name": "Standalone Script",
            "mimeType": "application/vnd.google-apps.script",
            "webViewLink": "https://example.com/script1",
        }
        service.files.return_value.update.return_value.execute.return_value = {
            "id": "script1",
            "name": "Standalone Script",
            "trashed": True,
            "webViewLink": "https://example.com/script1",
        }

        delete_script_project = _get_innermost_tool_function("delete_script_project")
        result = await delete_script_project(service, "david@example.com", "script1", dry_run=False)

        assert "Successfully moved standalone Apps Script project to trash." in result
        assert "- Trashed: True" in result
        service.files.return_value.update.assert_called_once()


class TestAppsScriptReadSurfaceTools:
    """Tests for APPS-03 read-surface tools and filter contracts."""

    @pytest.mark.asyncio
    async def test_get_script_content_formats_files_and_version(self):
        service = MagicMock()
        service.projects.return_value.getContent.return_value.execute.return_value = {
            "scriptId": "abc123",
            "scriptVersion": {"versionNumber": 4},
            "files": [
                {"name": "Code", "type": "SERVER_JS", "source": "function run() {}"},
                {"name": "appsscript", "type": "JSON", "source": '{"timeZone":"UTC"}'},
            ],
        }

        get_script_content = _get_innermost_tool_function("get_script_content")
        result = await get_script_content(service, "david@example.com", "abc123", version_number=4)

        assert "Apps Script Content:" in result
        assert "- Script ID: abc123" in result
        assert "- Version: 4" in result
        assert "File: Code (type: SERVER_JS)" in result
        assert "function run() {}" in result

    @pytest.mark.asyncio
    async def test_list_deployments_formats_entries(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.list.return_value.execute.return_value = {
            "deployments": [
                {
                    "deploymentId": "dep1",
                    "updateTime": "2026-03-03T10:00:00Z",
                    "deploymentConfig": {"description": "Production", "versionNumber": 7},
                }
            ],
            "nextPageToken": "next-dep",
        }

        list_deployments = _get_innermost_tool_function("list_deployments")
        result = await list_deployments(service, "david@example.com", "abc123")

        assert "Found 1 deployment(s)" in result
        assert "Deployment ID: dep1" in result
        assert "Version: 7" in result
        assert "Next Page Token: next-dep" in result

    @pytest.mark.asyncio
    async def test_list_versions_and_get_version_format_entries(self):
        service = MagicMock()
        service.projects.return_value.versions.return_value.list.return_value.execute.return_value = {
            "versions": [{"versionNumber": 2, "description": "Stable", "createTime": "2026-03-01T10:00:00Z"}],
            "nextPageToken": "next-ver",
        }
        service.projects.return_value.versions.return_value.get.return_value.execute.return_value = {
            "versionNumber": 2,
            "description": "Stable",
            "createTime": "2026-03-01T10:00:00Z",
        }

        list_versions = _get_innermost_tool_function("list_versions")
        get_version = _get_innermost_tool_function("get_version")
        list_result = await list_versions(service, "david@example.com", "abc123")
        version_result = await get_version(service, "david@example.com", "abc123", 2)

        assert "Found 1 version(s)" in list_result
        assert "Version: 2" in list_result
        assert "Next Page Token: next-ver" in list_result
        assert "Apps Script Version:" in version_result
        assert "- Version Number: 2" in version_result

    @pytest.mark.asyncio
    async def test_list_script_processes_with_script_filter(self):
        service = MagicMock()
        service.processes.return_value.listScriptProcesses.return_value.execute.return_value = {
            "processes": [
                {
                    "processId": "proc1",
                    "functionName": "runJob",
                    "processType": "TIME_DRIVEN",
                    "processStatus": "COMPLETED",
                    "startTime": "2026-03-01T00:00:00Z",
                }
            ]
        }

        list_script_processes = _get_innermost_tool_function("list_script_processes")
        result = await list_script_processes(
            service,
            "david@example.com",
            script_id="abc123",
            script_process_filter_json='{"deploymentId":"dep1","statuses":["COMPLETED"]}',
        )

        assert "Found 1 process(es)" in result
        assert "Process ID: proc1" in result
        assert "Status: COMPLETED" in result
        service.processes.return_value.listScriptProcesses.assert_called_once_with(
            scriptId="abc123",
            pageSize=50,
            scriptProcessFilter_deploymentId="dep1",
            scriptProcessFilter_statuses=["COMPLETED"],
        )

    @pytest.mark.asyncio
    async def test_list_script_processes_rejects_invalid_filter_payload(self):
        service = MagicMock()
        list_script_processes = _get_innermost_tool_function("list_script_processes")

        with pytest.raises(ValueError, match="must be valid JSON"):
            await list_script_processes(
                service,
                "david@example.com",
                script_id="abc123",
                script_process_filter_json="{not-json}",
            )

        with pytest.raises(ValueError, match="Invalid script_process_filter_json"):
            await list_script_processes(
                service,
                "david@example.com",
                script_id="abc123",
                script_process_filter_json='{"statuses":["NOT_A_STATUS"]}',
            )

        with pytest.raises(ValueError, match="requires script_id"):
            await list_script_processes(
                service,
                "david@example.com",
                script_process_filter_json='{"deploymentId":"dep1"}',
            )

    @pytest.mark.asyncio
    async def test_get_script_metrics_formats_response_and_validates_granularity(self):
        service = MagicMock()
        service.projects.return_value.getMetrics.return_value.execute.return_value = {"totalExecutions": 5}
        get_script_metrics = _get_innermost_tool_function("get_script_metrics")

        result = await get_script_metrics(
            service,
            "david@example.com",
            script_id="abc123",
            metrics_granularity="WEEKLY",
            metrics_filter_json='{"deploymentId":"dep1"}',
        )
        assert "Apps Script Metrics:" in result
        assert "- Granularity: WEEKLY" in result
        assert '"totalExecutions": 5' in result

        with pytest.raises(ValueError, match="Invalid metrics_filter_json"):
            await get_script_metrics(
                service,
                "david@example.com",
                script_id="abc123",
                metrics_granularity="DAILY",
                metrics_filter_json='{"unknown":"value"}',
            )

        with pytest.raises(ValueError, match="MetricsGranularity"):
            await get_script_metrics(
                service,
                "david@example.com",
                script_id="abc123",
                metrics_granularity="MONTHLY",
            )


class TestAppsScriptMutatingTools:
    """Tests for APPS-04 mutating tools and dry-run safety behavior."""

    @pytest.mark.asyncio
    async def test_create_script_project_dry_run_default_skips_mutation(self):
        service = MagicMock()
        create_script_project = _get_innermost_tool_function("create_script_project")

        result = await create_script_project(
            service,
            "david@example.com",
            title="My Script",
        )

        assert result.startswith("DRY RUN:")
        assert "Title: My Script" in result
        service.projects.return_value.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_script_project_executes_when_dry_run_false(self):
        service = MagicMock()
        service.projects.return_value.create.return_value.execute.return_value = {
            "scriptId": "script123",
            "title": "My Script",
            "parentId": "parent123",
        }
        create_script_project = _get_innermost_tool_function("create_script_project")

        result = await create_script_project(
            service,
            "david@example.com",
            title="My Script",
            parent_id="parent123",
            dry_run=False,
        )

        assert "Successfully created Apps Script project." in result
        assert "- Script ID: script123" in result
        service.projects.return_value.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_script_content_dry_run_default_skips_mutation(self):
        service = MagicMock()
        update_script_content = _get_innermost_tool_function("update_script_content")

        result = await update_script_content(
            service,
            "david@example.com",
            script_id="script123",
            files_json='[{"name":"appsscript","type":"JSON","source":"{}"},{"name":"Code","type":"SERVER_JS","source":"function run(){}"}]',
        )

        assert result.startswith("DRY RUN:")
        assert "- Files: 2" in result
        service.projects.return_value.updateContent.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_script_content_rejects_missing_manifest(self):
        service = MagicMock()
        update_script_content = _get_innermost_tool_function("update_script_content")

        with pytest.raises(ValueError, match="manifest file"):
            await update_script_content(
                service,
                "david@example.com",
                script_id="script123",
                files_json='[{"name":"Code","type":"SERVER_JS","source":"function run(){}"}]',
            )

    @pytest.mark.asyncio
    async def test_update_script_content_executes_when_dry_run_false(self):
        service = MagicMock()
        service.projects.return_value.updateContent.return_value.execute.return_value = {
            "scriptId": "script123",
            "files": [
                {"name": "appsscript", "type": "JSON", "source": "{}"},
                {"name": "Code", "type": "SERVER_JS", "source": "function run(){}"},
            ],
        }
        update_script_content = _get_innermost_tool_function("update_script_content")

        result = await update_script_content(
            service,
            "david@example.com",
            script_id="script123",
            files_json='[{"name":"appsscript","type":"JSON","source":"{}"},{"name":"Code","type":"SERVER_JS","source":"function run(){}"}]',
            dry_run=False,
        )

        assert "Successfully updated Apps Script content." in result
        service.projects.return_value.updateContent.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_script_content_accepts_get_content_style_file_metadata(self):
        service = MagicMock()
        service.projects.return_value.updateContent.return_value.execute.return_value = {
            "scriptId": "script123",
            "files": [
                {"name": "appsscript", "type": "JSON", "source": "{}"},
                {"name": "Code", "type": "SERVER_JS", "source": "function run(){}"},
            ],
        }
        update_script_content = _get_innermost_tool_function("update_script_content")

        result = await update_script_content(
            service,
            "david@example.com",
            script_id="script123",
            files_json='[{"name":"appsscript","type":"JSON","source":"{}","createTime":"2026-03-03T00:00:00Z"},{"name":"Code","type":"SERVER_JS","source":"function run(){}","lastModifyUser":{"email":"x@example.com"}}]',
            dry_run=False,
        )

        assert "Successfully updated Apps Script content." in result
        service.projects.return_value.updateContent.assert_called_once_with(
            scriptId="script123",
            body={
                "files": [
                    {"name": "appsscript", "type": "JSON", "source": "{}"},
                    {"name": "Code", "type": "SERVER_JS", "source": "function run(){}"},
                ]
            },
        )

    @pytest.mark.asyncio
    async def test_create_version_dry_run_default_skips_mutation(self):
        service = MagicMock()
        create_version = _get_innermost_tool_function("create_version")

        result = await create_version(service, "david@example.com", script_id="script123")

        assert result.startswith("DRY RUN:")
        service.projects.return_value.versions.return_value.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_version_executes_when_dry_run_false(self):
        service = MagicMock()
        service.projects.return_value.versions.return_value.create.return_value.execute.return_value = {
            "versionNumber": 4,
            "description": "Stable",
            "createTime": "2026-03-03T10:00:00Z",
        }
        create_version = _get_innermost_tool_function("create_version")

        result = await create_version(
            service,
            "david@example.com",
            script_id="script123",
            description="Stable",
            dry_run=False,
        )

        assert "Successfully created Apps Script version." in result
        assert "- Version Number: 4" in result
        service.projects.return_value.versions.return_value.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_deployment_dry_run_default_skips_mutation(self):
        service = MagicMock()
        create_deployment = _get_innermost_tool_function("create_deployment")

        result = await create_deployment(
            service,
            "david@example.com",
            script_id="script123",
            description="Prod",
            version_number=7,
        )

        assert result.startswith("DRY RUN:")
        service.projects.return_value.deployments.return_value.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_deployment_executes_when_dry_run_false(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.create.return_value.execute.return_value = {
            "deploymentId": "dep1",
            "deploymentConfig": {"versionNumber": 7, "description": "Prod"},
        }
        create_deployment = _get_innermost_tool_function("create_deployment")

        result = await create_deployment(
            service,
            "david@example.com",
            script_id="script123",
            description="Prod",
            version_number=7,
            dry_run=False,
        )

        assert "Successfully created Apps Script deployment." in result
        assert "- Deployment ID: dep1" in result
        service.projects.return_value.deployments.return_value.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_deployment_dry_run_default_skips_mutation(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.get.return_value.execute.return_value = {
            "deploymentConfig": {"description": "Old", "versionNumber": 3},
        }
        update_deployment = _get_innermost_tool_function("update_deployment")

        result = await update_deployment(
            service,
            "david@example.com",
            script_id="script123",
            deployment_id="dep1",
            description="New",
        )

        assert result.startswith("DRY RUN:")
        assert "Current Description: Old" in result
        service.projects.return_value.deployments.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_deployment_executes_when_dry_run_false(self):
        service = MagicMock()
        deployments = service.projects.return_value.deployments.return_value
        deployments.get.return_value.execute.return_value = {
            "deploymentConfig": {
                "description": "Old",
                "versionNumber": 3,
                "manifestFileName": "appsscript",
            }
        }
        deployments.update.return_value.execute.return_value = {
            "deploymentId": "dep1",
            "deploymentConfig": {"description": "New", "versionNumber": 3},
        }
        update_deployment = _get_innermost_tool_function("update_deployment")

        result = await update_deployment(
            service,
            "david@example.com",
            script_id="script123",
            deployment_id="dep1",
            description="New",
            dry_run=False,
        )

        assert "Successfully updated Apps Script deployment." in result
        deployments.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_deployment_dry_run_default_skips_mutation(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.get.return_value.execute.return_value = {
            "deploymentConfig": {"description": "Prod"},
        }
        delete_deployment = _get_innermost_tool_function("delete_deployment")

        result = await delete_deployment(
            service,
            "david@example.com",
            script_id="script123",
            deployment_id="dep1",
        )

        assert result.startswith("DRY RUN:")
        assert "Deployment ID: dep1" in result
        service.projects.return_value.deployments.return_value.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_deployment_executes_when_dry_run_false(self):
        service = MagicMock()
        deployments = service.projects.return_value.deployments.return_value
        deployments.get.return_value.execute.return_value = {"deploymentConfig": {"description": "Prod"}}
        deployments.delete.return_value.execute.return_value = {}
        delete_deployment = _get_innermost_tool_function("delete_deployment")

        result = await delete_deployment(
            service,
            "david@example.com",
            script_id="script123",
            deployment_id="dep1",
            dry_run=False,
        )

        assert "Successfully deleted Apps Script deployment." in result
        deployments.delete.assert_called_once_with(scriptId="script123", deploymentId="dep1")

    @pytest.mark.asyncio
    async def test_run_script_function_dry_run_default_skips_mutation(self):
        service = MagicMock()
        run_script_function = _get_innermost_tool_function("run_script_function")

        result = await run_script_function(
            service,
            "david@example.com",
            script_id="script123",
            function_name="runJob",
            parameters_json='["alpha", 2]',
        )

        assert result.startswith("DRY RUN:")
        assert "- Parameters: 2" in result
        service.scripts.return_value.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_script_function_executes_when_dry_run_false(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.list.return_value.execute.return_value = {
            "deployments": [
                {
                    "deploymentId": "dep-exec-1",
                    "updateTime": "2026-03-03T10:00:00Z",
                    "entryPoints": [{"entryPointType": "EXECUTION_API"}],
                }
            ]
        }
        service.scripts.return_value.run.return_value.execute.return_value = {"response": {"result": "ok"}}
        run_script_function = _get_innermost_tool_function("run_script_function")

        result = await run_script_function(
            service,
            "david@example.com",
            script_id="script123",
            function_name="runJob",
            parameters_json='["alpha"]',
            dry_run=False,
        )

        assert "Apps Script execution succeeded." in result
        service.scripts.return_value.run.assert_called_once_with(
            scriptId="dep-exec-1",
            body={"function": "runJob", "parameters": ["alpha"], "devMode": False},
        )

    @pytest.mark.asyncio
    async def test_run_script_function_surfaces_execution_error_payload(self):
        service = MagicMock()
        service.scripts.return_value.run.return_value.execute.return_value = {
            "error": {"message": "Execution failed", "details": [{"errorType": "TypeError"}]}
        }
        run_script_function = _get_innermost_tool_function("run_script_function")

        result = await run_script_function(
            service,
            "david@example.com",
            script_id="script123",
            function_name="runJob",
            dry_run=False,
        )

        assert "Apps Script execution failed." in result
        assert "Execution failed" in result

    @pytest.mark.asyncio
    async def test_run_script_function_rejects_non_list_parameters_json(self):
        service = MagicMock()
        run_script_function = _get_innermost_tool_function("run_script_function")

        with pytest.raises(ValueError, match="parameters_json must be a JSON list"):
            await run_script_function(
                service,
                "david@example.com",
                script_id="script123",
                function_name="runJob",
                parameters_json='{"bad":"payload"}',
            )

    @pytest.mark.asyncio
    async def test_run_script_function_surfaces_precondition_guidance_for_404(self):
        service = MagicMock()
        service.projects.return_value.getContent.return_value.execute.return_value = {
            "files": [
                {
                    "name": "appsscript",
                    "type": "JSON",
                    "source": '{"executionApi":{"access":"MYSELF"}}',
                }
            ]
        }
        service.scripts.return_value.run.return_value.execute.side_effect = HttpError(
            Response({"status": "404"}),
            b'{"error":{"message":"Requested entity was not found."}}',
        )
        run_script_function = _get_innermost_tool_function("run_script_function")

        result = await run_script_function(
            service,
            "david@example.com",
            script_id="script123",
            function_name="runJob",
            dry_run=False,
            dev_mode=True,
        )

        assert "Apps Script execution failed (precondition)." in result
        assert "- HTTP Status: 404" in result
        assert "- Manifest executionApi.access: MYSELF" in result
        assert "Next Steps:" in result

    @pytest.mark.asyncio
    async def test_run_script_function_falls_back_to_script_id_without_execution_deployment(self):
        service = MagicMock()
        service.projects.return_value.deployments.return_value.list.return_value.execute.return_value = {
            "deployments": []
        }
        service.scripts.return_value.run.return_value.execute.return_value = {"response": {"result": "ok"}}
        run_script_function = _get_innermost_tool_function("run_script_function")

        result = await run_script_function(
            service,
            "david@example.com",
            script_id="script123",
            function_name="runJob",
            dry_run=False,
            dev_mode=False,
        )

        assert "Apps Script execution succeeded." in result
        service.scripts.return_value.run.assert_called_once_with(
            scriptId="script123",
            body={"function": "runJob", "devMode": False},
        )
