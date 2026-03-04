# Apps Script + clasp Guide

This guide shows how to use the MCP Apps Script features together with `clasp` in a clean workflow.

## What This Integration Gives You

Use MCP for:
- metadata, deployment, process, and metrics APIs,
- safe dry-run previews for mutating operations,
- execution diagnostics and structured error guidance.

Use `clasp` for:
- local file editing in your IDE,
- pull/push sync with Apps Script project files,
- developer-centric local workflow.

## Important Boundaries

- The MCP does not execute `clasp` commands for you.
- `clasp` is still run from your local shell.
- Standalone script listing/deletion in MCP is Drive-backed and excludes container-bound scripts.

## Prerequisites

1. Install `clasp`:

```bash
npm install -g @google/clasp
```

2. Log in with the same Google account used by MCP:

```bash
clasp login
```

3. Make sure Apps Script API is enabled for your OAuth client project used by MCP.

## Workflow A: Existing Script -> Local Dev -> Managed Release

1. Discover script in MCP:
   - `list_script_projects` (standalone scripts)
   - `get_script_project`
2. Clone locally with `clasp`:

```bash
clasp clone <SCRIPT_ID>
cd <cloned-directory>
clasp pull
```

3. Edit locally and push:

```bash
clasp push
```

4. Release using MCP tools:
   - `create_version` (dry-run, then real)
   - `create_deployment` (dry-run, then real)
   - `run_script_function` (`dev_mode=False` for deployment path)
5. Observe runtime:
   - `list_script_processes`
   - `get_script_metrics`

## Workflow B: MCP-Created Project -> Local clasp Loop

1. Create project via MCP:
   - `create_script_project` (`dry_run=True`, then `dry_run=False`)
2. Take returned `script_id` and clone:

```bash
clasp clone <SCRIPT_ID>
clasp pull
```

3. Continue local development with `clasp push`.
4. Use MCP for versioning, deployment, execution, and monitoring.

## Workflow C: Local-First with clasp, MCP for Ops

1. Use `clasp` as source loop for code:
   - `clasp pull`
   - edit
   - `clasp push`
2. Use MCP as ops/control plane:
   - verify content (`get_script_content`)
   - release (`create_version`, `create_deployment`, `update_deployment`)
   - validate execution (`run_script_function`)
   - inspect health (`list_script_processes`, `get_script_metrics`)

## Keeping MCP and clasp in Sync (Recommended Discipline)

1. Before local edits: run `clasp pull`.
2. After local edits: run `clasp push`.
3. If you changed code with MCP `update_script_content`: run `clasp pull` before next local edit.
4. If you changed code with `clasp push`: use `get_script_content` to verify server state before release steps.
5. Avoid mixed writes from two places at the same time.

## Mapping Local Files to MCP Payloads

When using MCP `update_script_content`, payload must be:
- JSON list of file objects
- each file includes:
  - `name`
  - `type`
  - `source`

Minimal example:

```json
[
  {
    "name": "Code",
    "type": "SERVER_JS",
    "source": "function ping(){return 'pong';}"
  },
  {
    "name": "appsscript",
    "type": "JSON",
    "source": "{\"timeZone\":\"Europe/Berlin\",\"executionApi\":{\"access\":\"MYSELF\"}}"
  }
]
```

## Deployment and Execution Pattern

Use this sequence consistently:
1. Update content (`clasp push` or MCP `update_script_content`).
2. `create_version`.
3. `create_deployment` or `update_deployment`.
4. `run_script_function`.
5. Inspect with process/metrics tools.

If execution fails:
- `404` usually means execution-readiness/version/deployment mismatch.
- `403` often indicates permission or OAuth client/script project alignment mismatch.

## Multi-Client Routing with clasp Projects

If using single-MCP multi-client auth:
- map script IDs/deployment IDs in `script_clients` inside `auth_clients.json`,
- re-authenticate after mapping changes,
- then rerun execution/deployment operations.

This is especially important when your local `clasp` projects span multiple tenants or Google Cloud OAuth clients.

## What to Use for What

- Use `clasp` when:
  - you want IDE-native local editing and project layout.
- Use MCP when:
  - you want controlled dry-run previews,
  - deployment/version lifecycle automation,
  - execution diagnostics and runtime observability.

## Related Docs

- Apps Script setup: `docs/setup/APPS_SCRIPT_SETUP.md`
- Apps Script feature guide: `docs/setup/APPS_SCRIPT_USER_GUIDE.md`
- Multi-client auth routing: `docs/setup/MULTI_CLIENT_AUTH_SETUP.md`
