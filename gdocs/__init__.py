"""
Google Docs MCP Tools Package

This package provides MCP tools for interacting with Google Docs API.
"""

from gdocs.comments import (
    create_comment_tools,
    create_document_comment,
    read_document_comments,
    reply_to_document_comment,
    resolve_document_comment,
)
from gdocs.elements import insert_doc_elements, insert_doc_image
from gdocs.export import export_doc_to_pdf
from gdocs.reading import get_doc_content, inspect_doc_structure, list_docs_in_folder, search_docs
from gdocs.tables import create_table_with_data, debug_table_structure
from gdocs.writing import (
    batch_update_doc,
    create_doc,
    find_and_replace_doc,
    insert_markdown,
    modify_doc_text,
    update_doc_headers_footers,
)

__all__ = [
    "search_docs",
    "get_doc_content",
    "list_docs_in_folder",
    "inspect_doc_structure",
    "create_doc",
    "modify_doc_text",
    "insert_markdown",
    "find_and_replace_doc",
    "batch_update_doc",
    "update_doc_headers_footers",
    "insert_doc_elements",
    "insert_doc_image",
    "create_table_with_data",
    "debug_table_structure",
    "export_doc_to_pdf",
    "read_document_comments",
    "create_document_comment",
    "reply_to_document_comment",
    "resolve_document_comment",
    "create_comment_tools",
]
