"""Unit tests for distribution guard scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[3]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pypi_check_module():
    return _load_module("_test_check_pypi_version_available", "scripts/check_pypi_version_available.py")


def test_pypi_version_exists_true(pypi_check_module):
    package_data = {"releases": {"1.0.0": [{}], "1.0.1": [{}]}}
    assert pypi_check_module._version_exists(package_data, "1.0.0") is True


def test_pypi_version_exists_false(pypi_check_module):
    package_data = {"releases": {"1.0.1": [{}]}}
    assert pypi_check_module._version_exists(package_data, "1.0.0") is False


def test_pypi_version_exists_false_for_invalid_release_shape(pypi_check_module):
    package_data = {"releases": []}
    assert pypi_check_module._version_exists(package_data, "1.0.0") is False


def test_check_pypi_main_success(monkeypatch, pypi_check_module):
    monkeypatch.setattr(
        pypi_check_module,
        "_fetch_pypi_package_json",
        lambda package: {"releases": {"1.0.0": [{}]}},
    )
    monkeypatch.setattr(
        pypi_check_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(package="gws-mcp-advanced", version="1.0.0"),
    )
    assert pypi_check_module.main() == 0


def test_check_pypi_main_missing_version(monkeypatch, pypi_check_module):
    monkeypatch.setattr(
        pypi_check_module,
        "_fetch_pypi_package_json",
        lambda package: {"releases": {"1.0.1": [{}]}},
    )
    monkeypatch.setattr(
        pypi_check_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(package="gws-mcp-advanced", version="1.0.0"),
    )
    assert pypi_check_module.main() == 1
