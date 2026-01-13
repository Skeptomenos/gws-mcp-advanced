# Refactor Spec 01: Gmail Shared Logic Extraction

**Objective**: Extract internal helper functions from `gmail/gmail_tools.py` into a dedicated `gmail/helpers.py` module to prepare for modularization.

**Context**: 
`gmail/gmail_tools.py` is a 1600-line monolith containing both MCP tools (`@server.tool()`) and internal helper logic. To safely split the tools later, we first need to decouple the shared logic.

## 1. Analysis
Identify all functions in `gmail/gmail_tools.py` that start with `_` (underscore) AND are not tools.
*Expected candidates:*
- `_html_to_text`
- `_extract_message_body`
- `_extract_message_bodies`
- `_format_body_content`
- `_extract_attachments`
- `_extract_headers`
- `_prepare_gmail_message`
- `_generate_gmail_web_url`
- `_format_gmail_results_plain`
- `_format_thread_content`

## 2. Implementation Steps

### A. Create `gmail/helpers.py`
1. Create new file `gmail/helpers.py`.
2. Move all identified helper functions from `gmail_tools.py` to `helpers.py`.
3. Copy necessary imports (e.g., `BeautifulSoup`, `base64`, `re`, `html`) to `helpers.py`.

### B. Update `gmail/gmail_tools.py`
1. Remove the helper function definitions.
2. Add imports at the top: `from .helpers import (...)`.
3. Ensure no `@server.tool` decorated functions were moved.

## 3. Verification
1. Run linting: `uv run ruff check gmail/`
2. Run tests: `uv run pytest tests/`
   *Crucial*: Since we only moved internal logic, ALL existing tests must pass without modification.

## 4. Rollback Plan
If tests fail:
1. Delete `gmail/helpers.py`.
2. Revert changes to `gmail/gmail_tools.py` using git.
