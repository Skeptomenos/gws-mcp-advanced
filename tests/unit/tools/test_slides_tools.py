"""Unit tests for Google Slides mutator dry-run behavior."""

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


def _load_slides_tools_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gslides" / "slides_tools.py"

    module_name = "_test_gslides_slides_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def slides_tools_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
        "gdocs",
        "gdocs.comments",
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
    gdocs_comments = types.ModuleType("gdocs.comments")
    gdocs_comments.create_comment_tools = lambda *_args, **_kwargs: {
        "read_comments": lambda *a, **k: "ok",
        "create_comment": lambda *a, **k: "ok",
        "reply_to_comment": lambda *a, **k: "ok",
        "resolve_comment": lambda *a, **k: "ok",
    }

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["gdocs"] = gdocs_pkg
    sys.modules["gdocs.comments"] = gdocs_comments

    try:
        yield _load_slides_tools_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_presentation_dry_run_default_skips_mutation(slides_tools_module):
    service = MagicMock()

    result = await slides_tools_module.create_presentation(
        service=service,
        user_google_email="user@example.com",
        title="Demo Deck",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create presentation 'Demo Deck'" in result
    assert service.presentations.call_count == 0


@pytest.mark.asyncio
async def test_create_presentation_dry_run_false_calls_create(slides_tools_module):
    service = MagicMock()
    service.presentations.return_value.create.return_value.execute.return_value = {
        "presentationId": "pres-123",
        "slides": [{}],
    }

    result = await slides_tools_module.create_presentation(
        service=service,
        user_google_email="user@example.com",
        title="Demo Deck",
        dry_run=False,
    )

    assert "Presentation Created Successfully" in result
    assert service.presentations.return_value.create.call_count == 1


@pytest.mark.asyncio
async def test_batch_update_presentation_dry_run_default_skips_mutation(slides_tools_module):
    service = MagicMock()
    requests = [{"createSlide": {"slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"}}}]

    result = await slides_tools_module.batch_update_presentation(
        service=service,
        user_google_email="user@example.com",
        presentation_id="pres-123",
        requests=requests,
    )

    assert result.startswith("DRY RUN:")
    assert "Would apply 1 update request(s)" in result
    assert service.presentations.call_count == 0


@pytest.mark.asyncio
async def test_batch_update_presentation_dry_run_false_calls_batch_update(slides_tools_module):
    service = MagicMock()
    service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
        "replies": [{"createSlide": {"objectId": "slide-1"}}]
    }
    requests = [{"createSlide": {"slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"}}}]

    result = await slides_tools_module.batch_update_presentation(
        service=service,
        user_google_email="user@example.com",
        presentation_id="pres-123",
        requests=requests,
        dry_run=False,
    )

    assert "Batch Update Completed" in result
    assert "Created slide with ID slide-1" in result
    assert service.presentations.return_value.batchUpdate.call_count == 1
