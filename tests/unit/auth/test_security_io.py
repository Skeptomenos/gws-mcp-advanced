"""Unit tests for auth.security_io helpers."""

import os
import stat

import pytest

from auth.security_io import atomic_write_json, ensure_secure_directory


def test_atomic_write_json_writes_and_overwrites(tmp_path):
    """Atomic JSON writer should persist and overwrite file content safely."""
    target_file = tmp_path / "state.json"

    atomic_write_json(str(target_file), {"value": 1})
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") != ""

    atomic_write_json(str(target_file), {"value": 2})
    assert '"value": 2' in target_file.read_text(encoding="utf-8")


@pytest.mark.skipif(os.name == "nt", reason="POSIX file mode semantics are not guaranteed on Windows")
def test_atomic_write_json_applies_secure_file_mode(tmp_path):
    """Atomic JSON writer should apply restrictive permissions on POSIX systems."""
    target_file = tmp_path / "credentials.json"

    atomic_write_json(str(target_file), {"token": "secret"})
    file_mode = stat.S_IMODE(target_file.stat().st_mode)

    assert file_mode == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory mode semantics are not guaranteed on Windows")
def test_ensure_secure_directory_applies_secure_mode(tmp_path):
    """Directory helper should enforce restrictive directory permissions on POSIX systems."""
    secure_dir = tmp_path / "secure-dir"

    ensure_secure_directory(str(secure_dir))
    dir_mode = stat.S_IMODE(secure_dir.stat().st_mode)

    assert dir_mode == 0o700
