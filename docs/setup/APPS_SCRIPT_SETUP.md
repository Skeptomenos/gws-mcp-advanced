# Apps Script Setup

This guide covers Apps Script support in `google-workspace-mcp-advanced`, including required API/scopes, supported tools, and known runtime limitations.

## Scope

Apps Script v1 support includes:
- Project read: metadata/content/versions
- Deployment read and mutation
- Process and metrics read
- Safe-by-default mutators (`dry_run=True`)
- Drive-backed standalone script listing/deletion

## Prerequisites

1. Enable Google Apps Script API (`script.googleapis.com`) in the Google Cloud project used by your OAuth client.
2. Authenticate with a user who has access to the target script projects.
3. Keep runtime configuration on the canonical path:
   - `WORKSPACE_MCP_CONFIG_DIR=~/.config/google-workspace-mcp-advanced`

## Required Scope Families

Apps Script tools rely on these scope aliases:
- `script_projects_read`
- `script_projects`
- `script_deployments_read`
- `script_deployments`
- `script_processes`
- `script_metrics`
- `drive_read` and `drive_file` (Drive-backed standalone script list/delete)

## Tool Surface

Read tools:
- `get_script_project`
- `list_script_projects` (Drive-backed standalone scripts only)
- `get_script_content`
- `list_deployments`
- `list_versions`
- `get_version`
- `list_script_processes`
- `get_script_metrics`

Mutating tools (all default `dry_run=True`):
- `create_script_project`
- `update_script_content`
- `create_version`
- `create_deployment` (requires `version_number >= 1`)
- `update_deployment`
- `delete_deployment`
- `delete_script_project` (Drive-backed standalone script file trash)
- `run_script_function`

## Known Limitations

1. `list_script_projects` and `delete_script_project` are Drive-backed and affect only standalone script files (`application/vnd.google-apps.script`), not container-bound scripts.
2. `create_deployment` requires an explicit non-zero `version_number`; create a version first when needed.
3. `run_script_function` depends on script runtime/deployment readiness in Google Apps Script. A 404 from `scripts.run` can occur for scripts that are not execution-ready in the target environment.
4. Apps Script execution can return 403 when the active OAuth client does not match the script/deployment runtime project context. In multi-client mode, map script IDs/deployment IDs via `script_clients` in `auth_clients.json`.
5. Cross-project execution UX hardening is intentionally deferred as `APPS-07` (non-blocking). Current support remains functional, but broad multi-script onboarding/diagnostics improvements are paused until explicit roadmap pull-forward.

## Safety Model

1. All mutators above default to `dry_run=True`.
2. Real mutation requires explicit `dry_run=False`.
3. Prefer running `dry_run` first, then mutation, then cleanup verification.

## Convex-First Validation Note

Apps Script rollout validation is currently executed in Convex-hosted MCP flows (not OpenCode-host subprocess validation). Historical OpenCode evidence remains archived for earlier tracks.

## Deferred Backlog (APPS-07)

Current state:
- Deferred by product decision; not a release blocker.

Deferred scope:
- Cross-project `run_script_function` UX hardening (`deployment_id` operator override, execution preflight diagnostics, and scalable client-mapping onboarding for many scripts).

Resume trigger:
- Re-open only when explicitly pulled forward in roadmap planning.

## Troubleshooting

`SERVICE_DISABLED` from Script API:
- Ensure `script.googleapis.com` is enabled for the OAuth client project used in this session.

`Requested entity was not found` on `run_script_function`:
- Verify script visibility for the authenticated user.
- Verify deployment/version readiness.
- Retry with a known-good existing script before treating as code regression.

`PERMISSION_DENIED` on `run_script_function`:
- Confirm the target script/deployment is mapped to the intended OAuth client under `script_clients` in `auth_clients.json`.
- Re-authenticate after mapping changes.
- Retry with the deployment ID path (`dev_mode=False`) and then owner test (`dev_mode=True`).
- If this pattern affects many independent scripts/projects, track the batch-onboarding/diagnostics enhancement under deferred item `APPS-07`.

OAuth appears to re-prompt unexpectedly:
- Confirm `WORKSPACE_MCP_CONFIG_DIR` points to `~/.config/google-workspace-mcp-advanced`.
- Confirm script/account/domain mappings in `auth_clients.json` when using multi-client mode.
