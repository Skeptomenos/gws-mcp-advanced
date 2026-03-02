"""Dry-run contract tests for remaining Google Sheets mutators."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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


class _UserInputError(Exception):
    pass


def _load_sheets_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gsheets" / "sheets_tools.py"

    module_name = "_test_gsheets_dry_run_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sheets_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
        "gdocs",
        "gdocs.comments",
        "gsheets",
        "gsheets.sheets_helpers",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_server = types.ModuleType("core.server")
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils = types.ModuleType("core.utils")
    core_utils.UserInputError = _UserInputError
    core_utils.handle_http_errors = _identity_decorator

    gdocs_pkg = types.ModuleType("gdocs")
    gdocs_comments = types.ModuleType("gdocs.comments")
    gdocs_comments.create_comment_tools = lambda *_args, **_kwargs: {
        "read_comments": lambda *_a, **_k: "ok",
        "create_comment": lambda *_a, **_k: "ok",
        "reply_to_comment": lambda *_a, **_k: "ok",
        "resolve_comment": lambda *_a, **_k: "ok",
    }

    gsheets_pkg = types.ModuleType("gsheets")
    gsheets_helpers = types.ModuleType("gsheets.sheets_helpers")
    gsheets_helpers.CONDITION_TYPES = {"NUMBER_GREATER", "TEXT_CONTAINS"}
    gsheets_helpers._a1_range_for_values = lambda *_args, **_kwargs: "A1"
    gsheets_helpers._build_boolean_rule = (
        lambda ranges, condition_type, condition_values, background_color, text_color: (
            {
                "ranges": ranges,
                "booleanRule": {
                    "condition": {"type": condition_type.upper()},
                    "format": {
                        **({"backgroundColor": {"red": 1}} if background_color else {}),
                        **({"textFormat": {"foregroundColor": {"red": 1}}} if text_color else {}),
                    },
                },
            },
            condition_type.upper(),
        )
    )
    gsheets_helpers._build_gradient_rule = lambda ranges, points: {"ranges": ranges, "gradientRule": {"points": points}}
    gsheets_helpers._fetch_detailed_sheet_errors = AsyncMock(return_value=[])
    gsheets_helpers._fetch_sheets_with_rules = AsyncMock(
        return_value=(
            [
                {
                    "properties": {"sheetId": 0, "title": "Sheet1"},
                    "conditionalFormats": [
                        {
                            "ranges": [{"sheetId": 0}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "1"}]},
                                "format": {"backgroundColor": {"red": 1}},
                            },
                        }
                    ],
                }
            ],
            {0: "Sheet1"},
        )
    )
    gsheets_helpers._format_conditional_rules_section = lambda *_args, **_kwargs: "STATE"
    gsheets_helpers._format_sheet_error_section = lambda *_args, **_kwargs: ""
    gsheets_helpers._parse_a1_range = lambda _range_name, _sheets: {
        "sheetId": 0,
        "startRowIndex": 0,
        "endRowIndex": 1,
        "startColumnIndex": 0,
        "endColumnIndex": 1,
    }
    gsheets_helpers._parse_condition_values = lambda values: json.loads(values) if isinstance(values, str) else values
    gsheets_helpers._parse_gradient_points = lambda points: json.loads(points) if isinstance(points, str) else points
    gsheets_helpers._parse_hex_color = lambda color: {"red": 1.0, "green": 0.0, "blue": 0.0} if color else None
    gsheets_helpers._select_sheet = lambda sheets, _sheet_name: sheets[0]
    gsheets_helpers._values_contain_sheets_errors = lambda *_args, **_kwargs: False

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["gdocs"] = gdocs_pkg
    sys.modules["gdocs.comments"] = gdocs_comments
    sys.modules["gsheets"] = gsheets_pkg
    sys.modules["gsheets.sheets_helpers"] = gsheets_helpers

    try:
        yield _load_sheets_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_format_sheet_range_dry_run_default_skips_mutation(sheets_module):
    service = MagicMock()
    service.spreadsheets.return_value.get.return_value.execute.return_value = {
        "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1"}}]
    }

    result = await sheets_module.format_sheet_range(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        range_name="A1:B2",
        background_color="#FF0000",
    )

    assert result.startswith("DRY RUN:")
    assert "Would apply formatting to range 'A1:B2'" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 0


@pytest.mark.asyncio
async def test_format_sheet_range_dry_run_false_executes_mutation(sheets_module):
    service = MagicMock()
    service.spreadsheets.return_value.get.return_value.execute.return_value = {
        "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1"}}]
    }
    service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await sheets_module.format_sheet_range(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        range_name="A1:B2",
        background_color="#FF0000",
        dry_run=False,
    )

    assert "Applied formatting to range 'A1:B2'" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_add_conditional_formatting_dry_run_default_skips_mutation(sheets_module):
    service = MagicMock()

    result = await sheets_module.add_conditional_formatting(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        range_name="A1:A10",
        condition_type="NUMBER_GREATER",
        condition_values="[100]",
        background_color="#00FF00",
    )

    assert result.startswith("DRY RUN:")
    assert "Would add conditional format on 'A1:A10'" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 0


@pytest.mark.asyncio
async def test_add_conditional_formatting_dry_run_false_executes_mutation(sheets_module):
    service = MagicMock()
    service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await sheets_module.add_conditional_formatting(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        range_name="A1:A10",
        condition_type="NUMBER_GREATER",
        condition_values="[100]",
        background_color="#00FF00",
        dry_run=False,
    )

    assert "Added conditional format on 'A1:A10'" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_update_conditional_formatting_dry_run_default_skips_mutation(sheets_module):
    service = MagicMock()

    result = await sheets_module.update_conditional_formatting(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        rule_index=0,
        condition_type="NUMBER_GREATER",
        condition_values="[200]",
        background_color="#0000FF",
    )

    assert result.startswith("DRY RUN:")
    assert "Would update conditional format at index 0" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 0


@pytest.mark.asyncio
async def test_update_conditional_formatting_dry_run_false_executes_mutation(sheets_module):
    service = MagicMock()
    service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await sheets_module.update_conditional_formatting(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        rule_index=0,
        condition_type="NUMBER_GREATER",
        condition_values="[200]",
        background_color="#0000FF",
        dry_run=False,
    )

    assert "Updated conditional format at index 0" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_delete_conditional_formatting_dry_run_default_skips_mutation(sheets_module):
    service = MagicMock()

    result = await sheets_module.delete_conditional_formatting(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        rule_index=0,
    )

    assert result.startswith("DRY RUN:")
    assert "Would delete conditional format at index 0" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 0


@pytest.mark.asyncio
async def test_delete_conditional_formatting_dry_run_false_executes_mutation(sheets_module):
    service = MagicMock()
    service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await sheets_module.delete_conditional_formatting(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        rule_index=0,
        dry_run=False,
    )

    assert "Deleted conditional format at index 0" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_create_sheet_dry_run_default_skips_mutation(sheets_module):
    service = MagicMock()

    result = await sheets_module.create_sheet(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        sheet_name="New Sheet",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create sheet 'New Sheet'" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 0


@pytest.mark.asyncio
async def test_create_sheet_dry_run_false_executes_mutation(sheets_module):
    service = MagicMock()
    service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {
        "replies": [{"addSheet": {"properties": {"sheetId": 12345}}}]
    }

    result = await sheets_module.create_sheet(
        service=service,
        user_google_email="user@example.com",
        spreadsheet_id="spreadsheet-1",
        sheet_name="New Sheet",
        dry_run=False,
    )

    assert "Successfully created sheet 'New Sheet' (ID: 12345)" in result
    assert service.spreadsheets.return_value.batchUpdate.call_count == 1
