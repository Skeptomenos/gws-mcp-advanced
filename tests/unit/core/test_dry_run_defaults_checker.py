"""Tests for scripts/check_dry_run_defaults.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "check_dry_run_defaults.py"
    spec = importlib.util.spec_from_file_location("check_dry_run_defaults", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checker_reports_missing_dry_run_parameter(tmp_path):
    """Checker should flag required functions missing dry_run."""
    module = _load_checker_module()
    bad_file = tmp_path / "bad_tool.py"
    bad_file.write_text(
        """
async def create_event(service, user_google_email: str):
    return "ok"
""".strip(),
        encoding="utf-8",
    )

    violations = module.find_dry_run_violations_for_file(bad_file, ["create_event"])
    assert len(violations) == 1
    assert "missing dry_run parameter" in violations[0]


def test_checker_reports_non_true_dry_run_default(tmp_path):
    """Checker should reject dry_run defaults that are not True."""
    module = _load_checker_module()
    bad_file = tmp_path / "bad_default.py"
    bad_file.write_text(
        """
async def create_event(service, user_google_email: str, dry_run: bool = False):
    return "ok"
""".strip(),
        encoding="utf-8",
    )

    violations = module.find_dry_run_violations_for_file(bad_file, ["create_event"])
    assert len(violations) == 1
    assert "must default dry_run to True" in violations[0]


def test_checker_accepts_bool_true_dry_run_default(tmp_path):
    """Checker should pass when dry_run default is literal True."""
    module = _load_checker_module()
    good_file = tmp_path / "good_default.py"
    good_file.write_text(
        """
async def create_event(service, user_google_email: str, dry_run: bool = True):
    return "ok"
""".strip(),
        encoding="utf-8",
    )

    violations = module.find_dry_run_violations_for_file(good_file, ["create_event"])
    assert violations == []


def test_checker_accepts_fastapi_body_true_default(tmp_path):
    """Checker should accept FastAPI Body(True, ...) defaults."""
    module = _load_checker_module()
    good_file = tmp_path / "body_default.py"
    good_file.write_text(
        """
from fastapi import Body

async def create_event(service, user_google_email: str, dry_run: bool = Body(True, description="safe")):
    return "ok"
""".strip(),
        encoding="utf-8",
    )

    violations = module.find_dry_run_violations_for_file(good_file, ["create_event"])
    assert violations == []
