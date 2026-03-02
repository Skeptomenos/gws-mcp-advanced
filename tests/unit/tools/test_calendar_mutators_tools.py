"""Unit tests for Calendar mutator dry-run behavior."""

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


def _load_calendar_tools_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gcalendar" / "calendar_tools.py"

    module_name = "_test_gcalendar_calendar_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def calendar_tools_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.errors",
        "core.server",
        "core.utils",
        "googleapiclient",
        "googleapiclient.discovery",
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

    class ValidationError(Exception):
        pass

    core_errors.APIError = APIError
    core_errors.ValidationError = ValidationError
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils.handle_http_errors = _identity_decorator

    googleapiclient_pkg = types.ModuleType("googleapiclient")
    googleapiclient_discovery = types.ModuleType("googleapiclient.discovery")
    googleapiclient_errors = types.ModuleType("googleapiclient.errors")
    googleapiclient_discovery.build = lambda *_args, **_kwargs: MagicMock()

    class HttpError(Exception):
        def __init__(self, status: int = 500):
            self.resp = types.SimpleNamespace(status=status)
            super().__init__(f"HTTP {status}")

    googleapiclient_errors.HttpError = HttpError

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.errors"] = core_errors
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["googleapiclient"] = googleapiclient_pkg
    sys.modules["googleapiclient.discovery"] = googleapiclient_discovery
    sys.modules["googleapiclient.errors"] = googleapiclient_errors

    try:
        yield _load_calendar_tools_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_event_dry_run_default_skips_mutation(calendar_tools_module):
    service = MagicMock()

    result = await calendar_tools_module.create_event(
        service=service,
        user_google_email="user@example.com",
        summary="Planning Sync",
        start_time="2026-03-01T09:00:00Z",
        end_time="2026-03-01T10:00:00Z",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create event 'Planning Sync'" in result
    assert service.events.call_count == 0


@pytest.mark.asyncio
async def test_create_event_dry_run_false_executes_insert(calendar_tools_module):
    service = MagicMock()
    service.events.return_value.insert.return_value.execute.return_value = {
        "id": "evt-123",
        "summary": "Planning Sync",
        "htmlLink": "https://calendar.google.com/event?eid=evt-123",
    }

    result = await calendar_tools_module.create_event(
        service=service,
        user_google_email="user@example.com",
        summary="Planning Sync",
        start_time="2026-03-01T09:00:00Z",
        end_time="2026-03-01T10:00:00Z",
        dry_run=False,
    )

    assert "Successfully created event 'Planning Sync'" in result
    service.events.return_value.insert.assert_called_once()
    insert_kwargs = service.events.return_value.insert.call_args.kwargs
    assert insert_kwargs["calendarId"] == "primary"
    assert insert_kwargs["conferenceDataVersion"] == 0


@pytest.mark.asyncio
async def test_modify_event_dry_run_default_skips_mutation(calendar_tools_module):
    service = MagicMock()

    result = await calendar_tools_module.modify_event(
        service=service,
        user_google_email="user@example.com",
        event_id="evt-123",
        summary="Updated Planning Sync",
    )

    assert result.startswith("DRY RUN:")
    assert "Would modify event 'evt-123'" in result
    assert service.events.call_count == 0


@pytest.mark.asyncio
async def test_modify_event_dry_run_false_executes_update(calendar_tools_module):
    service = MagicMock()
    service.events.return_value.get.return_value.execute.return_value = {
        "id": "evt-123",
        "summary": "Planning Sync",
    }
    service.events.return_value.update.return_value.execute.return_value = {
        "id": "evt-123",
        "summary": "Updated Planning Sync",
        "htmlLink": "https://calendar.google.com/event?eid=evt-123",
    }

    result = await calendar_tools_module.modify_event(
        service=service,
        user_google_email="user@example.com",
        event_id="evt-123",
        summary="Updated Planning Sync",
        dry_run=False,
    )

    assert "Successfully modified event 'Updated Planning Sync'" in result
    assert service.events.return_value.get.call_count == 1
    assert service.events.return_value.update.call_count == 1


@pytest.mark.asyncio
async def test_delete_event_dry_run_default_skips_mutation(calendar_tools_module):
    service = MagicMock()

    result = await calendar_tools_module.delete_event(
        service=service,
        user_google_email="user@example.com",
        event_id="evt-123",
    )

    assert result.startswith("DRY RUN:")
    assert "Would delete event 'evt-123'" in result
    assert service.events.call_count == 0


@pytest.mark.asyncio
async def test_delete_event_dry_run_false_executes_delete(calendar_tools_module):
    service = MagicMock()
    service.events.return_value.get.return_value.execute.return_value = {"id": "evt-123"}
    service.events.return_value.delete.return_value.execute.return_value = {}

    result = await calendar_tools_module.delete_event(
        service=service,
        user_google_email="user@example.com",
        event_id="evt-123",
        dry_run=False,
    )

    assert "Successfully deleted event (ID: evt-123)" in result
    assert service.events.return_value.get.call_count == 1
    assert service.events.return_value.delete.call_count == 1
