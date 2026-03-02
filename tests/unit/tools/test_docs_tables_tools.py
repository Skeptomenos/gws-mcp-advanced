"""Unit tests for Google Docs table mutator dry-run behavior."""

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


class _ValidationManager:
    def validate_document_id(self, _document_id: str):
        return True, ""

    def validate_table_data(self, table_data: list[list[str]]):
        if not table_data:
            return False, "Table data cannot be empty"
        return True, ""

    def validate_index(self, index: int, _name: str = "Index"):
        if index < 1:
            return False, "Index must be >= 1"
        return True, ""


class _TableOperationManager:
    calls: int = 0

    def __init__(self, _service):
        self._service = _service

    async def create_and_populate_table(
        self,
        _document_id: str,
        table_data: list[list[str]],
        index: int,
        _bold_headers: bool,
    ):
        self.__class__.calls += 1
        return True, "Created table", {"rows": len(table_data), "columns": len(table_data[0]), "index": index}


def _load_tables_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gdocs" / "tables.py"

    module_name = "_test_gdocs_tables_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def docs_tables_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
        "gdocs",
        "gdocs.docs_structure",
        "gdocs.managers",
        "gdrive",
        "gdrive.drive_helpers",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_server = types.ModuleType("core.server")
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils = types.ModuleType("core.utils")
    core_utils.handle_http_errors = _identity_decorator

    gdocs_pkg = types.ModuleType("gdocs")
    gdocs_docs_structure = types.ModuleType("gdocs.docs_structure")
    gdocs_docs_structure.find_tables = lambda _doc: []
    gdocs_managers = types.ModuleType("gdocs.managers")
    gdocs_managers.TableOperationManager = _TableOperationManager
    gdocs_managers.ValidationManager = _ValidationManager

    gdrive_pkg = types.ModuleType("gdrive")
    gdrive_helpers = types.ModuleType("gdrive.drive_helpers")
    gdrive_helpers.resolve_file_id_or_alias = lambda value: value

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["gdocs"] = gdocs_pkg
    sys.modules["gdocs.docs_structure"] = gdocs_docs_structure
    sys.modules["gdocs.managers"] = gdocs_managers
    sys.modules["gdrive"] = gdrive_pkg
    sys.modules["gdrive.drive_helpers"] = gdrive_helpers

    _TableOperationManager.calls = 0
    try:
        yield _load_tables_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_table_with_data_dry_run_default_skips_mutation(docs_tables_module):
    service = MagicMock()
    table_data = [["H1", "H2"], ["A", "B"]]

    result = await docs_tables_module.create_table_with_data(
        service=service,
        user_google_email="user@example.com",
        document_id="doc-123",
        table_data=table_data,
        index=10,
    )

    assert result.startswith("DRY RUN:")
    assert "Table: 2x2" in result
    assert _TableOperationManager.calls == 0


@pytest.mark.asyncio
async def test_create_table_with_data_dry_run_false_executes_table_manager(docs_tables_module):
    service = MagicMock()
    table_data = [["H1", "H2"], ["A", "B"]]

    result = await docs_tables_module.create_table_with_data(
        service=service,
        user_google_email="user@example.com",
        document_id="doc-123",
        table_data=table_data,
        index=10,
        dry_run=False,
    )

    assert result.startswith("SUCCESS:")
    assert "Table: 2x2" in result
    assert _TableOperationManager.calls == 1
