# Apps Script User Guide

This guide explains what the Apps Script features in this MCP can do, how they work together, and how to use them safely in real workflows.

If you develop locally with `clasp`, also read:
- `docs/setup/APPS_SCRIPT_CLASP_GUIDE.md`

## What You Can Do

With the Apps Script tools, you can:
- Discover and inspect script projects.
- Read and update script source files (`.gs`, HTML, and `appsscript.json`).
- Manage versions and deployments.
- Run script functions through the Apps Script Execution API.
- Inspect runtime processes and usage metrics.
- Work safely with dry-run defaults for mutating operations.

## Core Concepts

- `script_id`: The Apps Script project identifier.
- Version: Immutable snapshot created with `create_version`.
- Deployment: Published target created/updated with `create_deployment` and `update_deployment`.
- `dev_mode` execution:
  - `True`: executes against latest code for owner-style testing.
  - `False`: executes deployed code path (the tool resolves an Execution API deployment when possible).
- Standalone vs container-bound:
  - `list_script_projects` and `delete_script_project` are Drive-backed and only work for standalone script files.
  - Container-bound scripts are intentionally excluded from those two tools.

## Tool Map

### Project Discovery and Read

- `get_script_project`: project metadata.
- `list_script_projects`: list standalone script projects from Drive.
- `get_script_content`: read project files, optionally pinned to a version.
- `list_versions`: list saved versions.
- `get_version`: inspect one version.
- `list_deployments`: list deployments.

### Operations and Runtime Insight

- `list_script_processes`: list script or user process history.
- `get_script_metrics`: retrieve metrics (`DAILY` or `WEEKLY` granularity).

### Mutating Tools (all default `dry_run=True`)

- `create_script_project`
- `update_script_content`
- `create_version`
- `create_deployment`
- `update_deployment`
- `delete_deployment`
- `delete_script_project` (standalone scripts only)
- `run_script_function`

## Safety Model (Important)

All mutating tools default to preview mode:
- `dry_run=True` shows what would happen.
- `dry_run=False` performs the real API call.

Recommended pattern:
1. Run dry-run first.
2. Confirm target IDs and payload shape.
3. Run with `dry_run=False`.
4. Verify outcome with a read tool.

## Common Workflows

## 1) Inspect an Existing Script

1. `get_script_project` to confirm identity and ownership context.
2. `get_script_content` to inspect files.
3. `list_versions` and `list_deployments` to understand release state.

## 2) Update Script Code Safely

1. Build `files_json` as a JSON list of objects with required keys:
   - `name`
   - `type`
   - `source`
2. Run `update_script_content` with `dry_run=True`.
3. Re-run with `dry_run=False`.
4. Verify with `get_script_content`.

Example `files_json` structure:

```json
[
  {
    "name": "Code",
    "type": "SERVER_JS",
    "source": "function hello(name) { return `Hello ${name}`; }"
  },
  {
    "name": "appsscript",
    "type": "JSON",
    "source": "{\"timeZone\":\"Europe/Berlin\",\"executionApi\":{\"access\":\"MYSELF\"}}"
  }
]
```

## 3) Create a Version and Deployment

1. `create_version` after content updates.
2. `create_deployment` using `version_number` from step 1.
3. `list_deployments` to confirm.

Notes:
- `create_deployment` requires `version_number >= 1`.
- `update_deployment` requires `description` and can optionally move to a new version.

## 4) Execute a Function

1. Verify function exists in script source.
2. Use `run_script_function`:
   - `parameters_json` must be a JSON list (or omitted).
   - start with `dry_run=True`.
3. For owner/debug path use `dev_mode=True`.
4. For deployment path use `dev_mode=False`.

If execution fails with precondition guidance, follow it in order:
1. Ensure `executionApi.access` is configured in `appsscript.json` (commonly `MYSELF`).
2. Create a new version/deployment after updates.
3. Run once from Apps Script editor to complete consent.
4. Retry.

## 5) Monitor Runtime and Usage

1. `list_script_processes` for function/process history.
2. `get_script_metrics` for usage/cost insight windows.

Process filter inputs are strict JSON objects:
- `script_process_filter_json`
- `user_process_filter_json`

Metrics filter input:
- `metrics_filter_json`

These filter payloads are validated; unknown keys and invalid enum values are rejected with actionable errors.

## Input Contracts You Should Know

## `parameters_json` (run execution)

- Type: JSON list
- Example:

```json
["alice", 3, true]
```

## `files_json` (update content)

- Type: JSON list of objects
- Required keys in each object:
  - `name`
  - `type`
  - `source`

## Process and metrics filters

- Type: JSON object
- Must follow documented schema/enums (validated by the server).

## Authentication and Routing

Apps Script tools run under the active OAuth client for the session.

In multi-client mode you can route specific scripts/deployments to a specific client with `script_clients` in `auth_clients.json`.

Resolution precedence is:
1. explicit override (internal/admin path),
2. script mapping (`script_clients`),
3. account mapping,
4. domain mapping,
5. default client.

If you change mappings, re-authenticate and retry.

## Known Limitations

- Drive-backed list/delete only cover standalone scripts.
- Execution can return:
  - `404` when script/deployment is not execution-ready,
  - `403` for permission/project-alignment issues.
- Cross-project execution UX hardening is deferred as `APPS-07` (non-blocking), so large-scale multi-script onboarding still requires explicit mapping discipline today.

## Recommended Best Practices

1. Keep `appsscript.json` under source control and validate `executionApi` settings early.
2. Use `dry_run=True` first for every mutator.
3. Version before deployment, deploy before non-dev execution.
4. Keep script/deployment IDs in your release notes.
5. Use `list_script_processes` after rollout to confirm real runtime behavior.
6. For multi-client setups, maintain `script_clients` mappings as part of release ops.

## Related Docs

- Setup and constraints: `docs/setup/APPS_SCRIPT_SETUP.md`
- Apps Script + clasp workflows: `docs/setup/APPS_SCRIPT_CLASP_GUIDE.md`
- Multi-client auth routing: `docs/setup/MULTI_CLIENT_AUTH_SETUP.md`
- Auth model details: `docs/setup/AUTHENTICATION_MODEL.md`
