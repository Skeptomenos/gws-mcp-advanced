"""
Google Gmail MCP Integration

This module provides MCP tools for interacting with the Gmail API.
"""

from .filters import (
    create_gmail_filter,
    delete_gmail_filter,
    list_gmail_filters,
)
from .labels import (
    batch_modify_gmail_message_labels,
    list_gmail_labels,
    manage_gmail_label,
    modify_gmail_message_labels,
)
from .messages import (
    draft_gmail_message,
    get_gmail_attachment_content,
    get_gmail_message_content,
    get_gmail_messages_content_batch,
    send_gmail_message,
)
from .search import search_gmail_messages
from .threads import (
    get_gmail_thread_content,
    get_gmail_threads_content_batch,
)

__all__ = [
    "search_gmail_messages",
    "get_gmail_message_content",
    "get_gmail_messages_content_batch",
    "get_gmail_attachment_content",
    "send_gmail_message",
    "draft_gmail_message",
    "get_gmail_thread_content",
    "get_gmail_threads_content_batch",
    "list_gmail_labels",
    "manage_gmail_label",
    "modify_gmail_message_labels",
    "batch_modify_gmail_message_labels",
    "list_gmail_filters",
    "create_gmail_filter",
    "delete_gmail_filter",
]
