"""Unit tests for Gmail label mutator dry-run behavior."""

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


def _load_gmail_labels_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gmail" / "labels.py"

    module_name = "_test_gmail_labels_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def gmail_labels_module():
    module_keys = [
        "auth",
        "auth.scopes",
        "auth.service_decorator",
        "core",
        "core.errors",
        "core.server",
        "core.utils",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_scopes = types.ModuleType("auth.scopes")
    auth_scopes.GMAIL_LABELS_SCOPE = "https://www.googleapis.com/auth/gmail.labels"
    auth_scopes.GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_errors = types.ModuleType("core.errors")
    core_server = types.ModuleType("core.server")
    core_utils = types.ModuleType("core.utils")

    class ValidationError(Exception):
        pass

    core_errors.ValidationError = ValidationError
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils.handle_http_errors = _identity_decorator

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.scopes"] = auth_scopes
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.errors"] = core_errors
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils

    try:
        yield _load_gmail_labels_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_manage_gmail_label_create_dry_run_default_skips_mutation(gmail_labels_module):
    service = MagicMock()

    result = await gmail_labels_module.manage_gmail_label(
        service=service,
        user_google_email="user@example.com",
        action="create",
        name="Project Label",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create Gmail label 'Project Label'" in result
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_manage_gmail_label_update_dry_run_default_skips_mutation(gmail_labels_module):
    service = MagicMock()

    result = await gmail_labels_module.manage_gmail_label(
        service=service,
        user_google_email="user@example.com",
        action="update",
        label_id="Label_123",
        name="Renamed Label",
    )

    assert result.startswith("DRY RUN:")
    assert "Would update Gmail label 'Label_123'" in result
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_manage_gmail_label_delete_dry_run_default_skips_mutation(gmail_labels_module):
    service = MagicMock()

    result = await gmail_labels_module.manage_gmail_label(
        service=service,
        user_google_email="user@example.com",
        action="delete",
        label_id="Label_123",
    )

    assert result.startswith("DRY RUN:")
    assert "Would delete Gmail label 'Label_123'" in result
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_manage_gmail_label_create_dry_run_false_calls_create(gmail_labels_module):
    service = MagicMock()
    service.users.return_value.labels.return_value.create.return_value.execute.return_value = {
        "id": "Label_123",
        "name": "Project Label",
    }

    result = await gmail_labels_module.manage_gmail_label(
        service=service,
        user_google_email="user@example.com",
        action="create",
        name="Project Label",
        dry_run=False,
    )

    assert "Label created successfully!" in result
    assert "ID: Label_123" in result
    assert service.users.return_value.labels.return_value.create.call_count == 1


@pytest.mark.asyncio
async def test_modify_gmail_message_labels_dry_run_default_skips_mutation(gmail_labels_module):
    service = MagicMock()

    result = await gmail_labels_module.modify_gmail_message_labels(
        service=service,
        user_google_email="user@example.com",
        message_id="msg-123",
        add_label_ids=["Label_A"],
        remove_label_ids=["INBOX"],
    )

    assert result.startswith("DRY RUN:")
    assert "Would modify Gmail labels for message 'msg-123'" in result
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_modify_gmail_message_labels_dry_run_false_calls_modify(gmail_labels_module):
    service = MagicMock()
    service.users.return_value.messages.return_value.modify.return_value.execute.return_value = {}

    result = await gmail_labels_module.modify_gmail_message_labels(
        service=service,
        user_google_email="user@example.com",
        message_id="msg-123",
        add_label_ids=["Label_A"],
        remove_label_ids=["INBOX"],
        dry_run=False,
    )

    assert "Message labels updated successfully!" in result
    assert "Message ID: msg-123" in result
    assert service.users.return_value.messages.return_value.modify.call_count == 1


@pytest.mark.asyncio
async def test_batch_modify_gmail_message_labels_dry_run_default_skips_mutation(gmail_labels_module):
    service = MagicMock()

    result = await gmail_labels_module.batch_modify_gmail_message_labels(
        service=service,
        user_google_email="user@example.com",
        message_ids=["msg-1", "msg-2"],
        add_label_ids=["Label_A"],
        remove_label_ids=["INBOX"],
    )

    assert result.startswith("DRY RUN:")
    assert "Would batch modify Gmail labels for 2 message(s)" in result
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_batch_modify_gmail_message_labels_dry_run_false_calls_batch_modify(gmail_labels_module):
    service = MagicMock()
    service.users.return_value.messages.return_value.batchModify.return_value.execute.return_value = {}

    result = await gmail_labels_module.batch_modify_gmail_message_labels(
        service=service,
        user_google_email="user@example.com",
        message_ids=["msg-1", "msg-2"],
        add_label_ids=["Label_A"],
        remove_label_ids=["INBOX"],
        dry_run=False,
    )

    assert "Labels updated for 2 messages" in result
    assert service.users.return_value.messages.return_value.batchModify.call_count == 1
