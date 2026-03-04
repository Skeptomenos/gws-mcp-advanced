# Product Roadmap

## Metadata
- Last Updated (UTC): 2026-03-03T14:27:00Z
- Canonical Execution Plan: `agent-docs/roadmap/PLAN.md`
- Canonical Manual Matrix: `agent-docs/testing/OPENCODE_MCP_MANUAL_TESTING.md`

## Current State

### Completed Roadmap Closures (Wave 3)
1. `RM-01` Code-block rendering parity: complete.
   - Evidence: OpenCode `OP-68` PASS.
2. `RM-02` Table reliability: complete.
   - Evidence: multi-table and preceding-content integration regressions plus manual extended-matrix PASS.
3. `RM-03` Task-list trailing bullet regression: complete.
   - Evidence: OpenCode `OP-67` PASS.
4. `RM-04` Markdown image rendering regression: complete.
   - Evidence: OpenCode `OP-69` PASS (visual confirmation).
   - Note: `inspect_doc_structure` does not surface inline image objects reliably for this scenario; visual verification is authoritative for image presence.

### Deferred Platform Item (Non-Blocking)
1. Programmable Search Engine (`search_custom`) enablement.
   - Status: Deferred by product decision.
   - Scope: `GOOGLE_PSE_API_KEY` + `GOOGLE_PSE_ENGINE_ID`.
   - Reason: web-search coverage currently provided by other MCPs.
   - Revisit trigger: when unified web-search routing through this MCP becomes a product requirement.

## Next Roadmap Focus
1. Apps Script v1 execution (Wave 7, active):
   - `APPS-01`: foundation (`gappsscript` package, service wiring, first read tool: `get_script_project`)
   - APPS gate after `APPS-01`: targeted tests + full verification (`ruff`, `format --check`, `pyright`, `pytest`) + existing-feature regression checklist
   - `APPS-02`: Drive-backed standalone script list/delete with explicit container-bound limitation messaging
   - `APPS-05` (early policy gate): least-privilege scope lock and mixed-service auth coverage before broad surface expansion
   - `APPS-03`: remaining read surface + strict filter DTO validation
   - `APPS-04`: mutating surface with `dry_run=True` defaults and runtime dry-run contract tests
   - `APPS-06`: docs/manual matrix/release notes closeout
2. Smart-chip extension stream (`RM-05`..`RM-07`) after Wave 7 closure:
   - Native checklist bullets
   - Mention-to-chip mapping
   - Add-ons-backed third-party chips feasibility

## Closure Notes
1. Markdown formatting is no longer an active roadmap risk area.
2. Historical design exploration for markdown parsing is preserved in commit history and specs; this roadmap now tracks only forward-looking work.
