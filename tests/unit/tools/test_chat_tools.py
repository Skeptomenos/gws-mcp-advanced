"""Unit tests for Google Chat mutator dry-run behavior."""

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


def _load_chat_tools_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gchat" / "chat_tools.py"

    module_name = "_test_gchat_chat_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def chat_tools_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
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
    core_server = types.ModuleType("core.server")
    core_utils = types.ModuleType("core.utils")
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
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["googleapiclient"] = googleapiclient_pkg
    sys.modules["googleapiclient.errors"] = googleapiclient_errors

    try:
        yield _load_chat_tools_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_send_message_dry_run_default_skips_mutation(chat_tools_module):
    service = MagicMock()

    result = await chat_tools_module.send_message(
        service=service,
        user_google_email="user@example.com",
        space_id="spaces/AAA",
        message_text="Hello team",
    )

    assert result.startswith("DRY RUN:")
    assert "Would send message to space 'spaces/AAA'" in result
    assert service.spaces.call_count == 0


@pytest.mark.asyncio
async def test_send_message_dry_run_false_calls_create(chat_tools_module):
    service = MagicMock()
    service.spaces.return_value.messages.return_value.create.return_value.execute.return_value = {
        "name": "spaces/AAA/messages/123",
        "createTime": "2026-02-27T00:00:00Z",
    }

    result = await chat_tools_module.send_message(
        service=service,
        user_google_email="user@example.com",
        space_id="spaces/AAA",
        message_text="Hello team",
        dry_run=False,
    )

    assert "Message sent to space 'spaces/AAA'" in result
    assert service.spaces.return_value.messages.return_value.create.call_count == 1
