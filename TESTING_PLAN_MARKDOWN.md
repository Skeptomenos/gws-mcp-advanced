# Testing Plan: Google Docs Markdown Formatting

## Metadata
- Last Updated (UTC): 2026-03-01T21:00:38Z
- Canonical Matrix: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`
- Canonical Plan: `/Users/david.helmus/repos/ai-dev/_infra/gws-mcp-advanced/gws-mcp-advanced/agent-docs/roadmap/PLAN.md`

## Current Result Snapshot

| Area | Status | Evidence |
|---|---|---|
| Markdown roadmap regressions (`RM-01`..`RM-04`) | PASS | OP-67, OP-68, OP-69 are all PASS in OpenCode manual matrix |
| Full manual matrix | PASS with product deferral | 80 PASS, 0 FAIL, 1 BLOCKED (`OP-06` deferred) |
| Defects | Closed | 12 found, 12 fixed |

## Verified Coverage
1. Typography, headings, lists, links, inline code, blockquotes.
2. Table generation and two-phase table population reliability.
3. Task-list transition behavior (no trailing empty bullet artifact).
4. Code block visual parity (language label + fenced content stability).
5. Markdown image rendering in create-doc flow.

## Important Validation Constraint
1. `inspect_doc_structure` does not reliably surface inline image objects for OP-69 verification.
2. Image validation is therefore visual-first in Google Docs, with text-flow confirmation as secondary evidence.

## Execution Source of Truth
1. Runbook and test IDs: `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`
2. Local quality gate:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run pytest -q`
3. Current local baseline: `598 passed, 3 skipped`.

## Open Items
1. No open markdown regression defects remain.
2. Product-deferred item remains outside this plan:
   - `OP-06` (`search_custom`, PSE env setup).

## Historical Note
This file previously tracked an early 2026-02-03 state with open markdown failures.
Those failures are now superseded by the canonical manual matrix and current verification snapshots.
