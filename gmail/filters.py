"""
Gmail Filter Tools

This module provides MCP tools for managing Gmail filters.
"""

import asyncio
import logging
from typing import Any

from fastapi import Body
from pydantic import Field

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("list_gmail_filters", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_settings_basic")
async def list_gmail_filters(service, user_google_email: str) -> str:
    """
    Lists all Gmail filters configured in the user's mailbox.

    Args:
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: A formatted list of filters with their criteria and actions.
    """
    logger.info(f"[list_gmail_filters] Invoked. Email: '{user_google_email}'")

    response = await asyncio.to_thread(service.users().settings().filters().list(userId="me").execute)

    filters = response.get("filter") or response.get("filters") or []

    if not filters:
        return "No filters found."

    lines = [f"Found {len(filters)} filters:", ""]

    for filter_obj in filters:
        filter_id = filter_obj.get("id", "(no id)")
        criteria = filter_obj.get("criteria", {})
        action = filter_obj.get("action", {})

        lines.append(f"🔹 Filter ID: {filter_id}")
        lines.append("  Criteria:")

        criteria_lines = []
        if criteria.get("from"):
            criteria_lines.append(f"From: {criteria['from']}")
        if criteria.get("to"):
            criteria_lines.append(f"To: {criteria['to']}")
        if criteria.get("subject"):
            criteria_lines.append(f"Subject: {criteria['subject']}")
        if criteria.get("query"):
            criteria_lines.append(f"Query: {criteria['query']}")
        if criteria.get("negatedQuery"):
            criteria_lines.append(f"Exclude Query: {criteria['negatedQuery']}")
        if criteria.get("hasAttachment"):
            criteria_lines.append("Has attachment")
        if criteria.get("excludeChats"):
            criteria_lines.append("Exclude chats")
        if criteria.get("size"):
            comparison = criteria.get("sizeComparison", "")
            criteria_lines.append(f"Size {comparison or ''} {criteria['size']} bytes".strip())

        if not criteria_lines:
            criteria_lines.append("(none)")

        lines.extend([f"    • {line}" for line in criteria_lines])

        lines.append("  Actions:")
        action_lines = []
        if action.get("forward"):
            action_lines.append(f"Forward to: {action['forward']}")
        if action.get("removeLabelIds"):
            action_lines.append(f"Remove labels: {', '.join(action['removeLabelIds'])}")
        if action.get("addLabelIds"):
            action_lines.append(f"Add labels: {', '.join(action['addLabelIds'])}")

        if not action_lines:
            action_lines.append("(none)")

        lines.extend([f"    • {line}" for line in action_lines])
        lines.append("")

    return "\n".join(lines).rstrip()


@server.tool()
@handle_http_errors("create_gmail_filter", service_type="gmail")
@require_google_service("gmail", "gmail_settings_basic")
async def create_gmail_filter(
    service,
    user_google_email: str,
    criteria: dict[str, Any] = Body(..., description="Filter criteria object as defined in the Gmail API."),
    action: dict[str, Any] = Body(..., description="Filter action object as defined in the Gmail API."),
) -> str:
    """
    Creates a Gmail filter using the users.settings.filters API.

    Args:
        user_google_email (str): The user's Google email address. Required.
        criteria (Dict[str, Any]): Criteria for matching messages.
        action (Dict[str, Any]): Actions to apply to matched messages.

    Returns:
        str: Confirmation message with the created filter ID.
    """
    logger.info("[create_gmail_filter] Invoked")

    filter_body = {"criteria": criteria, "action": action}

    created_filter = await asyncio.to_thread(
        service.users().settings().filters().create(userId="me", body=filter_body).execute
    )

    filter_id = created_filter.get("id", "(unknown)")
    return f"Filter created successfully!\nFilter ID: {filter_id}"


@server.tool()
@handle_http_errors("delete_gmail_filter", service_type="gmail")
@require_google_service("gmail", "gmail_settings_basic")
async def delete_gmail_filter(
    service,
    user_google_email: str,
    filter_id: str = Field(..., description="ID of the filter to delete."),
) -> str:
    """
    Deletes a Gmail filter by ID.

    Args:
        user_google_email (str): The user's Google email address. Required.
        filter_id (str): The ID of the filter to delete.

    Returns:
        str: Confirmation message for the deletion.
    """
    logger.info(f"[delete_gmail_filter] Invoked. Filter ID: '{filter_id}'")

    filter_details = await asyncio.to_thread(
        service.users().settings().filters().get(userId="me", id=filter_id).execute
    )

    await asyncio.to_thread(service.users().settings().filters().delete(userId="me", id=filter_id).execute)

    criteria = filter_details.get("criteria", {})
    action = filter_details.get("action", {})

    return (
        "Filter deleted successfully!\n"
        f"Filter ID: {filter_id}\n"
        f"Criteria: {criteria or '(none)'}\n"
        f"Action: {action or '(none)'}"
    )
