# Agent Operational Guide (AGENTS.md)

## 1. PROJECT OVERVIEW

**gws-mcp-advanced** - High-performance MCP server for Google Workspace integration.
Provides 50+ async tools for Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides, Tasks, and Search.

## 2. DEV STANDARDS (STRICT)

**Role:** Senior Python Engineer. **Manager:** User (Architect).
**Goal:** Production-Ready, Type-Safe, Modular MCP Tools.

### 🛑 HARD CONSTRAINTS
1.  **NO SPEC = NO CODE:** Demand `SPEC.md` or a clear plan before implementation.
2.  **ZERO TOLERANCE:** No lint errors (`ruff`). No type errors. No failing tests (`pytest`).
3.  **DRY RUN DEFAULT:** All tools modifying Google Workspace MUST default to `dry_run=True`.
4.  **ASYNC ONLY:** All MCP tools must be `async`. Wrap blocking SDK calls in `asyncio.to_thread()`.
5.  **SAFETY:** Use `@require_google_service` and `@handle_http_errors` decorators on all tools.
6.  **ATOMICITY:** One tool or feature per implementation. No scope creep.
7.  **EXPLICIT ACTION:** Only answer questions or write code when specifically requested by the User. NO proactive execution without explicit "Go" or task assignment.

### 📚 RULE ACTIVATION
*You must strictly apply the following rules based on the task:*
- **All Tasks:** `rules/architecture.md`, `rules/workflow.md`
- **Python Logic:** `rules/rules_python.md`, `rules/logging.md`
- **Google API/Security:** `rules/api_design.md`, `rules/security.md`
- **Documentation:** `rules/documentation.md`

### 🏗 ARCHITECTURE (3-LAYER)
1.  **Presentation (Tool Layer):** `*/tools.py`. FastMCP decorators, input validation, output formatting.
2.  **Service (Logic Layer):** `core/managers.py` or domain logic. Business rules, sync algorithms.
3.  **Data (SDK Layer):** `auth/service_decorator.py` and raw Google API calls.
*Use Pydantic models for all complex data structures (DTOs).*

### 🔄 WORKFLOW LOOP
1.  **READ:** Analyze existing `docs/MCP_PATTERNS.md` and `docs/PYTHON_CONVENTIONS.md`.
2.  **PLAN:** Use `update_plan` to define steps and self-verification strategy.
3.  **TDD:** If applicable, add a test case in `tests/`.
4.  **CODE:** Implement using `uv` for dependencies and `ruff` for formatting.
5.  **VERIFY:** Run the Verification Protocol below.

## 3. VERIFICATION PROTOCOL (DEFINITION OF DONE)

Before marking a task as complete, run these commands in order:

1. `uv run ruff check .` - Must return no errors.
2. `uv run ruff format .` - Must not modify files.
3. `uv run pytest` - Must pass all tests.

> ⚠️ **MCP TESTING REMINDER:** Before testing any MCP tool changes via OpenCode, remind the user to restart OpenCode. The MCP server runs as a subprocess and won't pick up code changes until OpenCode is restarted.

## 4. QUICK REFERENCE

| Task          | Command                                       |
| ------------- | --------------------------------------------- |
| Install       | `uv pip install -e ".[dev]"`                  |
| Run server    | `python main.py`                              |
| Lint + format | `uv run ruff check . && uv run ruff format .` |

> **Code changes**: Restart the MCP server to pick up changes (Ctrl+C, then re-run).

## 5. ENVIRONMENT & SECURITY

- `USER_GOOGLE_EMAIL`: Target Google account email (Required).
- `WORKSPACE_MCP_CONFIG_DIR`: Credentials directory (default: `~/.config/google-workspace-mcp`).
- **Never** hardcode secrets. **Never** log OAuth tokens. **Never** log PII (emails/content) in production.
