"""Integration tests for create_doc table-population workflow."""

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


class _StubBatchOperationManager:
    def __init__(self, _service):
        self._service = _service

    async def execute_batch_operations(self, _document_id: str, _operations):
        return True, "Batch operations completed", {"replies_count": 1}


class _StubHeaderFooterManager:
    def __init__(self, _service):
        self._service = _service

    async def update_header_footer_content(self, _document_id: str, _section_type: str, _content: str, _hf_type: str):
        return True, "Header/footer updated successfully"


class _StubValidationManager:
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


class _FakeTableOperationManager:
    calls: list[dict[str, object]] = []
    population_returns: list[int] = []

    def __init__(self, _service):
        self._service = _service

    async def _populate_table_cells(
        self,
        document_id: str,
        table_data: list[list[str]],
        bold_headers: bool,
        table_index: int = 0,
    ) -> int:
        self.__class__.calls.append(
            {
                "document_id": document_id,
                "table_data": table_data,
                "bold_headers": bold_headers,
                "table_index": table_index,
            }
        )

        if self.__class__.population_returns:
            return self.__class__.population_returns.pop(0)

        return sum(1 for row in table_data for cell in row if cell)


def _load_writing_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "gdocs" / "writing.py"
    module_name = "_test_gdocs_writing_table_flow"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def docs_writing_integration_module():
    module_keys = [
        "auth",
        "auth.service_decorator",
        "core",
        "core.server",
        "core.utils",
        "gdocs",
        "gdocs.docs_helpers",
        "gdocs.managers",
        "gdocs.managers.table_operation_manager",
        "gdocs.markdown_parser",
        "gdrive",
        "gdrive.drive_helpers",
    ]
    prior_modules = {key: sys.modules.get(key, _MISSING) for key in module_keys}

    root = Path(__file__).resolve().parents[2]
    markdown_parser_path = root / "gdocs" / "markdown_parser.py"
    markdown_spec = importlib.util.spec_from_file_location("gdocs.markdown_parser", markdown_parser_path)
    assert markdown_spec is not None and markdown_spec.loader is not None
    markdown_module = importlib.util.module_from_spec(markdown_spec)

    auth_pkg = types.ModuleType("auth")
    auth_service_decorator = types.ModuleType("auth.service_decorator")
    auth_service_decorator.require_google_service = _identity_decorator

    core_pkg = types.ModuleType("core")
    core_server = types.ModuleType("core.server")
    core_server.server = types.SimpleNamespace(tool=_tool_decorator)
    core_utils = types.ModuleType("core.utils")
    core_utils.handle_http_errors = _identity_decorator

    gdocs_pkg = types.ModuleType("gdocs")
    gdocs_pkg.__path__ = [str(root / "gdocs")]

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
    gdocs_managers.BatchOperationManager = _StubBatchOperationManager
    gdocs_managers.HeaderFooterManager = _StubHeaderFooterManager
    gdocs_managers.ValidationManager = _StubValidationManager

    gdocs_table_manager = types.ModuleType("gdocs.managers.table_operation_manager")
    gdocs_table_manager.TableOperationManager = _FakeTableOperationManager

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
    sys.modules["gdocs.managers.table_operation_manager"] = gdocs_table_manager
    sys.modules["gdocs.markdown_parser"] = markdown_module
    sys.modules["gdrive"] = gdrive_pkg
    sys.modules["gdrive.drive_helpers"] = gdrive_helpers

    markdown_spec.loader.exec_module(markdown_module)
    _FakeTableOperationManager.calls = []
    _FakeTableOperationManager.population_returns = []

    try:
        yield _load_writing_module(), _FakeTableOperationManager
    finally:
        for key, value in prior_modules.items():
            if value is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.asyncio
async def test_create_doc_populates_table_after_preceding_content(docs_writing_integration_module):
    module, table_manager = docs_writing_integration_module
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-123"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """Intro paragraph before table.

| H1 | H2 |
|---|---|
| A | B |
"""

    result = await module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Integration Table Test",
        content=markdown,
        parse_markdown=True,
        dry_run=False,
    )

    assert "Created Google Doc 'Integration Table Test'" in result
    assert service.documents.return_value.batchUpdate.call_count == 2
    phase_one_requests = service.documents.return_value.batchUpdate.call_args_list[0].kwargs["body"]["requests"]
    table_phase_requests = service.documents.return_value.batchUpdate.call_args_list[1].kwargs["body"]["requests"]
    assert any("insertText" in request for request in phase_one_requests)
    assert not any("insertTable" in request for request in phase_one_requests)
    assert any("insertTable" in request for request in table_phase_requests)

    assert len(table_manager.calls) == 1
    call = table_manager.calls[0]
    assert call["document_id"] == "doc-123"
    assert call["table_index"] == 0
    assert call["table_data"] == [["H1", "H2"], ["A", "B"]]


@pytest.mark.asyncio
async def test_create_doc_preserves_multiple_table_order_for_population(docs_writing_integration_module):
    module, table_manager = docs_writing_integration_module
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-456"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """First section.

| A1 | A2 |
|---|---|
| V1 | V2 |

Second section.

| B1 | B2 |
|---|---|
| W1 | W2 |
"""

    await module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Multi Table Order Test",
        content=markdown,
        parse_markdown=True,
        dry_run=False,
    )

    assert len(table_manager.calls) == 2
    assert [call["table_index"] for call in table_manager.calls] == [0, 1]
    assert table_manager.calls[0]["table_data"] == [["A1", "A2"], ["V1", "V2"]]
    assert table_manager.calls[1]["table_data"] == [["B1", "B2"], ["W1", "W2"]]


@pytest.mark.asyncio
async def test_create_doc_fails_when_table_population_is_incomplete(docs_writing_integration_module):
    module, table_manager = docs_writing_integration_module
    table_manager.population_returns = [0]
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-789"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """Intro.

| H1 | H2 |
|---|---|
| A | B |
"""

    with pytest.raises(RuntimeError, match="table population was incomplete"):
        await module.create_doc(
            service=service,
            user_google_email="user@example.com",
            title="Incomplete Table Population Test",
            content=markdown,
            parse_markdown=True,
            dry_run=False,
        )


@pytest.mark.asyncio
async def test_create_doc_applies_code_block_box_and_language_label(docs_writing_integration_module):
    module, _table_manager = docs_writing_integration_module
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-901"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """```python
print("hello")
```"""

    result = await module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Code Block Styling Test",
        content=markdown,
        parse_markdown=True,
        dry_run=False,
    )

    assert "Created Google Doc 'Code Block Styling Test'" in result
    batch_requests = service.documents.return_value.batchUpdate.call_args.kwargs["body"]["requests"]

    insert_request = next((request for request in batch_requests if "insertText" in request), None)
    assert insert_request is not None
    assert 'python\nprint("hello")' in insert_request["insertText"]["text"]

    code_block_paragraph = next(
        (
            request
            for request in batch_requests
            if "updateParagraphStyle" in request
            and "shading" in request["updateParagraphStyle"].get("paragraphStyle", {})
        ),
        None,
    )
    assert code_block_paragraph is not None
    paragraph_style = code_block_paragraph["updateParagraphStyle"]["paragraphStyle"]
    for side in ("borderTop", "borderRight", "borderBottom", "borderLeft"):
        assert side in paragraph_style


@pytest.mark.asyncio
async def test_create_doc_includes_inline_image_request_with_surrounding_text(docs_writing_integration_module):
    module, _table_manager = docs_writing_integration_module
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-902"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """Intro paragraph.

![logo](https://example.com/logo.png)

Outro paragraph."""

    result = await module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Image Insertion Flow Test",
        content=markdown,
        parse_markdown=True,
        dry_run=False,
    )

    assert "Created Google Doc 'Image Insertion Flow Test'" in result
    assert service.documents.return_value.batchUpdate.call_count == 2
    phase_one_requests = service.documents.return_value.batchUpdate.call_args_list[0].kwargs["body"]["requests"]
    phase_two_requests = service.documents.return_value.batchUpdate.call_args_list[1].kwargs["body"]["requests"]

    insert_request = next((request for request in phase_one_requests if "insertText" in request), None)
    assert insert_request is not None
    inserted_text = insert_request["insertText"]["text"]
    assert "Intro paragraph." in inserted_text
    assert "Outro paragraph." in inserted_text

    assert not any("insertInlineImage" in request for request in phase_one_requests)

    image_request = next((request for request in phase_two_requests if "insertInlineImage" in request), None)
    assert image_request is not None
    assert image_request["insertInlineImage"]["uri"] == "https://example.com/logo.png"
    assert image_request["insertInlineImage"]["location"]["index"] > 1

    delete_requests = [request for request in phase_two_requests if "deleteContentRange" in request]
    assert len(delete_requests) == 1


@pytest.mark.asyncio
async def test_create_doc_preserves_multiple_markdown_image_order(docs_writing_integration_module):
    module, _table_manager = docs_writing_integration_module
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-903"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """![first](https://example.com/first.png)

![second](https://example.com/second.png)"""

    await module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Multi Image Order Test",
        content=markdown,
        parse_markdown=True,
        dry_run=False,
    )

    assert service.documents.return_value.batchUpdate.call_count == 2
    phase_two_requests = service.documents.return_value.batchUpdate.call_args_list[1].kwargs["body"]["requests"]
    image_requests = [request for request in phase_two_requests if "insertInlineImage" in request]
    delete_requests = [request for request in phase_two_requests if "deleteContentRange" in request]

    assert len(image_requests) == 2
    assert len(delete_requests) == 2
    assert [request["insertInlineImage"]["uri"] for request in image_requests] == [
        "https://example.com/first.png",
        "https://example.com/second.png",
    ]
    first_index = image_requests[0]["insertInlineImage"]["location"]["index"]
    second_index = image_requests[1]["insertInlineImage"]["location"]["index"]
    assert first_index < second_index


@pytest.mark.asyncio
async def test_create_doc_runs_image_phase_before_table_population(docs_writing_integration_module):
    module, table_manager = docs_writing_integration_module
    service = MagicMock()
    service.documents.return_value.create.return_value.execute.return_value = {"documentId": "doc-904"}
    service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    markdown = """Before image.

![logo](https://example.com/logo.png)

| H1 | H2 |
|---|---|
| A | B |
"""

    await module.create_doc(
        service=service,
        user_google_email="user@example.com",
        title="Image And Table Ordering Test",
        content=markdown,
        parse_markdown=True,
        dry_run=False,
    )

    assert service.documents.return_value.batchUpdate.call_count == 3
    phase_one_requests = service.documents.return_value.batchUpdate.call_args_list[0].kwargs["body"]["requests"]
    image_phase_requests = service.documents.return_value.batchUpdate.call_args_list[1].kwargs["body"]["requests"]
    table_phase_requests = service.documents.return_value.batchUpdate.call_args_list[2].kwargs["body"]["requests"]

    assert any("insertText" in request for request in phase_one_requests)
    assert not any("insertTable" in request for request in phase_one_requests)
    assert any("insertInlineImage" in request for request in image_phase_requests)
    assert any("insertTable" in request for request in table_phase_requests)
    assert len(table_manager.calls) == 1
