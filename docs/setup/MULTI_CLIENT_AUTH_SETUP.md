# Single-MCP Multi-Client Auth Setup

Audience: operators who need one MCP server to work with multiple OAuth clients (for example private + enterprise tenants).

## When to Use This

Use this mode when:
1. different Google tenants require different OAuth clients,
2. enterprise policy blocks external OAuth clients,
3. you still want one MCP entry (`google-workspace`) in your client.

## Key Behavior

1. Client routing is deterministic by script/account/domain mapping.
2. `selection_mode=mapped_only` hard-fails on missing mapping or domain/client mismatch.
3. No cross-client fallback is attempted on mismatch.
4. Credentials and sessions are persisted with client context.

## Config Location

`WORKSPACE_MCP_CONFIG_DIR/auth_clients.json`

Default config root if not overridden:
`~/.config/google-workspace-mcp-advanced`

## Setup Workflow

### 1) Bootstrap `auth_clients.json`

Call MCP tool:

`setup_google_auth_clients`

This creates the config skeleton if missing and returns the exact path.

### 2) Import each OAuth client JSON

For each tenant/client, call:

`import_google_auth_client`

Parameters:
1. `client_key` (for example `private`, `work`)
2. `oauth_client_json_path` (path to downloaded Google OAuth client JSON)
3. `mapped_script_ids` (optional script IDs/deployment IDs that must use this client)
4. `mapped_accounts` (optional specific emails)
5. `mapped_domains` (optional domains)
6. `set_default` (optional, only used in non-`mapped_only` modes)

### 3) Verify generated config

Expected shape:

```json
{
  "version": 1,
  "selection_mode": "mapped_only",
  "default_client": null,
  "oauth_clients": {
    "private": {
      "client_id": "...apps.googleusercontent.com",
      "client_secret": "...",
      "allowed_domains": ["helmus.me"],
      "flow_preference": "auto"
    },
    "work": {
      "client_id": "...apps.googleusercontent.com",
      "client_secret": "...",
      "allowed_domains": ["hellofresh.com"],
      "flow_preference": "auto"
    }
  },
  "script_clients": {
    "127dMAUctpUu0-ReHWFMtt4T5HWNfzfEH-m0a-7sDzEzSskTecvMvK2xu": "private",
    "AKfycbw46UjH2FT0voBOgAWjjlbTGS7aHyVyZd70wCMxXDR16uyEN6FYvUG3vLI_Cn_5DRDHDw": "private"
  },
  "account_clients": {
    "david@helmus.me": "private",
    "david.helmus@hellofresh.com": "work"
  },
  "domain_clients": {
    "helmus.me": "private",
    "hellofresh.com": "work"
  }
}
```

### 4) Authenticate accounts

Run `start_google_auth` with a mapped `user_google_email`.

If callback completion is needed in your client lifecycle, use:
1. `start_google_auth`
2. `complete_google_auth` with `callback_url` (preferred) or `authorization_code + state`.

## Runtime Notes

1. Legacy env-only auth (`GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`) still works when auth client config is not configured yet.
2. Once mappings/profiles are configured under `mapped_only`, mapping is required.
3. Resolution precedence is: override -> `script_clients` -> `account_clients` -> `domain_clients` -> default client (non-`mapped_only` only).
4. Domain mismatch errors are expected and intentional security behavior.

## Troubleshooting

### "No OAuth client mapping found ... selection_mode=mapped_only"

Add script, account, or domain mapping in `auth_clients.json`.

### "OAuth client 'X' is not allowed for domain 'Y'"

`allowed_domains` for that client does not include the email domain.

### "Authentication completed for A, but expected B"

The callback finished with a different account than the mapped target account.
Retry with the intended Google account.
