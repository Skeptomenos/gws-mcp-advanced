# Spec: Adopt Drive Import Conversion as Markdown Fallback

**Goal:** Add a Taylor-style Google Drive import conversion path as a fallback for Markdown -> Google Doc formatting while keeping our parser pipeline as primary.

**Severity:** HIGH (reliability + user success on complex/edge markdown)
**Status:** Proposed
**Date:** 2026-03-02

## Why

Current behavior is parser-driven (`MarkdownToDocsConverter`) and highly controlled, but some markdown inputs can still fail due to index/structure edge cases.

Taylor’s approach uses Drive conversion (`files.create` with source MIME like `text/markdown`, target MIME `application/vnd.google-apps.document`) and is robust for "just import this content/file" workflows.

We should combine both:
- Primary: parser path (deterministic, testable, style fidelity control)
- Fallback: Drive conversion path (high success import path for difficult inputs)

## Scope

## In Scope (v1)

1. Add a new safe import tool:
   - `import_to_google_doc`
   - Supports `content`, local `file_path`, or `file_url`
   - Supports source format detection (`md`, `markdown`, `txt`, `html`, `docx`, `doc`, `rtf`, `odt`)
   - Defaults to `dry_run=True`

2. Add fallback behavior to `create_doc` only:
   - Parser remains default path
   - On parser failure (or explicit fallback mode), create doc via Drive import conversion

3. Add secure URL/file ingestion hardening to this flow:
   - local path allowlisting (`validate_file_path` / `ALLOWED_FILE_DIRS`)
   - SSRF-safe URL fetch for `file_url` inputs (host/IP validation + redirect checks)

4. Add tests and docs.

## Out of Scope (v1)

1. Fallback for `insert_markdown` (in-place update)  
   Reason: Drive conversion creates/replaces docs, not in-place range insert.
2. Automatic migration of existing docs from parser path to import path.
3. Changes to parser internals except integration hooks.

## Product/API Design

## New Tool: `import_to_google_doc`

Location:
- `gdrive/import_tools.py` (preferred) or `gdrive/files.py` (if minimal churn)

Decorator stack:
- `@server.tool()`
- `@handle_http_errors("import_to_google_doc", service_type="drive")`
- `@require_google_service("drive", "drive_file")`

Proposed signature:

```python
async def import_to_google_doc(
    service,
    user_google_email: str,
    file_name: str,
    content: str | None = None,
    file_path: str | None = None,
    file_url: str | None = None,
    source_format: str | None = None,
    folder_id: str = "root",
    dry_run: bool = True,
) -> str:
    ...
```

Rules:
1. Exactly one of `content`, `file_path`, `file_url` must be provided.
2. `dry_run=True` returns planned source format, target format, and folder resolution preview.
3. On execution:
   - detect/resolve source MIME
   - upload bytes via Drive API with target mimeType = Google Doc
4. Return `document_id`, `webViewLink`, source/target MIME summary.

## `create_doc` Fallback Controls

Update `gdocs/writing.py:create_doc` with new arg:

```python
fallback_mode: str = "on_error"  # "disabled" | "on_error" | "always"
```

Behavior:
1. `disabled`: current parser-only behavior.
2. `on_error` (default): try parser path; if conversion pipeline raises, fallback to import conversion path.
3. `always`: skip parser and import via Drive conversion directly.

Notes:
- `parse_markdown=False` keeps plain text insertion behavior and bypasses fallback.
- `dry_run=True` must clearly state which path would be used.

## Architecture

## New helper module (recommended)

`gdrive/import_conversion.py`:
- source format detection map
- content/path/url byte loading
- SSRF-safe fetch helper(s)
- Drive create conversion function

This keeps tool functions thin and reusable by:
- `import_to_google_doc`
- `create_doc` fallback branch

## Security Requirements

1. Mutations default `dry_run=True`.
2. Validate local paths with allowlist mechanism (`validate_file_path`).
3. For URLs:
   - allow only `http`/`https`
   - resolve DNS and reject private/internal IP ranges
   - verify redirect chains with same controls
4. No token/secret leakage in logs.
5. Limit payload size for `content` and fetched file bytes (configurable threshold).

## Reliability/Resilience Requirements

1. All Google SDK calls wrapped in `asyncio.to_thread()`.
2. Fallback path only triggers on typed conversion failures (no silent swallow of programming errors).
3. Responses explicitly indicate path used: `parser` vs `drive_import_fallback`.
4. Preserve deterministic behavior under `dry_run`.

## MIME Detection

Target MIME (always):
- `application/vnd.google-apps.document`

Source format map:
- `.md`, `.markdown` -> `text/markdown`
- `.txt`, `.text` -> `text/plain`
- `.html`, `.htm` -> `text/html`
- `.docx` -> `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `.doc` -> `application/msword`
- `.rtf` -> `application/rtf`
- `.odt` -> `application/vnd.oasis.opendocument.text`

Unknown:
- fallback to `text/plain`

## Testing Plan

## Unit

1. Source selection validation (exactly one source input).
2. MIME detection by extension and explicit `source_format`.
3. `dry_run` outputs for tool + `create_doc` fallback modes.
4. `create_doc`:
   - parser success: no fallback call
   - parser exception + `on_error`: fallback called
   - `always`: parser not called
   - `disabled`: parser exception propagated

## Security Tests

1. `file_url` rejects localhost/private IP destinations.
2. Redirect chain to private IP is rejected.
3. Local path outside allowlist is rejected.

## Integration (mocked API)

1. Drive `files.create` called with:
   - target Google Doc MIME
   - source media MIME expected
2. Shared drive folder resolution path preserved.

## Files to Modify

1. `gdrive/import_conversion.py` (new)
2. `gdrive/import_tools.py` (new) or `gdrive/files.py`
3. `gdocs/writing.py` (`create_doc` fallback_mode support)
4. `gdrive/__init__.py` (export new tool)
5. `main.py` (ensure module import/registration)
6. `tests/unit/tools/test_import_to_google_doc.py` (new)
7. `tests/unit/gdocs/test_create_doc_fallback.py` (new)
8. `README.md` (new tool docs + fallback mode docs)

## Rollout (Atomic PRs)

1. PR1: Add `import_to_google_doc` tool with `dry_run` and unit tests.
2. PR2: Add secure URL/file ingestion hardening for import flow.
3. PR3: Add `create_doc` fallback mode integration + tests.
4. PR4: Docs updates and examples.

## Definition of Done

1. Fallback mode works as specified for `create_doc`.
2. New tool `import_to_google_doc` available and safe-by-default.
3. All mutating paths default `dry_run=True`.
4. `uv run ruff check .` passes.
5. `uv run ruff format .` produces no diffs.
6. `uv run pytest` passes.
7. `uv run pyright --project pyrightconfig.json` passes.

## Open Questions

1. Should `fallback_mode` default to `on_error` immediately, or be feature-flagged first?
2. Do we want `source_format` to accept only enum values or free string normalization?
3. Should we expose the fallback path in response text by default, or only with verbose/debug mode?

