"""OAuth client registry and resolver for single-MCP multi-client auth."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auth.config import get_credentials_directory, reload_oauth_config
from auth.security_io import atomic_write_json, ensure_secure_directory
from core.errors import AuthenticationError

logger = logging.getLogger(__name__)

AUTH_CLIENTS_FILENAME = "auth_clients.json"
SELECTION_MODE_MAPPED_ONLY = "mapped_only"
ALLOWED_SELECTION_MODES = {SELECTION_MODE_MAPPED_ONLY, "default_first"}


@dataclass(frozen=True)
class OAuthClientSelection:
    """Resolved OAuth client selection for a user/account."""

    client_key: str
    client_id: str
    client_secret: str | None
    source: str
    selection_mode: str
    flow_preference: str | None = None


def get_auth_clients_config_path() -> str:
    """Return canonical auth-clients config path under WORKSPACE_MCP_CONFIG_DIR."""
    return str(Path(get_credentials_directory()) / AUTH_CLIENTS_FILENAME)


def _default_auth_clients_config() -> dict[str, Any]:
    """Return default auth-clients config skeleton."""
    return {
        "version": 1,
        "selection_mode": SELECTION_MODE_MAPPED_ONLY,
        "default_client": None,
        "oauth_clients": {},
        "script_clients": {},
        "account_clients": {},
        "domain_clients": {},
    }


def ensure_auth_clients_config() -> tuple[dict[str, Any], bool]:
    """Ensure auth_clients.json exists and return config + created flag."""
    config_path = Path(get_auth_clients_config_path())
    ensure_secure_directory(str(config_path.parent))

    if not config_path.exists():
        config = _default_auth_clients_config()
        atomic_write_json(str(config_path), config)
        logger.warning("Created auth clients config skeleton at %s", config_path)
        return config, True

    try:
        with config_path.open() as fp:
            raw = json.load(fp)
        if not isinstance(raw, dict):
            raise ValueError("root object must be a JSON object")
        return raw, False
    except Exception as exc:
        raise AuthenticationError(
            f"Failed to read auth client config at {config_path}: {exc}. Fix the file or remove it and retry."
        ) from exc


def _normalized_email(user_google_email: str) -> str:
    normalized = (user_google_email or "").strip().lower()
    if "@" not in normalized:
        raise AuthenticationError(
            f"Invalid user_google_email '{user_google_email}'. A valid email is required for client selection."
        )
    return normalized


def _extract_domain(user_google_email: str) -> str:
    normalized = _normalized_email(user_google_email)
    return normalized.split("@", 1)[1]


def _normalize_client_key(client_key: str) -> str:
    normalized = (client_key or "").strip().lower()
    if not normalized:
        raise AuthenticationError("client_key must be a non-empty string")
    return normalized


def _normalize_email_map(account_clients: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for user_email, client_key in account_clients.items():
        if not isinstance(user_email, str) or not isinstance(client_key, str):
            continue
        normalized[_normalized_email(user_email)] = _normalize_client_key(client_key)
    return normalized


def _normalize_domain_map(domain_clients: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for domain, client_key in domain_clients.items():
        if not isinstance(domain, str) or not isinstance(client_key, str):
            continue
        normalized[domain.strip().lower()] = _normalize_client_key(client_key)
    return normalized


def _normalize_script_id(script_id: str) -> str:
    normalized = (script_id or "").strip()
    if not normalized:
        raise AuthenticationError("script_id must be a non-empty string")
    return normalized


def _normalize_script_map(script_clients: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for script_id, client_key in script_clients.items():
        if not isinstance(script_id, str) or not isinstance(client_key, str):
            continue
        normalized[_normalize_script_id(script_id)] = _normalize_client_key(client_key)
    return normalized


def _normalize_clients_map(oauth_clients: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for client_key, payload in oauth_clients.items():
        if not isinstance(client_key, str) or not isinstance(payload, dict):
            continue
        normalized[_normalize_client_key(client_key)] = payload
    return normalized


def _config_has_usable_profiles(oauth_clients: dict[str, dict[str, Any]]) -> bool:
    for payload in oauth_clients.values():
        if isinstance(payload.get("client_id"), str) and payload["client_id"].strip():
            return True
    return False


def _resolve_legacy_env_client() -> OAuthClientSelection:
    """Resolve legacy/global OAuth client from environment or embedded config."""
    config = reload_oauth_config()
    if not config.client_id:
        raise AuthenticationError(
            "No OAuth client credentials configured. "
            "Set GOOGLE_OAUTH_CLIENT_ID/GOOGLE_OAUTH_CLIENT_SECRET or configure auth_clients.json."
        )
    return OAuthClientSelection(
        client_key="legacy-env",
        client_id=config.client_id,
        client_secret=config.client_secret,
        source="legacy_env",
        selection_mode=SELECTION_MODE_MAPPED_ONLY,
        flow_preference=None,
    )


def resolve_oauth_client_for_user(
    user_google_email: str | None,
    *,
    override_client_key: str | None = None,
    script_id: str | None = None,
) -> OAuthClientSelection:
    """
    Resolve OAuth client for a user with deterministic precedence.

    Precedence:
    1. internal/admin override
    2. script mapping
    3. account mapping
    4. domain mapping
    5. default client (only in non-mapped_only mode)
    6. legacy env fallback (only when config is effectively unconfigured)
    """
    user_email: str | None = None
    user_domain: str | None = None
    if user_google_email:
        user_email = _normalized_email(user_google_email)
        user_domain = _extract_domain(user_email)
    normalized_script_id = _normalize_script_id(script_id) if isinstance(script_id, str) and script_id.strip() else None

    raw_config, _ = ensure_auth_clients_config()
    selection_mode = str(raw_config.get("selection_mode", SELECTION_MODE_MAPPED_ONLY)).strip().lower()
    if selection_mode not in ALLOWED_SELECTION_MODES:
        raise AuthenticationError(
            f"Unsupported selection_mode '{selection_mode}' in {get_auth_clients_config_path()}. "
            f"Supported: {sorted(ALLOWED_SELECTION_MODES)}"
        )

    oauth_clients = _normalize_clients_map(raw_config.get("oauth_clients", {}))
    script_clients = _normalize_script_map(raw_config.get("script_clients", {}))
    account_clients = _normalize_email_map(raw_config.get("account_clients", {}))
    domain_clients = _normalize_domain_map(raw_config.get("domain_clients", {}))
    default_client = raw_config.get("default_client")
    default_client_key = _normalize_client_key(default_client) if isinstance(default_client, str) else None

    resolved_key: str | None = None
    source = "none"
    if override_client_key:
        resolved_key = _normalize_client_key(override_client_key)
        source = "override"
    elif normalized_script_id and normalized_script_id in script_clients:
        resolved_key = script_clients[normalized_script_id]
        source = "script_map"
    elif user_email and user_email in account_clients:
        resolved_key = account_clients[user_email]
        source = "account_map"
    elif user_domain and user_domain in domain_clients:
        resolved_key = domain_clients[user_domain]
        source = "domain_map"
    elif selection_mode != SELECTION_MODE_MAPPED_ONLY and default_client_key:
        resolved_key = default_client_key
        source = "default_client"

    configured = bool(script_clients or account_clients or domain_clients or _config_has_usable_profiles(oauth_clients))

    if resolved_key == "legacy-env":
        return _resolve_legacy_env_client()

    if not resolved_key:
        if configured and selection_mode == SELECTION_MODE_MAPPED_ONLY:
            raise AuthenticationError(
                "No OAuth client mapping found for this account and selection_mode=mapped_only is enforced. "
                f"Add mapping for '{user_google_email}' in {get_auth_clients_config_path()} "
                "(script_clients, account_clients, or domain_clients)."
            )
        return _resolve_legacy_env_client()

    profile = oauth_clients.get(resolved_key)
    if not profile:
        raise AuthenticationError(
            f"Resolved OAuth client '{resolved_key}' from {source}, but no matching profile exists in "
            f"{get_auth_clients_config_path()}."
        )

    client_id = str(profile.get("client_id") or "").strip()
    client_secret = profile.get("client_secret")
    if not client_id:
        raise AuthenticationError(
            f"OAuth client profile '{resolved_key}' is missing client_id in {get_auth_clients_config_path()}."
        )
    if client_secret is not None:
        client_secret = str(client_secret).strip() or None

    allowed_domains_raw = profile.get("allowed_domains", [])
    allowed_domains = [
        str(item).strip().lower() for item in allowed_domains_raw if isinstance(item, str) and str(item).strip()
    ]
    if allowed_domains and user_domain and user_domain not in allowed_domains:
        raise AuthenticationError(
            f"OAuth client '{resolved_key}' is not allowed for domain '{user_domain}'. "
            "Hard-fail policy is active; no cross-client fallback will be attempted."
        )

    flow_preference = None
    if isinstance(profile.get("flow_preference"), str):
        flow_preference = profile["flow_preference"].strip().lower() or None

    return OAuthClientSelection(
        client_key=resolved_key,
        client_id=client_id,
        client_secret=client_secret,
        source=source,
        selection_mode=selection_mode,
        flow_preference=flow_preference,
    )


def _extract_google_client_credentials(client_json: dict[str, Any]) -> tuple[str, str | None]:
    """Extract client id/secret from Google OAuth client JSON format."""
    payload = client_json.get("web") if isinstance(client_json, dict) else None
    if payload is None and isinstance(client_json, dict):
        payload = client_json.get("installed")
    if payload is None and isinstance(client_json, dict):
        payload = client_json
    if not isinstance(payload, dict):
        raise AuthenticationError("OAuth client JSON must include a 'web' or 'installed' object")

    client_id = str(payload.get("client_id") or "").strip()
    client_secret_raw = payload.get("client_secret")
    client_secret = str(client_secret_raw).strip() if isinstance(client_secret_raw, str) else None

    if not client_id:
        raise AuthenticationError("OAuth client JSON is missing required field 'client_id'")
    return client_id, client_secret


def import_oauth_client_config(
    *,
    client_key: str,
    oauth_client_json_path: str,
    account_emails: list[str] | None = None,
    domains: list[str] | None = None,
    script_ids: list[str] | None = None,
    set_default: bool = False,
    flow_preference: str = "auto",
) -> dict[str, Any]:
    """Import OAuth client credentials from a Google OAuth JSON file into auth_clients.json."""
    normalized_client_key = _normalize_client_key(client_key)
    source_path = Path(oauth_client_json_path).expanduser()
    if not source_path.exists():
        raise AuthenticationError(f"OAuth client JSON file not found: {source_path}")

    try:
        with source_path.open() as fp:
            source_json = json.load(fp)
    except Exception as exc:
        raise AuthenticationError(f"Failed to read OAuth client JSON '{source_path}': {exc}") from exc

    client_id, client_secret = _extract_google_client_credentials(source_json)

    config, _ = ensure_auth_clients_config()
    oauth_clients = _normalize_clients_map(config.get("oauth_clients", {}))
    script_clients = _normalize_script_map(config.get("script_clients", {}))
    account_clients = _normalize_email_map(config.get("account_clients", {}))
    domain_clients = _normalize_domain_map(config.get("domain_clients", {}))

    normalized_domains = sorted(
        {item.strip().lower() for item in (domains or []) if isinstance(item, str) and item.strip()}
    )
    normalized_accounts = sorted(
        {_normalized_email(item) for item in (account_emails or []) if isinstance(item, str) and item.strip()}
    )
    normalized_script_ids = sorted(
        {_normalize_script_id(item) for item in (script_ids or []) if isinstance(item, str) and item.strip()}
    )

    oauth_clients[normalized_client_key] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "allowed_domains": normalized_domains,
        "flow_preference": flow_preference.strip().lower() or "auto",
    }
    for email in normalized_accounts:
        account_clients[email] = normalized_client_key
    for domain in normalized_domains:
        domain_clients[domain] = normalized_client_key
    for script_id in normalized_script_ids:
        script_clients[script_id] = normalized_client_key

    config["oauth_clients"] = oauth_clients
    config["script_clients"] = script_clients
    config["account_clients"] = account_clients
    config["domain_clients"] = domain_clients
    if set_default:
        config["default_client"] = normalized_client_key

    destination_path = Path(get_auth_clients_config_path())
    atomic_write_json(str(destination_path), config)
    logger.info(
        "Imported OAuth client '%s' into %s (scripts=%d, accounts=%d, domains=%d, default=%s)",
        normalized_client_key,
        destination_path,
        len(normalized_script_ids),
        len(normalized_accounts),
        len(normalized_domains),
        set_default,
    )

    return {
        "config_path": str(destination_path),
        "client_key": normalized_client_key,
        "client_id": client_id,
        "mapped_script_ids": normalized_script_ids,
        "mapped_accounts": normalized_accounts,
        "mapped_domains": normalized_domains,
        "set_default": set_default,
    }
