"""Unit tests for Google Docs writing mutator dry-run behavior."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MISSING = object()


def _identity_decorator(*_args, **_kwargs):
    def decorator(func):
        return func

    return decorator


def _tool_decorator():
    def decorator(func):
        func.name = func.__name__
        func.fn = func
        return func

    return decorator


class _ValidationManager:
    def validate_document_id(self, _document_id: str):
        return True, ""

    def validate_text_formatting_params(self, *_args, **_kwargs):
        return True, ""

    def validate_index_range(self, *_args, **_kwargs):
        return True, ""

    def validate_header_footer_params(self, *_args, **_kwargs):
        return True, ""

    def validate_text_content(self, *_args, **_kwargs):
        return True, ""

    def validate_batch_operations(self, *_args, **_kwargs):
        return True, ""


class _BatchOperationManager:
    def __init__(self, _service):
        self._service = _service

    async def execute_batch_operations(self, _document_id: str, _operations):
        return True, "Batch operations completed", {"replies_count": 1}


class _HeaderFooterManager:
    def __init__(self, _service):
        self._service = _service

    async def update_header_footer_content(self, _document_id: str, _section_type: str, _content: str, _hf_type: str):
        return True, "Header/footer updated successfully"


class _MarkdownToDocsConverter:
    def __init__(self, checklist_mode: str = "unicode", mention_mode: str = "text"):
        self.checklist_mode = checklist_mode
        self.mention_mode = mention_mode
        self.pending_tables = []

    def convert(self, _markdown_text: str, start_index: int = 1):
        return [{"insertText": {"location": {"index": start_index}, "text": "converted"}}]


def _load_writing_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "gdocs" / "writing.py"

    module_name = "_test_gdocs_writing_tools"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def docs_writing_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
        "gdocs",
        "gdocs.docs_helpers",
        "gdocs.managers",
        "gdocs.markdown_parser",
        "gdrive",
        "gdrive.drive_helpers",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    auth_pkg = types.ModuleType("auth")
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_server = types.ModuleType("core.server")
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils = types.ModuleType("core.utils")
    core_utils.handle_http_errors = _identity_decorator

    gdocs_pkg = types.ModuleType("gdocs")
    gdocs_helpers = types.ModuleType("gdocs.docs_helpers")
    gdocs_helpers.create_delete_range_request = lambda start, end: {
        "deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}
    }
    gdocs_helpers.create_find_replace_request = lambda find_text, replace_text, match_case=False: {
        "replaceAllText": {"containsText": {"text": find_text, "matchCase": match_case}, "replaceText": replace_text}
    }
    gdocs_helpers.create_format_text_request = lambda start, end, *_args, **_kwargs: {
        "updateTextStyle": {"range": {"startIndex": start, "endIndex": end}, "textStyle": {"bold": True}}
    }
    gdocs_helpers.create_insert_text_request = lambda index, text: {
        "insertText": {"location": {"index": index}, "text": text}
    }

    gdocs_managers = types.ModuleType("gdocs.managers")
    gdocs_managers.BatchOperationManager = _BatchOperationManager
    gdocs_managers.HeaderFooterManager = _HeaderFooterManager
    gdocs_managers.ValidationManager = _ValidationManager

    gdocs_markdown_parser = types.ModuleType("gdocs.markdown_parser")
    gdocs_markdown_parser.MarkdownToDocsConverter = _MarkdownToDocsConverter

    gdrive_pkg = types.ModuleType("gdrive")
    gdrive_helpers = types.ModuleType("gdrive.drive_helpers")
    gdrive_helpers.resolve_file_id_or_alias = lambda value: value

    sys.modules["auth"] = auth_pkg
    sys.modules["auth.service_decorator"] = auth_service_decorator
    sys.modules["core"] = core_pkg
    sys.modules["core.server"] = core_server
    sys.modules["core.utils"] = core_utils
    sys.modules["gdocs"] = gdocs_pkg
    sys.modules["gdocs.docs_helpers"] = gdocs_helpers
    sys.modules["gdocs.managers"] = gdocs_managers
    sys.modules["gdocs.markdown_parser"] = gdocs_markdown_parser
    sys.modules["gdrive"] = gdrive_pkg
    sys.modules["gdrive.drive_helpers"] = gdrive_helpers

    try:
        yield _load_writing_module()
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_doc_dry_run_default_skips_mutation(docs_writing_module):
    service = MagicMock()

    result = await docs_writing_module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Dry Run Doc",
        content="# Heading",
    )

    assert result.startswith("DRY RUN:")
    assert "apply 1 request(s)" in result
    assert service.documents.call_count == 0


def test_partition_markdown_requests_extracts_structural_pairs(docs_writing_module):
    requests = [
        {"insertText": {"location": {"index": 1}, "text": "intro\ufffcoutro"}},
        {"updateParagraphStyle": {"range": {"startIndex": 1, "endIndex": 6}}},
        {"deleteContentRange": {"range": {"startIndex": 6, "endIndex": 7}}},
        {"insertInlineImage": {"location": {"index": 6}, "uri": "https://example.com/logo.png"}},
        {"deleteContentRange": {"range": {"startIndex": 3, "endIndex": 4}}},
        {"insertTable": {"location": {"index": 3}, "rows": 2, "columns": 2}},
    ]

    base, mention_phase, image_phase, table_phase = docs_writing_module._partition_markdown_requests(requests)

    assert len(base) == 2
    assert any("insertText" in request for request in base)
    assert any("updateParagraphStyle" in request for request in base)
    assert mention_phase == []

    assert len(image_phase) == 2
    assert "deleteContentRange" in image_phase[0]
    assert "insertInlineImage" in image_phase[1]

    assert len(table_phase) == 2
    assert "deleteContentRange" in table_phase[0]
    assert "insertTable" in table_phase[1]


@pytest.mark.asyncio
async def test_insert_markdown_person_chip_fallback_keeps_literal_token(docs_writing_module):
    service = MagicMock()

    class _MentionConverter:
        pending_tables = []

        def __init__(self, checklist_mode: str = "unicode", mention_mode: str = "text"):
            self.checklist_mode = checklist_mode
            self.mention_mode = mention_mode

        def convert(self, _markdown_text: str, start_index: int = 1):
            return [
                {"insertText": {"location": {"index": start_index}, "text": "@user@example.com\n"}},
                {"deleteContentRange": {"range": {"startIndex": start_index, "endIndex": start_index + 17}}},
                {
                    "insertPerson": {
                        "location": {"index": start_index},
                        "personProperties": {"email": "user@example.com"},
                    }
                },
            ]

    docs_writing_module.MarkdownToDocsConverter = _MentionConverter
    service.documents.return_value.batchUpdate.return_value.execute.side_effect = [
        {},  # base phase succeeds
        RuntimeError("insertPerson unsupported"),  # mention phase fails -> fallback note
    ]
    document_id = "f" * 24

    result = await docs_writing_module.insert_markdown(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        markdown_text="@user@example.com",
        mention_mode="person_chip",
        dry_run=False,
    )

    assert "Inserted Markdown content into document" in result
    assert "Mention fallback kept literal tokens for: @user@example.com" in result


@pytest.mark.asyncio
async def test_create_doc_dry_run_false_executes_create_and_batch_update(docs_writing_module):
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-123"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    result = await docs_writing_module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Live Doc",
        content="Plain text",
        parse_markdown=False,
        dry_run=False,
    )

    assert "Created Google Doc 'Live Doc' (ID: doc-123)" in result
    assert service.documents.return_value.create.call_count == 1
    assert service.documents.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_modify_doc_text_dry_run_default_skips_mutation(docs_writing_module):
    service = MagicMock()
    document_id = "a" * 24

    result = await docs_writing_module.modify_doc_text(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        start_index=1,
        text="hello",
    )

    assert result.startswith("DRY RUN:")
    assert f"document {document_id}" in result
    assert service.documents.call_count == 0


@pytest.mark.asyncio
async def test_modify_doc_text_dry_run_false_executes_batch_update(docs_writing_module):
    service = MagicMock()
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}
    document_id = "a" * 24

    result = await docs_writing_module.modify_doc_text(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        start_index=1,
        text="hello",
        dry_run=False,
    )

    assert "Inserted text at index 1" in result
    assert service.documents.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_find_and_replace_doc_dry_run_default_skips_mutation(docs_writing_module):
    service = MagicMock()
    document_id = "b" * 24

    result = await docs_writing_module.find_and_replace_doc(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        find_text="old",
        replace_text="new",
    )

    assert result.startswith("DRY RUN:")
    assert "replace occurrences of 'old' with 'new'" in result
    assert service.documents.call_count == 0


@pytest.mark.asyncio
async def test_find_and_replace_doc_dry_run_false_executes_batch_update(docs_writing_module):
    service = MagicMock()
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {
        "replies": [{"replaceAllText": {"occurrencesChanged": 3}}]
    }
    document_id = "b" * 24

    result = await docs_writing_module.find_and_replace_doc(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        find_text="old",
        replace_text="new",
        dry_run=False,
    )

    assert "Replaced 3 occurrence(s)" in result
    assert service.documents.return_value.batchUpdate.call_count == 1


@pytest.mark.asyncio
async def test_update_doc_headers_footers_dry_run_default_skips_mutation(docs_writing_module):
    service = MagicMock()
    document_id = "c" * 24

    result = await docs_writing_module.update_doc_headers_footers(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        section_type="header",
        content="Confidential",
    )

    assert result.startswith("DRY RUN:")
    assert "Would update header (DEFAULT)" in result
    assert service.documents.call_count == 0


@pytest.mark.asyncio
async def test_update_doc_headers_footers_dry_run_false_executes_update(docs_writing_module):
    service = MagicMock()
    document_id = "c" * 24

    result = await docs_writing_module.update_doc_headers_footers(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        section_type="header",
        content="Confidential",
        dry_run=False,
    )

    assert "Header/footer updated successfully" in result


@pytest.mark.asyncio
async def test_batch_update_doc_dry_run_default_skips_mutation(docs_writing_module):
    service = MagicMock()
    document_id = "d" * 24
    operations = [{"type": "insert_text", "index": 1, "text": "hello"}]

    result = await docs_writing_module.batch_update_doc(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        operations=operations,
    )

    assert result.startswith("DRY RUN:")
    assert "Would execute 1 batch operation(s)" in result
    assert service.documents.call_count == 0


@pytest.mark.asyncio
async def test_batch_update_doc_dry_run_false_executes_operations(docs_writing_module):
    service = MagicMock()
    document_id = "d" * 24
    operations = [{"type": "insert_text", "index": 1, "text": "hello"}]

    result = await docs_writing_module.batch_update_doc(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        operations=operations,
        dry_run=False,
    )

    assert "Batch operations completed on document" in result


@pytest.mark.asyncio
async def test_insert_markdown_dry_run_default_skips_mutation(docs_writing_module):
    service = MagicMock()
    document_id = "e" * 24

    result = await docs_writing_module.insert_markdown(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        markdown_text="# Title",
    )

    assert result.startswith("DRY RUN:")
    assert "Would insert Markdown into document" in result
    assert service.documents.call_count == 0


@pytest.mark.asyncio
async def test_insert_markdown_dry_run_false_executes_batch_update(docs_writing_module):
    service = MagicMock()
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}
    document_id = "e" * 24

    result = await docs_writing_module.insert_markdown(
        service=service,
        user_google_email="user@example.com",
        document_id=document_id,
        markdown_text="# Title",
        dry_run=False,
    )

    assert "Inserted Markdown content into document" in result
    assert service.documents.return_value.batchUpdate.call_count == 1
