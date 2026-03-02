"""Security-focused file I/O helpers for auth persistence."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

SECURE_DIR_MODE = 0o700
SECURE_FILE_MODE = 0o600


def ensure_secure_directory(path: str, mode: int = SECURE_DIR_MODE) -> None:
    """Ensure a directory exists with restrictive permissions where supported."""
    os.makedirs(path, mode=mode, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError:
        # Best effort; some platforms/filesystems do not support POSIX chmod semantics.
        pass


def atomic_write_json(
    file_path: str,
    data: dict[str, Any],
    *,
    file_mode: int = SECURE_FILE_MODE,
    dir_mode: int = SECURE_DIR_MODE,
) -> None:
    """Atomically write JSON data with restrictive file permissions."""
    dir_path = os.path.dirname(file_path) or "."
    ensure_secure_directory(dir_path, mode=dir_mode)

    fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, file_mode)
        with os.fdopen(fd, "w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, indent=2)
        os.replace(temp_path, file_path)
        try:
            os.chmod(file_path, file_mode)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
