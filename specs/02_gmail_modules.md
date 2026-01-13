# Refactor Spec 02: Gmail Modularization

**Objective**: Split the Gmail tools from `gmail/gmail_tools.py` into domain-specific modules and use `__init__.py` as a facade.

**Prerequisites**: Spec 01 (Helpers) must be complete.

## 1. Target Structure
Create the following files in `gmail/`:
- `search.py`: `search_gmail_messages`
- `messages.py`: `get_gmail_message_content`, `get_gmail_messages_content_batch`, `send_gmail_message`, `draft_gmail_message`, `get_gmail_attachment_content`
- `threads.py`: `get_gmail_thread_content`, `get_gmail_threads_content_batch`
- `labels.py`: `list_gmail_labels`, `manage_gmail_label`, `modify_gmail_message_labels`, `batch_modify_gmail_message_labels`
- `filters.py`: `list_gmail_filters`, `create_gmail_filter`, `delete_gmail_filter`

## 2. Implementation Steps

### A. Create Modules
For each new file above:
1. Move the relevant `@server.tool` functions from `gmail_tools.py`.
2. Add necessary imports (including `from core.server import server` and `from .helpers import ...`).

### B. Update `gmail/__init__.py`
1. Create/Update `gmail/__init__.py` to re-export all tools.
   ```python
   from .search import search_gmail_messages
   from .messages import get_gmail_message_content, ...
   # ... repeat for all
   ```
   *Goal*: `from gmail import search_gmail_messages` should still work.

### C. Clean up `gmail/gmail_tools.py`
1. It should be empty or nearly empty.
2. If `main.py` imports directly from `gmail.gmail_tools`, update `main.py` to import from `gmail` package instead.
3. Delete `gmail/gmail_tools.py` if no longer referenced.

## 3. Verification
1. Check imports: `uv run ruff check .`
2. Run server startup check: `python main.py --help` (ensures tools register).
3. Run tests: `uv run pytest tests/`

## 4. Rollback Plan
1. Restore `gmail/gmail_tools.py` from git.
2. Delete the new split files.
