# Project Context

> This file provides shared context for all Ralphus agents.
> Fill in the sections below to help agents understand your project.

## Ralphus Structure

**CRITICAL**: All Ralphus files live under `ralph-wiggum/`:
- `ralph-wiggum/specs/` - Technical specifications
- `ralph-wiggum/prds/` - Product requirement docs
- `ralph-wiggum/memory/` - Shared context (this file)
- `ralph-wiggum/[variant]/` - Variant workspaces

**NEVER** create `specs/`, `prds/`, or `inbox/` at the project root.

## Project Overview

**gws-mcp-advanced** is a Model Context Protocol (MCP) server that connects AI assistants (like Claude) to Google Workspace. It enables AI to read/write Emails, Docs, Sheets, Calendar events, and more.

**Key capabilities:**
- **Markdown-to-Docs:** Convert Markdown directly to native Google Docs formatting
- **Bidirectional Sync:** Sync local files with Google Drive
- **Search Aliases:** Smart caching of search results (A-Z aliases)

## Tech Stack

- **Language:** Python 3.11+
- **Package Manager:** `uv`
- **Framework:** `fastmcp` (MCP implementation)
- **Google SDK:** `google-api-python-client`
- **Formatting:** `ruff`
- **Testing:** `pytest`
- **Markdown Parser:** `markdown-it-py`

## Architecture

**Three-Layer Architecture:**
1.  **Tool Layer (`*/tools.py`)**: Interface exposed to AI. Handles input/output.
2.  **Logic Layer (`core/managers.py`, `gdocs/markdown_parser.py`)**: Business logic, state management.
3.  **SDK Layer (`auth/`)**: Raw Google API interactions, authentication.

**Key Patterns:**
- **Two-Phase Reverse Styling:** For Google Docs `batchUpdate`, always insert text first, then apply styles in reverse order to prevent index shifts.
- **Dry Run Default:** All mutation tools default to `dry_run=True`.
- **Async Only:** All operations must be non-blocking.

## Development Workflow

1.  **Specs First:** Create `ralph-wiggum/specs/FEATURE.md`.
2.  **Debug/Trace:** Use small scripts to verify API behavior (see `specs/FIX_STYLE_BLEED.md`).
3.  **Implement:** Code changes.
4.  **Verify:** Run `uv run pytest` and manual E2E tests.

## Conventions

- **Logging:** Use `logging.getLogger(__name__)`.
- **Error Handling:** Decorate tools with `@handle_http_errors`.
- **Auth:** Decorate tools with `@require_google_service`.

## Key Files

- `main.py`: Entry point.
- `gdocs/markdown_parser.py`: Core logic for Markdown conversion.
- `docs/MCP_PATTERNS.md`: Standard patterns for tools.
- `TESTING_PLAN_MARKDOWN.md`: Current status of Markdown feature.
