"""Tests for scripts/check_tool_decorators.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "check_tool_decorators.py"
    spec = importlib.util.spec_from_file_location("check_tool_decorators", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checker_reports_invalid_decorator_order(tmp_path):
    """Checker should flag tool functions with wrong decorator order."""
    module = _load_checker_module()
    bad_file = tmp_path / "bad_tool.py"
    bad_file.write_text(
        """
@server.tool()
@require_google_service("gmail", "gmail_read")
@handle_http_errors("bad", is_read_only=True, service_type="gmail")
async def bad_tool(service, user_google_email: str):
    return "ok"
""".strip(),
        encoding="utf-8",
    )

    violations = module.find_decorator_order_violations_for_file(bad_file)
    assert len(violations) == 1
    assert "invalid decorator order" in violations[0]


def test_checker_accepts_expected_decorator_order(tmp_path):
    """Checker should pass when decorators use the standard order."""
    module = _load_checker_module()
    good_file = tmp_path / "good_tool.py"
    good_file.write_text(
        """
@server.tool()
@handle_http_errors("good", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_read")
async def good_tool(service, user_google_email: str):
    return "ok"
""".strip(),
        encoding="utf-8",
    )

    violations = module.find_decorator_order_violations_for_file(good_file)
    assert violations == []
