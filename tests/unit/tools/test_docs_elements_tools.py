"""Unit tests for Google Docs element mutator dry-run behavior."""

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


def _load_elements_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gdocs" / "elements.py"

    module_name = "_test_gdocs_elements_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def docs_elements_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
        "gdocs",
        "gdocs.docs_helpers",
        "gdrive",
        "gdrive.drive_helpers",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator
    auth_service_decorator.require_multiple_services = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_server = types.ModuleType("core.server")
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils = types.ModuleType("core.utils")
    core_utils.handle_http_errors = _identity_decorator

    gdocs_pkg = types.ModuleType("gdocs")
    gdocs_helpers = types.ModuleType("gdocs.docs_helpers")
    gdocs_helpers.create_insert_table_request = lambda index, rows, columns: {
        "insertTable": {"location": {"index": index}, "rows": rows, "columns": columns}
    }
    gdocs_helpers.create_insert_text_request = lambda index, text: {
        "insertText": {"location": {"index": index}, "text": text}
    }
    gdocs_helpers.create_bullet_list_request = lambda start, end, list_type: {
        "createParagraphBullets": {
            "range": {"startIndex": start, "endIndex": end},
            "bulletPreset": list_type,
        }
    }
    gdocs_helpers.create_insert_page_break_request = lambda index: {"insertPageBreak": {"location": {"index": index}}}
    gdocs_helpers.create_insert_image_request = lambda index, uri, width=0, height=0: {
        "insertInlineImage": {"location": {"index": index}, "uri": uri, "width": width, "height": height}
    }

    gdrive_pkg = types.ModuleType("gdrive")
    gdrive_helpers = types.ModuleType("gdrive.drive_helpers")
    gdrive_helpers.resolve_file_id_or_alias = lambda value: value

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["gdocs"] = gdocs_pkg
    sys.modules["gdocs.docs_helpers"] = gdocs_helpers
    sys.modules["gdrive"] = gdrive_pkg
    sys.modules["gdrive.drive_helpers"] = gdrive_helpers

    try:
        yield _load_elements_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_insert_doc_elements_dry_run_default_skips_mutation(docs_elements_module):
    service = MagicMock()

    result = await docs_elements_module.insert_doc_elements(
        service=service,
        user_google_email="user@example.com",
        document_id="doc-123",
        element_type="table",
        index=1,
        rows=2,
        columns=2,
    )

    assert result.startswith("DRY RUN:")
    assert "Would insert table (2x2)" in result
    assert service.documents.call_count == 0


@pytest.mark.asyncio
async def test_insert_doc_elements_dry_run_false_executes_batch_update(docs_elements_module):
    service = MagicMock()
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await docs_elements_module.insert_doc_elements(
        service=service,
        user_google_email="user@example.com",
        document_id="doc-123",
        element_type="page_break",
        index=3,
        dry_run=False,
    )

    assert "Inserted page break at index 3" in result
    assert service.documents.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_insert_doc_image_dry_run_default_skips_drive_and_docs_calls(docs_elements_module):
    docs_service = MagicMock()
    drive_service = MagicMock()

    result = await docs_elements_module.insert_doc_image(
        docs_service=docs_service,
        drive_service=drive_service,
        user_google_email="user@example.com",
        document_id="doc-123",
        image_source="https://example.com/test.png",
        index=1,
    )

    assert result.startswith("DRY RUN:")
    assert "Would insert URL image" in result
    assert docs_service.documents.call_count == 0
    assert drive_service.files.call_count == 0


@pytest.mark.asyncio
async def test_insert_doc_image_dry_run_false_executes_docs_batch_update_for_url(docs_elements_module):
    docs_service = MagicMock()
    drive_service = MagicMock()
    docs_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await docs_elements_module.insert_doc_image(
        docs_service=docs_service,
        drive_service=drive_service,
        user_google_email="user@example.com",
        document_id="doc-123",
        image_source="https://example.com/test.png",
        index=2,
        dry_run=False,
    )

    assert "Inserted URL image at index 2" in result
    assert docs_service.documents.return_value.batchUpdate.call_count == 1
    assert drive_service.files.call_count == 0
