"""Tests for scripts/mcp_live_cleanup.py."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _load_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "mcp_live_cleanup.py"
    spec = importlib.util.spec_from_file_location("mcp_live_cleanup", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Executable:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _DriveFilesAPI:
    def __init__(self, items):
        self._items = items
        self.deleted: list[tuple[str, bool]] = []
        self.list_calls: list[dict] = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return _Executable({"files": self._items})

    def delete(self, *, fileId: str, supportsAllDrives: bool = True):
        self.deleted.append((fileId, supportsAllDrives))
        return _Executable({})


class _DriveService:
    def __init__(self, items):
        self._api = _DriveFilesAPI(items)

    def files(self):
        return self._api


class _CalendarEventsAPI:
    def __init__(self, items):
        self._items = items
        self.deleted: list[tuple[str, str]] = []

    def list(self, **_kwargs):
        return _Executable({"items": self._items})

    def delete(self, *, calendarId: str, eventId: str):
        self.deleted.append((calendarId, eventId))
        return _Executable({})


class _CalendarService:
    def __init__(self, items):
        self._api = _CalendarEventsAPI(items)

    def events(self):
        return self._api


class _TasklistsAPI:
    def __init__(self, items):
        self._items = items
        self.deleted: list[str] = []

    def list(self, **_kwargs):
        return _Executable({"items": self._items})

    def delete(self, *, tasklist: str):
        self.deleted.append(tasklist)
        return _Executable({})


class _TasksService:
    def __init__(self, items):
        self._api = _TasklistsAPI(items)

    def tasklists(self):
        return self._api


def _to_rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_parse_services_supports_all_alias():
    module = _load_module()
    assert module._parse_services("all") == {"drive", "calendar", "tasks"}


def test_parse_services_rejects_invalid_entry():
    module = _load_module()
    with pytest.raises(ValueError, match="Unsupported services"):
        module._parse_services("drive,unknown")


def test_parse_rfc3339_handles_z_suffix():
    module = _load_module()
    parsed = module._parse_rfc3339("2026-03-05T12:34:56Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_cleanup_drive_files_filters_prefix_and_cutoff():
    module = _load_module()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    older = _to_rfc3339(cutoff - timedelta(hours=1))
    newer = _to_rfc3339(cutoff + timedelta(hours=1))
    service = _DriveService(
        [
            {"id": "1", "name": "codex-it-old", "modifiedTime": older},
            {"id": "2", "name": "codex-it-new", "modifiedTime": newer},
            {"id": "3", "name": "other-old", "modifiedTime": older},
        ]
    )

    stats_dry = module.cleanup_drive_files(service, prefix="codex-it-", cutoff=cutoff, execute=False, max_items=100)
    assert stats_dry.scanned == 3
    assert stats_dry.matched == 1
    assert stats_dry.deleted == 0

    stats_exec = module.cleanup_drive_files(service, prefix="codex-it-", cutoff=cutoff, execute=True, max_items=100)
    assert stats_exec.matched == 1
    assert stats_exec.deleted == 1
    assert service.files().deleted == [("1", True)]


def test_cleanup_calendar_events_filters_prefix_and_cutoff():
    module = _load_module()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    older = _to_rfc3339(cutoff - timedelta(hours=2))
    newer = _to_rfc3339(cutoff + timedelta(hours=2))
    service = _CalendarService(
        [
            {"id": "e1", "summary": "codex-it-event-old", "updated": older},
            {"id": "e2", "summary": "codex-it-event-new", "updated": newer},
            {"id": "e3", "summary": "other-event-old", "updated": older},
        ]
    )

    stats = module.cleanup_calendar_events(service, prefix="codex-it-", cutoff=cutoff, execute=True, max_items=100)
    assert stats.scanned == 3
    assert stats.matched == 1
    assert stats.deleted == 1
    assert service.events().deleted == [("primary", "e1")]


def test_cleanup_task_lists_filters_prefix_and_cutoff():
    module = _load_module()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    older = _to_rfc3339(cutoff - timedelta(hours=3))
    newer = _to_rfc3339(cutoff + timedelta(hours=3))
    service = _TasksService(
        [
            {"id": "t1", "title": "codex-it-list-old", "updated": older},
            {"id": "t2", "title": "codex-it-list-new", "updated": newer},
            {"id": "t3", "title": "other-list-old", "updated": older},
        ]
    )

    stats = module.cleanup_task_lists(service, prefix="codex-it-", cutoff=cutoff, execute=True, max_items=100)
    assert stats.scanned == 3
    assert stats.matched == 1
    assert stats.deleted == 1
    assert service.tasklists().deleted == ["t1"]
