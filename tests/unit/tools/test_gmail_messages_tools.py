"""Unit tests for Gmail message mutator dry-run behavior."""

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


def _body(default=None, **_kwargs):
    return default


def _load_gmail_messages_module():
    root = Path(__file__).resolve().parents[3]
    package_path = root / "gmail"
    helpers_path = package_path / "helpers.py"
    messages_path = package_path / "messages.py"

    helpers_spec = importlib.util.spec_from_file_location("gmail.helpers", helpers_path)
    assert helpers_spec is not None and helpers_spec.loader is not None
    helpers_module = importlib.util.module_from_spec(helpers_spec)
    sys.modules["gmail.helpers"] = helpers_module
    helpers_spec.loader.exec_module(helpers_module)

    messages_spec = importlib.util.spec_from_file_location("gmail.messages", messages_path)
    assert messages_spec is not None and messages_spec.loader is not None
    messages_module = importlib.util.module_from_spec(messages_spec)
    sys.modules["gmail.messages"] = messages_module
    messages_spec.loader.exec_module(messages_module)
    return messages_module


@pytest.fixture
def gmail_messages_module():
    module_keys = [
        "auth",
        "auth.scopes",
        "auth.service_decorator",
        "core",
        "core.errors",
        "core.server",
        "core.utils",
        "fastapi",
        "gmail",
        "gmail.helpers",
        "gmail.messages",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_scopes = types.ModuleType("auth.scopes")
    auth_scopes.GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
    auth_scopes.GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
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

    fastapi_module = types.ModuleType("fastapi")
    fastapi_module.Body = _body

    gmail_pkg = types.ModuleType("gmail")
    gmail_pkg.__path__ = [str(Path(__file__).resolve().parents[3] / "gmail")]

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.scopes"] = auth_scopes
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.errors"] = core_errors
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["fastapi"] = fastapi_module
    sys.modules["gmail"] = gmail_pkg

    try:
        yield _load_gmail_messages_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_send_gmail_message_dry_run_skips_message_build_and_send(gmail_messages_module, monkeypatch):
    service = MagicMock()
    prepare_called = False

    def fake_prepare(**_kwargs):
        nonlocal prepare_called
        prepare_called = True
        return "raw", None

    monkeypatch.setattr(gmail_messages_module, "_prepare_gmail_message", fake_prepare)

    result = await gmail_messages_module.send_gmail_message(
        service=service,
        user_google_email="user@example.com",
        to="friend@example.com",
        subject="Hello",
        body="Hi there",
    )

    assert result.startswith("DRY RUN:")
    assert "Would send email from user@example.com" in result
    assert prepare_called is False
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_send_gmail_message_dry_run_false_executes_send(gmail_messages_module, monkeypatch):
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "msg-123"}

    monkeypatch.setattr(
        gmail_messages_module,
        "_prepare_gmail_message",
        lambda **_kwargs: ("encoded-raw-message", "thread-123"),
    )

    result = await gmail_messages_module.send_gmail_message(
        service=service,
        user_google_email="user@example.com",
        to="friend@example.com",
        subject="Hello",
        body="Hi there",
        dry_run=False,
    )

    assert result == "Email sent! Message ID: msg-123"
    service.users.return_value.messages.return_value.send.assert_called_once_with(
        userId="me",
        body={"raw": "encoded-raw-message", "threadId": "thread-123"},
    )


@pytest.mark.asyncio
async def test_draft_gmail_message_dry_run_skips_message_build_and_create(gmail_messages_module, monkeypatch):
    service = MagicMock()
    prepare_called = False

    def fake_prepare(**_kwargs):
        nonlocal prepare_called
        prepare_called = True
        return "raw", None

    monkeypatch.setattr(gmail_messages_module, "_prepare_gmail_message", fake_prepare)

    result = await gmail_messages_module.draft_gmail_message(
        service=service,
        user_google_email="user@example.com",
        subject="Draft Subject",
        body="Draft body",
        to="friend@example.com",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create draft from user@example.com" in result
    assert prepare_called is False
    assert service.users.call_count == 0


@pytest.mark.asyncio
async def test_draft_gmail_message_dry_run_false_executes_create(gmail_messages_module, monkeypatch):
    service = MagicMock()
    service.users.return_value.drafts.return_value.create.return_value.execute.return_value = {"id": "draft-123"}

    monkeypatch.setattr(
        gmail_messages_module,
        "_prepare_gmail_message",
        lambda **_kwargs: ("encoded-raw-message", "thread-123"),
    )

    result = await gmail_messages_module.draft_gmail_message(
        service=service,
        user_google_email="user@example.com",
        subject="Draft Subject",
        body="Draft body",
        to="friend@example.com",
        dry_run=False,
    )

    assert result == "Draft created! Draft ID: draft-123"
    service.users.return_value.drafts.return_value.create.assert_called_once_with(
        userId="me",
        body={"message": {"raw": "encoded-raw-message", "threadId": "thread-123"}},
    )
