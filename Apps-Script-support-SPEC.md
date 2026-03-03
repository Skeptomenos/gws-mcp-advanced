# Apps Script Support Spec

Status: Draft (Ready for implementation slicing)  
Date: 2026-03-02  
Owner: Platform (MCP)  
Related: `AGENTS.md`, `agent-docs/architecture/MCP_PATTERNS.md`, `agent-docs/architecture/PYTHON_CONVENTIONS.md`

## 1. Problem Statement

`gws-mcp-advanced` currently has no Google Apps Script MCP surface.  
This blocks common automation workflows and prevents direct interoperability with existing Apps Script projects and `clasp`-based development loops.

We need production-grade Apps Script support that matches our repo standards:
- async-only tools
- decorator safety model
- mutating operations default to `dry_run=True`
- strong test and quality gates

## 2. Goals

1. Add first-class Apps Script MCP tools for read, write, execution, deployment, versioning, and metrics.
2. Keep architecture modular and testable (tool layer + service layer + SDK layer).
3. Preserve safety defaults (`dry_run=True`) for all mutating operations.
4. Enable practical `clasp` workflows by exposing script/project IDs and deterministic file payload formats.

## 3. Non-Goals (Initial Scope)

1. Full `clasp` CLI orchestration from MCP server (running shell commands inside tool handlers).
2. Trigger CRUD via Apps Script API (Google API limitations; we only generate helper code).
3. Building a complete local filesystem sync engine in v1.

## 4. User Personas and Workflows

## 4.1 Automation Engineer
- Discover script projects.
- Inspect source files.
- Update code safely (`dry_run` preview first).
- Deploy new version and run a function.

## 4.2 Agent + `clasp` Workflow
- Create or locate script project from MCP.
- Use returned `script_id` with local `clasp clone/push/pull`.
- Use MCP tools for review, metrics, and controlled deployment.

## 5. Functional Scope (v1)

### 5.1 Read tools
1. `list_script_projects`
2. `get_script_project`
3. `get_script_content`
4. `list_deployments`
5. `list_versions`
6. `get_version`
7. `list_script_processes`
8. `get_script_metrics`
9. `generate_trigger_code` (read-only utility)

### 5.2 Mutating tools (all must default `dry_run=True`)
1. `create_script_project`
2. `update_script_content`
3. `delete_script_project`
4. `create_deployment`
5. `update_deployment`
6. `delete_deployment`
7. `create_version`
8. `run_script_function` (considered mutating because executed code can modify data)

## 6. Architecture and File Layout

New package:
- `gappsscript/`
- `gappsscript/__init__.py`
- `gappsscript/apps_script_tools.py` (presentation/tool layer)
- `gappsscript/apps_script_manager.py` (service/business layer)
- Optional helpers: `gappsscript/models.py` (Pydantic DTOs)

Existing files to update:
- `main.py` (add `appscript` service option for `--tools`)
- `auth/scopes.py` (script scopes + service mapping)
- `auth/service_decorator.py` (scope aliases)
- `core/tool_tiers.yaml` (tier placement)
- `README.md` (tool docs + examples)
- tests under `tests/unit/...`

Design rule:
- Tool functions stay thin (validation + formatting).
- API calls and business rules move to manager layer.

## 7. Tool Contracts (Initial Signatures)

All tools must be `async`, wrapped in:
- `@server.tool()`
- `@handle_http_errors(...)`
- `@require_google_service(...)` (or `@require_multiple_services` when needed)

### 7.1 Read tools

```python
async def list_script_projects(
    service,
    user_google_email: str,
    page_size: int = 50,
    page_token: str | None = None,
) -> str: ...

async def get_script_project(
    service,
    user_google_email: str,
    script_id: str,
) -> str: ...

async def get_script_content(
    service,
    user_google_email: str,
    script_id: str,
    file_name: str,
) -> str: ...

async def list_deployments(
    service,
    user_google_email: str,
    script_id: str,
) -> str: ...

async def list_versions(
    service,
    user_google_email: str,
    script_id: str,
) -> str: ...

async def get_version(
    service,
    user_google_email: str,
    script_id: str,
    version_number: int,
) -> str: ...

async def list_script_processes(
    service,
    user_google_email: str,
    page_size: int = 50,
    script_id: str | None = None,
) -> str: ...

async def get_script_metrics(
    service,
    user_google_email: str,
    script_id: str,
    metrics_granularity: str = "DAILY",
) -> str: ...

async def generate_trigger_code(
    trigger_type: str,
    function_name: str,
    schedule: str = "",
) -> str: ...
```

### 7.2 Mutating tools (must include `dry_run: bool = True`)

```python
async def create_script_project(
    service,
    user_google_email: str,
    title: str,
    parent_id: str | None = None,
    dry_run: bool = True,
) -> str: ...

async def update_script_content(
    service,
    user_google_email: str,
    script_id: str,
    files_json: str,  # JSON list to avoid anyOf schema issues
    dry_run: bool = True,
) -> str: ...

async def delete_script_project(
    service,
    user_google_email: str,
    script_id: str,
    dry_run: bool = True,
) -> str: ...

async def create_deployment(
    service,
    user_google_email: str,
    script_id: str,
    description: str,
    version_description: str | None = None,
    dry_run: bool = True,
) -> str: ...

async def update_deployment(
    service,
    user_google_email: str,
    script_id: str,
    deployment_id: str,
    description: str,
    dry_run: bool = True,
) -> str: ...

async def delete_deployment(
    service,
    user_google_email: str,
    script_id: str,
    deployment_id: str,
    dry_run: bool = True,
) -> str: ...

async def create_version(
    service,
    user_google_email: str,
    script_id: str,
    description: str | None = None,
    dry_run: bool = True,
) -> str: ...

async def run_script_function(
    service,
    user_google_email: str,
    script_id: str,
    function_name: str,
    parameters_json: str | None = None,  # JSON list
    dev_mode: bool = False,
    dry_run: bool = True,
) -> str: ...
```

Notes:
- Keep complex params as JSON strings (`files_json`, `parameters_json`) to avoid `anyOf` schema issues.
- Parse and validate via Pydantic DTOs in manager layer.

## 8. Scope and Permission Model

Add scopes in `auth/scopes.py` and aliases in `auth/service_decorator.py`:
- `script_readonly`
- `script_projects`
- `script_deployments`
- `script_deployments_readonly`
- `script_processes_readonly`
- `script_metrics`

Mutating tools must request least-necessary write scope.
Read tools must use readonly scope where available.

## 9. Safety and Security Requirements

1. All mutators default `dry_run=True`.
2. Never log full script source or function parameters if they may contain secrets.
3. Validate `script_id`, `deployment_id`, and file names before API calls.
4. Reject empty/invalid payloads with actionable errors.
5. For `run_script_function`, surface API error payloads safely (no token leakage).
6. Add max payload guardrails for script update content (size and file count).

## 10. Reliability and Resilience Requirements

1. Wrap all blocking Google SDK calls in `asyncio.to_thread()`.
2. Use structured, deterministic response formatting.
3. Separate manager-layer pure logic where possible for unit tests.
4. Handle partial failures explicitly (for example, report which file updates failed).
5. Return stable IDs/links in success responses (`script_id`, deployment IDs, edit URL).

## 11. `clasp` Alignment Plan

v1 alignment (no direct `clasp` execution):
1. Ensure responses always include `script_id`.
2. Standardize file payload structure compatible with `clasp` source concepts:
   - `{ "name": "Code", "type": "SERVER_JS", "source": "..." }`
   - `{ "name": "appsscript", "type": "JSON", "source": "{...}" }`
3. Add documentation snippets:
   - `clasp clone <script_id>`
   - `clasp pull`
   - `clasp push`

Future (v2 optional):
1. Add dedicated local sync tools (`pull_script_to_local`, `push_local_to_script`) with strict path allowlisting and `dry_run=True`.

## 12. Tool Tier Placement

Proposed `core/tool_tiers.yaml` entries:
- `appscript.core`:
  - `list_script_projects`
  - `get_script_project`
  - `get_script_content`
  - `create_script_project`
  - `update_script_content`
  - `run_script_function`
  - `generate_trigger_code`
- `appscript.extended`:
  - `create_deployment`
  - `update_deployment`
  - `delete_deployment`
  - `list_deployments`
  - `delete_script_project`
  - `list_versions`
  - `create_version`
  - `get_version`
  - `list_script_processes`
  - `get_script_metrics`
- `appscript.complete`: empty initially

## 13. Implementation Phases (Atomic PRs)

### Phase 0: Foundation
1. Add `gappsscript` package skeleton and imports.
2. Add scopes and service aliases.
3. Add `appscript` service option in `main.py`.
4. Add empty tier config.

### Phase 1: Read Surface
1. `list_script_projects`
2. `get_script_project`
3. `get_script_content`
4. `list_deployments`
5. `list_versions`
6. `get_version`
7. `list_script_processes`
8. `get_script_metrics`
9. `generate_trigger_code`

### Phase 2: Write Surface (safe by default)
1. `create_script_project`
2. `update_script_content`
3. `delete_script_project`
4. `create_version`
5. `create_deployment`
6. `update_deployment`
7. `delete_deployment`
8. `run_script_function`

### Phase 3: Docs and Examples
1. README tools table and examples.
2. `clasp` usage guidance section.

## 14. Test Strategy

Required:
1. Unit tests for each manager function (mock API service).
2. Tool wrapper tests for validation, decorator behavior, and dry-run message semantics.
3. Scope/permission tests for new `appscript` service selection.
4. Negative tests:
   - invalid JSON payloads
   - missing required IDs
   - invalid action/enum values
   - API errors propagated via `handle_http_errors`

Suggested structure:
- `tests/unit/gappsscript/test_apps_script_manager.py`
- `tests/unit/gappsscript/test_apps_script_tools.py`
- `tests/unit/auth/test_appscript_scopes.py`

## 15. Observability

Log format:
- include tool name, user email (already standard), target script/deployment IDs
- do not log full source content

Example safe logs:
- `[update_script_content] script_id=..., files=3, dry_run=True`
- `[run_script_function] script_id=..., function_name=..., dev_mode=False`

## 16. Acceptance Criteria (Definition of Done)

Functional:
1. All v1 tools available and discoverable through MCP.
2. Mutating tools default to `dry_run=True`.
3. Tool responses include actionable IDs/links.

Quality:
1. `uv run ruff check .` passes.
2. `uv run ruff format .` produces no diffs.
3. `uv run pytest` passes.
4. `uv run pyright --project pyrightconfig.json` passes.

Operational:
1. `main.py --tools appscript` loads successfully.
2. Tier filtering includes `appscript`.
3. README documents tool usage and `clasp` alignment.

## 17. Risks and Mitigations

1. Risk: Apps Script API behavior differences across standalone vs bound projects.  
   Mitigation: explicit validation and clear error messages; include examples for both.
2. Risk: Payload schema incompatibilities in MCP clients (`anyOf`).  
   Mitigation: JSON string params for complex lists/maps + strict parsing.
3. Risk: Hidden side effects from function execution.  
   Mitigation: `dry_run` preview by default + clear warnings in docs.
4. Risk: Scope overreach.  
   Mitigation: use readonly scopes for read tools; granular scope aliases.

## 18. Open Questions

1. Should `run_script_function` remain in core tier or move to extended due to side effects?
2. Should `generate_trigger_code` include templates for webapp deployment setup?
3. Do we want v1 to include optional `clasp` helper outputs (for example, generated `.clasp.json` stub)?

## 19. Immediate Next Step

Start Phase 0 with a single PR:
1. add scope aliases
2. add `appscript` service routing
3. add empty tool module + minimal read tool (`list_script_projects`)
4. add tests and pass all quality gates

