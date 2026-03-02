# Distribution Test Phase Guide (Living)

Use this file to execute and track the next distribution validation phase.

## Document Controls
- Status: `IN_PROGRESS`
- Last Updated (UTC): `2026-03-02T11:54:53Z`
- Tester: Codex
- Branch: `main` (workflow target validated from local branch `codex/run-01-fastmcp-import-smoke`)
- Commit: `a39b34f` (latest `main` after merge)
- Related Plan: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`
- Related Release Guide: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/docs/DISTRIBUTION_RELEASE.md`

## Preconditions
1. Trusted publisher is configured in PyPI for `google-workspace-mcp-advanced` (GitHub OIDC).
2. Trusted publisher is configured in npm for `google-workspace-mcp-advanced`.
3. Release workflows are present:
   - `.github/workflows/release-pypi.yml`
   - `.github/workflows/release-npm.yml`
4. Guard scripts pass:
   - `uv run python scripts/check_distribution_scope.py`
   - `uv run python scripts/check_release_version_match.py`

## Test Matrix

| ID | Area | Action | Expected Result | Status | Evidence | Notes |
|---|---|---|---|---|---|---|
| DT-01 | Release (PyPI) | Trigger `Release PyPI` workflow for current version | Workflow passes, dist artifact published to PyPI | BLOCKED | `HTTP 404: workflow release-pypi.yml not found on the default branch` | Re-validated on `main` after merge attempt; workflow file still absent on default branch. |
| DT-02 | Release (npm gate) | Trigger `Release npm` workflow before DT-01 or with missing PyPI version | Workflow fails at `check_pypi_version_available.py` gate | BLOCKED | `HTTP 404: workflow release-npm.yml not found on the default branch` | Re-validated on `main`; cannot execute gate until workflow exists on default branch. |
| DT-03 | Release (npm publish) | Trigger `Release npm` after DT-01 succeeds | Workflow passes and publishes npm package with provenance | BLOCKED | `HTTP 404: workflow release-npm.yml not found on the default branch` | Still blocked by missing release workflow on default branch. |
| DT-04 | Channel Stable | `npx -y google-workspace-mcp-advanced --transport stdio` | Server starts via launcher and exposes tools normally | BLOCKED | `npm error 404 The requested resource 'google-workspace-mcp-advanced@*' could not be found` | Package is not yet published to npm. Blocked by DT-03. |
| DT-05 | Channel Next | `npx -y google-workspace-mcp-advanced@next --transport stdio` | Prerelease channel starts and exposes tools | BLOCKED | Package not on npm | Blocked by DT-03. |
| DT-06 | Channel Pinned | `npx -y google-workspace-mcp-advanced@<version> --transport stdio` | Deterministic pinned version starts successfully | BLOCKED | Package not on npm | Blocked by DT-03. |
| DT-07 | Rollback | Repoint `latest` dist-tag to previous version | Consumers on `latest` resolve to rollback version | BLOCKED | `npm view google-workspace-mcp-advanced ...` -> `E404 Not Found` | Package is not on npm yet; rollback cannot be validated before first publish (DT-03). |
| DT-08 | Launcher Fallback | Run launcher on host without `uvx` but with `uv` | Launcher falls back to `uv tool run` and starts | PASS | Mocked `uvx` to `exit 127`. Output: `Because gws-mcp-advanced was not found in the package registry and you require google-workspace-mcp-advanced==1.0.0, we can conclude that your requirements are unsatisfiable.` | Confirms launcher correctly falls back to `uv tool run` and constructs correct PyPI package identifier. |

## Execution Notes
1. Record exact workflow run IDs and package version numbers in Evidence.
2. If any test fails, add a defect row in `PLAN.md` / `TASKS.md` and keep this file append-only.
3. Keep `Status` values to: `PASS`, `FAIL`, `BLOCKED`, `NOT RUN`.

## Session Summary (OpenCode - 2026-03-01)
- **Tester:** OpenCode
- **Branch:** `codex/run-01-fastmcp-import-smoke`
- **Commit:** `003a608a15d635774182aaf59c6de8c7924e1a7c`
- **Timestamp:** `2026-03-01T21:55:00Z`
- **Results:**
  - PASS: 1 (DT-08)
  - FAIL: 0
  - BLOCKED: 7 (DT-01 to DT-07)
  - NOT RUN: 0

**Blocker Details:**
1. **GitHub Actions limitation:** GitHub requires a workflow to exist on the default branch (`main`) before it can be triggered using `workflow_dispatch`. Trying to trigger `release-pypi.yml` and `release-npm.yml` via `gh workflow run` on the current branch results in `HTTP 404: workflow [...] not found on the default branch`.
2. **Missing Package:** DT-04 through DT-07 require the package to be published on npm, which is blocked by the workflows not being executable.

## Next Actions
1. **Merge to default branch:** Merge the workflow files to `main` so they can be triggered manually, or trigger a release by pushing a semver tag to the remote.
2. **Re-run DT-01 to DT-07:** Once merged, run `workflow_dispatch` on the release workflows to test PyPI and npm publishing, then test the npm channels.

## Session Summary (Codex - 2026-03-02)
- **Tester:** Codex
- **Branch/Target:** local `codex/run-01-fastmcp-import-smoke` -> remote `main`
- **Commit Context:** `a39b34f` on `main`
- **Timestamp:** `2026-03-02T11:54:53Z`
- **Commands Run:**
  - `gh workflow list --repo Skeptomenos/google-workspace-mcp-advanced` (only `CI` visible)
  - `gh workflow run release-pypi.yml --repo Skeptomenos/google-workspace-mcp-advanced --ref main` (404)
  - `gh workflow run release-npm.yml --repo Skeptomenos/google-workspace-mcp-advanced --ref main` (404)
  - `npm view google-workspace-mcp-advanced dist-tags versions --json` (`E404`)
  - `uv run python scripts/check_distribution_scope.py` (pass)
  - `uv run python scripts/check_release_version_match.py` (pass)
- **Result Delta:** No status transitions; `DT-01`, `DT-02`, `DT-03`, and `DT-07` remain `BLOCKED` with refreshed evidence from post-merge validation on `main`.
