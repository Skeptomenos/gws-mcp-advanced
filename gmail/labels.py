"""
Gmail Label Tools

This module provides MCP tools for managing Gmail labels.
"""

import asyncio
import logging
from typing import Any, Literal

from pydantic import Field

from auth.scopes import GMAIL_LABELS_SCOPE, GMAIL_MODIFY_SCOPE
from auth.service_decorator import require_google_service
from core.errors import ValidationError
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("list_gmail_labels", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_read")
async def list_gmail_labels(service, user_google_email: str) -> str:
    """
    Lists all labels in the user's Gmail account.

    Args:
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: A formatted list of all labels with their IDs, names, and types.
    """
    logger.info(f"[list_gmail_labels] Invoked. Email: '{user_google_email}'")

    response = await asyncio.to_thread(service.users().labels().list(userId="me").execute)
    labels = response.get("labels", [])

    if not labels:
        return "No labels found."

    lines = [f"Found {len(labels)} labels:", ""]

    system_labels = []
    user_labels = []

    for label in labels:
        if label.get("type") == "system":
            system_labels.append(label)
        else:
            user_labels.append(label)

    if system_labels:
        lines.append("📂 SYSTEM LABELS:")
        for label in system_labels:
            lines.append(f"  • {label['name']} (ID: {label['id']})")
        lines.append("")

    if user_labels:
        lines.append("🏷️  USER LABELS:")
        for label in user_labels:
            lines.append(f"  • {label['name']} (ID: {label['id']})")

    return "\n".join(lines)


@server.tool()
@handle_http_errors("manage_gmail_label", service_type="gmail")
@require_google_service("gmail", GMAIL_LABELS_SCOPE)
async def manage_gmail_label(
    service,
    user_google_email: str,
    action: Literal["create", "update", "delete"],
    name: str | None = None,
    label_id: str | None = None,
    label_list_visibility: Literal["labelShow", "labelHide"] = "labelShow",
    message_list_visibility: Literal["show", "hide"] = "show",
) -> str:
    """
    Manages Gmail labels: create, update, or delete labels.

    Args:
        user_google_email (str): The user's Google email address. Required.
        action (Literal["create", "update", "delete"]): Action to perform on the label.
        name (Optional[str]): Label name. Required for create, optional for update.
        label_id (Optional[str]): Label ID. Required for update and delete operations.
        label_list_visibility (Literal["labelShow", "labelHide"]): Whether the label is shown in the label list.
        message_list_visibility (Literal["show", "hide"]): Whether the label is shown in the message list.

    Returns:
        str: Confirmation message of the label operation.
    """
    logger.info(f"[manage_gmail_label] Invoked. Email: '{user_google_email}', Action: '{action}'")

    if action == "create" and not name:
        raise ValidationError("Label name is required for create action.")

    if action in ["update", "delete"] and not label_id:
        raise ValidationError("Label ID is required for update and delete actions.")

    if action == "create":
        label_object = {
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }
        created_label = await asyncio.to_thread(service.users().labels().create(userId="me", body=label_object).execute)
        return f"Label created successfully!\nName: {created_label['name']}\nID: {created_label['id']}"

    elif action == "update":
        current_label = await asyncio.to_thread(service.users().labels().get(userId="me", id=label_id).execute)

        label_object = {
            "id": label_id,
            "name": name if name is not None else current_label["name"],
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }

        updated_label = await asyncio.to_thread(
            service.users().labels().update(userId="me", id=label_id, body=label_object).execute
        )
        return f"Label updated successfully!\nName: {updated_label['name']}\nID: {updated_label['id']}"

    elif action == "delete":
        label = await asyncio.to_thread(service.users().labels().get(userId="me", id=label_id).execute)
        label_name = label["name"]

        await asyncio.to_thread(service.users().labels().delete(userId="me", id=label_id).execute)
        return f"Label '{label_name}' (ID: {label_id}) deleted successfully!"

    return "Unknown action"


@server.tool()
@handle_http_errors("modify_gmail_message_labels", service_type="gmail")
@require_google_service("gmail", GMAIL_MODIFY_SCOPE)
async def modify_gmail_message_labels(
    service,
    user_google_email: str,
    message_id: str,
    add_label_ids: list[str] = Field(default=[], description="Label IDs to add to the message."),
    remove_label_ids: list[str] = Field(default=[], description="Label IDs to remove from the message."),
) -> str:
    """
    Adds or removes labels from a Gmail message.
    To archive an email, remove the INBOX label.
    To delete an email, add the TRASH label.

    Args:
        user_google_email (str): The user's Google email address. Required.
        message_id (str): The ID of the message to modify.
        add_label_ids (Optional[List[str]]): List of label IDs to add to the message.
        remove_label_ids (Optional[List[str]]): List of label IDs to remove from the message.

    Returns:
        str: Confirmation message of the label changes applied to the message.
    """
    logger.info(f"[modify_gmail_message_labels] Invoked. Email: '{user_google_email}', Message ID: '{message_id}'")

    if not add_label_ids and not remove_label_ids:
        raise ValidationError("At least one of add_label_ids or remove_label_ids must be provided.")

    body: dict[str, Any] = {}
    if add_label_ids:
        body["addLabelIds"] = add_label_ids
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids

    await asyncio.to_thread(service.users().messages().modify(userId="me", id=message_id, body=body).execute)

    actions = []
    if add_label_ids:
        actions.append(f"Added labels: {', '.join(add_label_ids)}")
    if remove_label_ids:
        actions.append(f"Removed labels: {', '.join(remove_label_ids)}")

    return f"Message labels updated successfully!\nMessage ID: {message_id}\n{'; '.join(actions)}"


@server.tool()
@handle_http_errors("batch_modify_gmail_message_labels", service_type="gmail")
@require_google_service("gmail", GMAIL_MODIFY_SCOPE)
async def batch_modify_gmail_message_labels(
    service,
    user_google_email: str,
    message_ids: list[str],
    add_label_ids: list[str] = Field(default=[], description="Label IDs to add to messages."),
    remove_label_ids: list[str] = Field(default=[], description="Label IDs to remove from messages."),
) -> str:
    """
    Adds or removes labels from multiple Gmail messages in a single batch request.

    Args:
        user_google_email (str): The user's Google email address. Required.
        message_ids (List[str]): A list of message IDs to modify.
        add_label_ids (Optional[List[str]]): List of label IDs to add to the messages.
        remove_label_ids (Optional[List[str]]): List of label IDs to remove from the messages.

    Returns:
        str: Confirmation message of the label changes applied to the messages.
    """
    logger.info(
        f"[batch_modify_gmail_message_labels] Invoked. Email: '{user_google_email}', Message IDs: '{message_ids}'"
    )

    if not add_label_ids and not remove_label_ids:
        raise ValidationError("At least one of add_label_ids or remove_label_ids must be provided.")

    body: dict[str, Any] = {"ids": message_ids}
    if add_label_ids:
        body["addLabelIds"] = add_label_ids
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids

    await asyncio.to_thread(service.users().messages().batchModify(userId="me", body=body).execute)

    actions = []
    if add_label_ids:
        actions.append(f"Added labels: {', '.join(add_label_ids)}")
    if remove_label_ids:
        actions.append(f"Removed labels: {', '.join(remove_label_ids)}")

    return f"Labels updated for {len(message_ids)} messages: {'; '.join(actions)}"
