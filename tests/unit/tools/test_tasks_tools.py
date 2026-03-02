"""Unit tests for Google Tasks mutator dry-run behavior."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MISSING = object()


def _identity_decorator(*_args, **_kwargs):
    def decorator(func):
        return func

    return decorator


def _tool_decorator():
    def decorator(func):
        func.name = func.__name__
        func.fn = func
        return func

    return decorator


def _load_tasks_tools_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gtasks" / "tasks_tools.py"

    module_name = "_test_gtasks_tasks_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tasks_tools_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.errors",
        "core.server",
        "core.utils",
        "googleapiclient",
        "googleapiclient.errors",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_errors = types.ModuleType("core.errors")
    core_server = types.ModuleType("core.server")
    core_utils = types.ModuleType("core.utils")

    class APIError(Exception):
        pass

    core_errors.APIError = APIError
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils.handle_http_errors = _identity_decorator

    googleapiclient_pkg = types.ModuleType("googleapiclient")
    googleapiclient_errors = types.ModuleType("googleapiclient.errors")

    class HttpError(Exception):
        pass

    googleapiclient_errors.HttpError = HttpError

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.errors"] = core_errors
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["googleapiclient"] = googleapiclient_pkg
    sys.modules["googleapiclient.errors"] = googleapiclient_errors

    try:
        yield _load_tasks_tools_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_task_list_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.create_task_list(
        service=service,
        user_google_email="user@example.com",
        title="My Tasks",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create task list 'My Tasks'" in result
    assert service.tasklists.call_count == 0


@pytest.mark.asyncio
async def test_create_task_list_dry_run_false_calls_insert(tasks_tools_module):
    service = MagicMock()
    service.tasklists.return_value.insert.return_value.execute.return_value = {
        "id": "list-123",
        "title": "My Tasks",
        "updated": "2026-02-27T00:00:00Z",
    }

    result = await tasks_tools_module.create_task_list(
        service=service,
        user_google_email="user@example.com",
        title="My Tasks",
        dry_run=False,
    )

    assert "Task List Created for user@example.com" in result
    assert service.tasklists.return_value.insert.call_count == 1


@pytest.mark.asyncio
async def test_update_task_list_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.update_task_list(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        title="Updated Tasks",
    )

    assert result.startswith("DRY RUN:")
    assert "Would update task list list-123 title to 'Updated Tasks'" in result
    assert service.tasklists.call_count == 0


@pytest.mark.asyncio
async def test_update_task_list_dry_run_false_calls_update(tasks_tools_module):
    service = MagicMock()
    service.tasklists.return_value.update.return_value.execute.return_value = {
        "id": "list-123",
        "title": "Updated Tasks",
        "updated": "2026-02-27T00:00:00Z",
    }

    result = await tasks_tools_module.update_task_list(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        title="Updated Tasks",
        dry_run=False,
    )

    assert "Task List Updated for user@example.com" in result
    assert service.tasklists.return_value.update.call_count == 1


@pytest.mark.asyncio
async def test_delete_task_list_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.delete_task_list(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
    )

    assert result.startswith("DRY RUN:")
    assert "Would delete task list list-123" in result
    assert service.tasklists.call_count == 0


@pytest.mark.asyncio
async def test_delete_task_list_dry_run_false_calls_delete(tasks_tools_module):
    service = MagicMock()
    service.tasklists.return_value.delete.return_value.execute.return_value = {}

    result = await tasks_tools_module.delete_task_list(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        dry_run=False,
    )

    assert "Task list list-123 has been deleted" in result
    assert service.tasklists.return_value.delete.call_count == 1


@pytest.mark.asyncio
async def test_update_task_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.update_task(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        task_id="task-123",
        title="Updated Title",
    )

    assert result.startswith("DRY RUN:")
    assert "Would update task task-123 in list list-123" in result
    assert service.tasks.call_count == 0


@pytest.mark.asyncio
async def test_update_task_dry_run_false_calls_get_and_update(tasks_tools_module):
    service = MagicMock()
    service.tasks.return_value.get.return_value.execute.return_value = {
        "id": "task-123",
        "title": "Current Title",
        "status": "needsAction",
    }
    service.tasks.return_value.update.return_value.execute.return_value = {
        "id": "task-123",
        "title": "Updated Title",
        "status": "needsAction",
        "updated": "2026-02-28T00:00:00Z",
    }

    result = await tasks_tools_module.update_task(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        task_id="task-123",
        title="Updated Title",
        dry_run=False,
    )

    assert "Task Updated for user@example.com" in result
    assert service.tasks.return_value.get.call_count == 1
    assert service.tasks.return_value.update.call_count == 1


@pytest.mark.asyncio
async def test_delete_task_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.delete_task(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        task_id="task-123",
    )

    assert result.startswith("DRY RUN:")
    assert "Would delete task task-123 from task list list-123" in result
    assert service.tasks.call_count == 0


@pytest.mark.asyncio
async def test_delete_task_dry_run_false_calls_delete(tasks_tools_module):
    service = MagicMock()
    service.tasks.return_value.delete.return_value.execute.return_value = {}

    result = await tasks_tools_module.delete_task(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        task_id="task-123",
        dry_run=False,
    )

    assert "Task task-123 has been deleted from task list list-123" in result
    assert service.tasks.return_value.delete.call_count == 1


@pytest.mark.asyncio
async def test_move_task_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.move_task(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        task_id="task-123",
        destination_task_list="list-456",
    )

    assert result.startswith("DRY RUN:")
    assert "destination_task_list=list-456" in result
    assert service.tasks.call_count == 0


@pytest.mark.asyncio
async def test_move_task_dry_run_false_calls_move(tasks_tools_module):
    service = MagicMock()
    service.tasks.return_value.move.return_value.execute.return_value = {
        "id": "task-123",
        "title": "Task",
        "status": "needsAction",
        "updated": "2026-02-28T00:00:00Z",
    }

    result = await tasks_tools_module.move_task(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        task_id="task-123",
        destination_task_list="list-456",
        dry_run=False,
    )

    assert "Task Moved for user@example.com" in result
    assert service.tasks.return_value.move.call_count == 1


@pytest.mark.asyncio
async def test_clear_completed_tasks_dry_run_default_skips_mutation(tasks_tools_module):
    service = MagicMock()

    result = await tasks_tools_module.clear_completed_tasks(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
    )

    assert result.startswith("DRY RUN:")
    assert "Would clear completed tasks from task list list-123" in result
    assert service.tasks.call_count == 0


@pytest.mark.asyncio
async def test_clear_completed_tasks_dry_run_false_calls_clear(tasks_tools_module):
    service = MagicMock()
    service.tasks.return_value.clear.return_value.execute.return_value = {}

    result = await tasks_tools_module.clear_completed_tasks(
        service=service,
        user_google_email="user@example.com",
        task_list_id="list-123",
        dry_run=False,
    )

    assert "All completed tasks have been cleared from task list list-123" in result
    assert service.tasks.return_value.clear.call_count == 1
