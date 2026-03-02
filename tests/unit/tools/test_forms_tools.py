"""Unit tests for Google Forms mutator dry-run behavior."""

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


def _load_forms_tools_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gforms" / "forms_tools.py"

    module_name = "_test_gforms_forms_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def forms_tools_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
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

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils

    try:
        yield _load_forms_tools_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_form_dry_run_default_skips_mutation(forms_tools_module):
    service = MagicMock()

    result = await forms_tools_module.create_form(
        service=service,
        user_google_email="user@example.com",
        title="Demo Form",
        description="Testing",
    )

    assert result.startswith("DRY RUN:")
    assert "Would create form 'Demo Form'" in result
    assert service.forms.call_count == 0


@pytest.mark.asyncio
async def test_create_form_dry_run_false_calls_create(forms_tools_module):
    service = MagicMock()
    service.forms.return_value.create.return_value.execute.return_value = {
        "formId": "form-123",
        "info": {"title": "Demo Form"},
        "responderUri": "https://docs.google.com/forms/d/form-123/viewform",
    }

    result = await forms_tools_module.create_form(
        service=service,
        user_google_email="user@example.com",
        title="Demo Form",
        dry_run=False,
    )

    assert "Successfully created form 'Demo Form'" in result
    assert service.forms.return_value.create.call_count == 1


@pytest.mark.asyncio
async def test_set_publish_settings_dry_run_default_skips_mutation(forms_tools_module):
    service = MagicMock()

    result = await forms_tools_module.set_publish_settings(
        service=service,
        user_google_email="user@example.com",
        form_id="form-123",
        publish_as_template=True,
        require_authentication=True,
    )

    assert result.startswith("DRY RUN:")
    assert "Would update publish settings for form form-123" in result
    assert service.forms.call_count == 0


@pytest.mark.asyncio
async def test_set_publish_settings_dry_run_false_calls_mutation(forms_tools_module):
    service = MagicMock()
    service.forms.return_value.setPublishSettings.return_value.execute.return_value = {}

    result = await forms_tools_module.set_publish_settings(
        service=service,
        user_google_email="user@example.com",
        form_id="form-123",
        publish_as_template=False,
        require_authentication=True,
        dry_run=False,
    )

    assert "Successfully updated publish settings for form form-123" in result
    assert service.forms.return_value.setPublishSettings.call_count == 1
