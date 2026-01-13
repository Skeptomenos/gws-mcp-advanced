"""
Google Docs Comment Tools

This module provides MCP tools for managing comments on Google Docs.
"""

from core.comments import create_comment_tools

_comment_tools = create_comment_tools("document", "document_id")

read_document_comments = _comment_tools["read_comments"]
create_document_comment = _comment_tools["create_comment"]
reply_to_document_comment = _comment_tools["reply_to_comment"]
resolve_document_comment = _comment_tools["resolve_comment"]
