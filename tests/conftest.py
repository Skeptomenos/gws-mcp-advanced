"""Shared pytest fixtures for gws-mcp-advanced tests."""

import tempfile
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_drive_service():
    """Create a mock Google Drive service."""
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {"id": "file1", "name": "Test File 1", "mimeType": "application/pdf"},
            {"id": "file2", "name": "Test File 2", "mimeType": "text/plain"},
        ]
    }
    return service


@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail service."""
    service = MagicMock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"},
        ]
    }
    return service


@pytest.fixture
def sample_credentials():
    """Create sample OAuth credentials for testing."""
    return {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
    }


@pytest.fixture
def env_override(monkeypatch):
    """Helper to override environment variables."""

    def _override(**kwargs):
        for key, value in kwargs.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)

    return _override
