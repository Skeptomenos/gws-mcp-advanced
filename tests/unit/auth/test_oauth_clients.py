"""Unit tests for single-MCP multi-client OAuth client routing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auth.oauth_clients import (
    ensure_auth_clients_config,
    get_auth_clients_config_path,
    import_oauth_client_config,
    resolve_oauth_client_for_user,
)
from core.errors import AuthenticationError


def _write_auth_clients_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def test_resolve_oauth_client_uses_legacy_env_when_auth_clients_not_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "legacy-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "legacy-client-secret")

    resolved = resolve_oauth_client_for_user("user@example.com")

    assert resolved.client_key == "legacy-env"
    assert resolved.client_id == "legacy-client-id"
    assert Path(get_auth_clients_config_path()).exists()


def test_resolve_oauth_client_mapped_only_hard_fails_when_mapping_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "legacy-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "legacy-client-secret")

    config_path = Path(get_auth_clients_config_path())
    _write_auth_clients_config(
        config_path,
        {
            "version": 1,
            "selection_mode": "mapped_only",
            "default_client": None,
            "oauth_clients": {
                "work": {
                    "client_id": "work-client-id",
                    "client_secret": "work-client-secret",
                    "allowed_domains": ["hellofresh.com"],
                    "flow_preference": "auto",
                }
            },
            "script_clients": {},
            "account_clients": {},
            "domain_clients": {},
        },
    )

    with pytest.raises(AuthenticationError, match="selection_mode=mapped_only"):
        resolve_oauth_client_for_user("user@hellofresh.com")


def test_resolve_oauth_client_enforces_domain_mismatch_hard_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "legacy-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "legacy-client-secret")

    config_path = Path(get_auth_clients_config_path())
    _write_auth_clients_config(
        config_path,
        {
            "version": 1,
            "selection_mode": "mapped_only",
            "default_client": None,
            "oauth_clients": {
                "work": {
                    "client_id": "work-client-id",
                    "client_secret": "work-client-secret",
                    "allowed_domains": ["hellofresh.com"],
                    "flow_preference": "auto",
                }
            },
            "script_clients": {},
            "account_clients": {
                "user@gmail.com": "work",
            },
            "domain_clients": {
                "hellofresh.com": "work",
            },
        },
    )

    resolved = resolve_oauth_client_for_user("user@hellofresh.com")
    assert resolved.client_key == "work"

    with pytest.raises(AuthenticationError, match="not allowed for domain"):
        resolve_oauth_client_for_user("user@gmail.com")


def test_resolve_oauth_client_prefers_script_mapping_over_account_and_domain(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "legacy-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "legacy-client-secret")

    config_path = Path(get_auth_clients_config_path())
    _write_auth_clients_config(
        config_path,
        {
            "version": 1,
            "selection_mode": "mapped_only",
            "default_client": None,
            "oauth_clients": {
                "default": {
                    "client_id": "default-client-id",
                    "client_secret": "default-client-secret",
                    "allowed_domains": ["example.com"],
                    "flow_preference": "auto",
                },
                "scriptclient": {
                    "client_id": "script-client-id",
                    "client_secret": "script-client-secret",
                    "allowed_domains": ["example.com"],
                    "flow_preference": "auto",
                },
            },
            "script_clients": {
                "script-123": "scriptclient",
            },
            "account_clients": {
                "user@example.com": "default",
            },
            "domain_clients": {
                "example.com": "default",
            },
        },
    )

    resolved = resolve_oauth_client_for_user("user@example.com", script_id="script-123")
    assert resolved.client_key == "scriptclient"
    assert resolved.source == "script_map"

    fallback = resolve_oauth_client_for_user("user@example.com", script_id="unknown-script")
    assert fallback.client_key == "default"
    assert fallback.source == "account_map"


def test_import_oauth_client_config_updates_registry_and_mappings(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_CONFIG_DIR", str(tmp_path))
    ensure_auth_clients_config()

    oauth_json_path = tmp_path / "work-client.json"
    oauth_json_path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "work-client-id",
                    "client_secret": "work-client-secret",
                }
            }
        )
    )

    result = import_oauth_client_config(
        client_key="work",
        oauth_client_json_path=str(oauth_json_path),
        script_ids=["script-abc"],
        account_emails=["alice@hellofresh.com"],
        domains=["hellofresh.com"],
        set_default=False,
    )

    assert result["client_key"] == "work"
    config_path = Path(get_auth_clients_config_path())
    loaded = json.loads(config_path.read_text())
    assert loaded["oauth_clients"]["work"]["client_id"] == "work-client-id"
    assert loaded["script_clients"]["script-abc"] == "work"
    assert loaded["account_clients"]["alice@hellofresh.com"] == "work"
    assert loaded["domain_clients"]["hellofresh.com"] == "work"
    assert result["mapped_script_ids"] == ["script-abc"]
