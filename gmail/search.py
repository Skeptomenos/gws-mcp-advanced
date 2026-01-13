"""
Gmail Search Tools

This module provides MCP tools for searching Gmail messages.
"""

import asyncio
import logging

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

from .helpers import _format_gmail_results_plain

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("search_gmail_messages", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_read")
async def search_gmail_messages(
    service,
    query: str,
    user_google_email: str,
    page_size: int = 10,
    page_token: str | None = None,
) -> str:
    """
    Searches messages in a user's Gmail account based on a query.
    Returns both Message IDs and Thread IDs for each found message, along with Gmail web interface links for manual verification.
    Supports pagination via page_token parameter.

    Args:
        query (str): The search query. Supports standard Gmail search operators.
        user_google_email (str): The user's Google email address. Required.
        page_size (int): The maximum number of messages to return. Defaults to 10.
        page_token (Optional[str]): Token for retrieving the next page of results. Use the next_page_token from a previous response.

    Returns:
        str: LLM-friendly structured results with Message IDs, Thread IDs, and clickable Gmail web interface URLs for each found message.
        Includes pagination token if more results are available.
    """
    logger.info(f"[search_gmail_messages] Email: '{user_google_email}', Query: '{query}', Page size: {page_size}")

    request_params = {"userId": "me", "q": query, "maxResults": page_size}

    if page_token:
        request_params["pageToken"] = page_token
        logger.info("[search_gmail_messages] Using page_token for pagination")

    response = await asyncio.to_thread(service.users().messages().list(**request_params).execute)

    if response is None:
        logger.warning("[search_gmail_messages] Null response from Gmail API")
        return f"No response received from Gmail API for query: '{query}'"

    messages = response.get("messages", [])
    if messages is None:
        messages = []

    next_page_token = response.get("nextPageToken")

    formatted_output = _format_gmail_results_plain(messages, query, next_page_token)

    logger.info(f"[search_gmail_messages] Found {len(messages)} messages")
    if next_page_token:
        logger.info("[search_gmail_messages] More results available (next_page_token present)")
    return formatted_output
