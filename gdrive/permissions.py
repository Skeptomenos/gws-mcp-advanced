"""
Google Drive Permission Tools

This module provides MCP tools for managing file permissions and sharing in Google Drive.
"""

import asyncio
import logging
from typing import Literal

from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors
from gdrive.drive_helpers import (
    check_public_link_permission,
    format_permission_info,
    resolve_drive_item,
    validate_expiration_time,
    validate_share_role,
    validate_share_type,
)

logger = logging.getLogger(__name__)


class ShareRecipient(BaseModel):
    """Model for a share recipient in batch operations."""

    email: str | None = Field(None, description="Recipient email address. Required for 'user' or 'group' share_type.")
    domain: str | None = Field(None, description="Domain name. Required when share_type is 'domain'.")
    role: Literal["reader", "commenter", "writer"] = Field("reader", description="Permission role.")
    share_type: Literal["user", "group", "domain", "anyone"] = Field("user", description="Type of sharing.")
    expiration_time: str | None = Field(
        None, description="Expiration in RFC 3339 format (e.g., '2025-01-15T00:00:00Z')."
    )


@server.tool()
@handle_http_errors("get_drive_file_permissions", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def get_drive_file_permissions(
    service,
    user_google_email: str,
    file_id: str,
) -> str:
    """
    Gets detailed metadata about a Google Drive file including sharing permissions.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file to check permissions for.

    Returns:
        str: Detailed file metadata including sharing status and URLs.
    """
    logger.info(f"[get_drive_file_permissions] Checking file {file_id} for {user_google_email}")

    resolved_file_id, _ = await resolve_drive_item(service, file_id)
    file_id = resolved_file_id

    try:
        file_metadata = await asyncio.to_thread(
            service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, owners, "
                "permissions(id, type, role, emailAddress, domain, expirationTime, permissionDetails), "
                "webViewLink, webContentLink, shared, sharingUser, viewersCanCopyContent",
                supportsAllDrives=True,
            )
            .execute
        )

        output_parts = [
            f"File: {file_metadata.get('name', 'Unknown')}",
            f"ID: {file_id}",
            f"Type: {file_metadata.get('mimeType', 'Unknown')}",
            f"Size: {file_metadata.get('size', 'N/A')} bytes",
            f"Modified: {file_metadata.get('modifiedTime', 'N/A')}",
            "",
            "Sharing Status:",
            f"  Shared: {file_metadata.get('shared', False)}",
        ]

        sharing_user = file_metadata.get("sharingUser")
        if sharing_user:
            output_parts.append(
                f"  Shared by: {sharing_user.get('displayName', 'Unknown')} ({sharing_user.get('emailAddress', 'Unknown')})"
            )

        permissions = file_metadata.get("permissions", [])
        if permissions:
            output_parts.append(f"  Number of permissions: {len(permissions)}")
            output_parts.append("  Permissions:")
            for perm in permissions:
                output_parts.append(f"    - {format_permission_info(perm)}")
        else:
            output_parts.append("  No additional permissions (private file)")

        output_parts.extend(
            [
                "",
                "URLs:",
                f"  View Link: {file_metadata.get('webViewLink', 'N/A')}",
            ]
        )

        web_content_link = file_metadata.get("webContentLink")
        if web_content_link:
            output_parts.append(f"  Direct Download Link: {web_content_link}")

        has_public_link = check_public_link_permission(permissions)

        if has_public_link:
            output_parts.extend(
                [
                    "",
                    "This file is shared with 'Anyone with the link' - it can be inserted into Google Docs",
                ]
            )
        else:
            output_parts.extend(
                [
                    "",
                    "This file is NOT shared with 'Anyone with the link' - it cannot be inserted into Google Docs",
                    "   To fix: Right-click the file in Google Drive -> Share -> Anyone with the link -> Viewer",
                ]
            )

        return "\n".join(output_parts)

    except Exception as e:
        logger.error(f"Error getting file permissions: {e}")
        return f"Error getting file permissions: {e}"


@server.tool()
@handle_http_errors("get_drive_shareable_link", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def get_drive_shareable_link(
    service,
    user_google_email: str,
    file_id: str,
) -> str:
    """
    Gets the shareable link for a Google Drive file or folder.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file or folder to get the shareable link for. Required.

    Returns:
        str: The shareable links and current sharing status.
    """
    logger.info(f"[get_drive_shareable_link] Invoked. Email: '{user_google_email}', File ID: '{file_id}'")

    resolved_file_id, _ = await resolve_drive_item(service, file_id)
    file_id = resolved_file_id

    file_metadata = await asyncio.to_thread(
        service.files()
        .get(
            fileId=file_id,
            fields="id, name, mimeType, webViewLink, webContentLink, shared, "
            "permissions(id, type, role, emailAddress, domain, expirationTime)",
            supportsAllDrives=True,
        )
        .execute
    )

    output_parts = [
        f"File: {file_metadata.get('name', 'Unknown')}",
        f"ID: {file_id}",
        f"Type: {file_metadata.get('mimeType', 'Unknown')}",
        f"Shared: {file_metadata.get('shared', False)}",
        "",
        "Links:",
        f"  View: {file_metadata.get('webViewLink', 'N/A')}",
    ]

    web_content_link = file_metadata.get("webContentLink")
    if web_content_link:
        output_parts.append(f"  Download: {web_content_link}")

    permissions = file_metadata.get("permissions", [])
    if permissions:
        output_parts.append("")
        output_parts.append("Current permissions:")
        for perm in permissions:
            output_parts.append(f"  - {format_permission_info(perm)}")

    return "\n".join(output_parts)


@server.tool()
@handle_http_errors("share_drive_file", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def share_drive_file(
    service,
    user_google_email: str,
    file_id: str,
    share_with: str | None = None,
    role: str = "reader",
    share_type: str = "user",
    send_notification: bool = True,
    email_message: str | None = None,
    expiration_time: str | None = None,
    allow_file_discovery: bool | None = None,
) -> str:
    """
    Shares a Google Drive file or folder with a user, group, domain, or anyone with the link.

    When sharing a folder, all files inside inherit the permission.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file or folder to share. Required.
        share_with (Optional[str]): Email address (for user/group), domain name (for domain), or omit for 'anyone'.
        role (str): Permission role - 'reader', 'commenter', or 'writer'. Defaults to 'reader'.
        share_type (str): Type of sharing - 'user', 'group', 'domain', or 'anyone'. Defaults to 'user'.
        send_notification (bool): Whether to send a notification email. Defaults to True.
        email_message (Optional[str]): Custom message for the notification email.
        expiration_time (Optional[str]): Expiration time in RFC 3339 format (e.g., "2025-01-15T00:00:00Z"). Permission auto-revokes after this time.
        allow_file_discovery (Optional[bool]): For 'domain' or 'anyone' shares - whether the file can be found via search. Defaults to None (API default).

    Returns:
        str: Confirmation with permission details and shareable link.
    """
    logger.info(
        f"[share_drive_file] Invoked. Email: '{user_google_email}', File ID: '{file_id}', Share with: '{share_with}', Role: '{role}', Type: '{share_type}'"
    )

    validate_share_role(role)
    validate_share_type(share_type)

    if share_type in ("user", "group") and not share_with:
        raise ValueError(f"share_with is required for share_type '{share_type}'")
    if share_type == "domain" and not share_with:
        raise ValueError("share_with (domain name) is required for share_type 'domain'")

    resolved_file_id, file_metadata = await resolve_drive_item(service, file_id, extra_fields="name, webViewLink")
    file_id = resolved_file_id

    permission_body: dict = {
        "type": share_type,
        "role": role,
    }

    if share_type in ("user", "group"):
        permission_body["emailAddress"] = share_with
    elif share_type == "domain":
        permission_body["domain"] = share_with

    if expiration_time:
        validate_expiration_time(expiration_time)
        permission_body["expirationTime"] = expiration_time

    if share_type in ("domain", "anyone") and allow_file_discovery is not None:
        permission_body["allowFileDiscovery"] = allow_file_discovery

    create_params: dict = {
        "fileId": file_id,
        "body": permission_body,
        "supportsAllDrives": True,
        "fields": "id, type, role, emailAddress, domain, expirationTime",
    }

    if share_type in ("user", "group"):
        create_params["sendNotificationEmail"] = send_notification
        if email_message:
            create_params["emailMessage"] = email_message

    created_permission = await asyncio.to_thread(service.permissions().create(**create_params).execute)

    output_parts = [
        f"Successfully shared '{file_metadata.get('name', 'Unknown')}'",
        "",
        "Permission created:",
        f"  - {format_permission_info(created_permission)}",
        "",
        f"View link: {file_metadata.get('webViewLink', 'N/A')}",
    ]

    return "\n".join(output_parts)


@server.tool()
@handle_http_errors("batch_share_drive_file", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def batch_share_drive_file(
    service,
    user_google_email: str,
    file_id: str,
    recipients: list[ShareRecipient],
    send_notification: bool = True,
    email_message: str | None = None,
) -> str:
    """
    Shares a Google Drive file or folder with multiple users or groups in a single operation.

    Each recipient can have a different role and optional expiration time.

    Note: Each recipient is processed sequentially. For very large recipient lists,
    consider splitting into multiple calls.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file or folder to share. Required.
        recipients (List[ShareRecipient]): List of recipient objects.
        send_notification (bool): Whether to send notification emails. Defaults to True.
        email_message (Optional[str]): Custom message for notification emails.

    Returns:
        str: Summary of created permissions with success/failure for each recipient.
    """
    logger.info(
        f"[batch_share_drive_file] Invoked. Email: '{user_google_email}', File ID: '{file_id}', Recipients: {len(recipients)}"
    )

    resolved_file_id, file_metadata = await resolve_drive_item(service, file_id, extra_fields="name, webViewLink")
    file_id = resolved_file_id

    if not recipients:
        raise ValueError("recipients list cannot be empty")

    results = []
    success_count = 0
    failure_count = 0

    for recipient in recipients:
        share_type = recipient.share_type
        role = recipient.role
        expiration_time = recipient.expiration_time

        if share_type == "domain":
            domain = recipient.domain
            if not domain:
                results.append("  - Skipped: missing domain for domain share")
                failure_count += 1
                continue
            identifier = domain
        else:
            email = recipient.email
            if not email:
                results.append("  - Skipped: missing email address")
                failure_count += 1
                continue
            identifier = email

        permission_body: dict = {
            "type": share_type,
            "role": role,
        }

        if share_type == "domain":
            permission_body["domain"] = identifier
        else:
            permission_body["emailAddress"] = identifier

        if expiration_time:
            try:
                validate_expiration_time(expiration_time)
                permission_body["expirationTime"] = expiration_time
            except ValueError as e:
                results.append(f"  - {identifier}: Failed - {e}")
                failure_count += 1
                continue

        create_params: dict = {
            "fileId": file_id,
            "body": permission_body,
            "supportsAllDrives": True,
            "fields": "id, type, role, emailAddress, domain, expirationTime",
        }

        if share_type in ("user", "group"):
            create_params["sendNotificationEmail"] = send_notification
            if email_message:
                create_params["emailMessage"] = email_message

        try:
            created_permission = await asyncio.to_thread(service.permissions().create(**create_params).execute)
            results.append(f"  - {format_permission_info(created_permission)}")
            success_count += 1
        except HttpError as e:
            results.append(f"  - {identifier}: Failed - {str(e)}")
            failure_count += 1

    output_parts = [
        f"Batch share results for '{file_metadata.get('name', 'Unknown')}'",
        "",
        f"Summary: {success_count} succeeded, {failure_count} failed",
        "",
        "Results:",
    ]
    output_parts.extend(results)
    output_parts.extend(
        [
            "",
            f"View link: {file_metadata.get('webViewLink', 'N/A')}",
        ]
    )

    return "\n".join(output_parts)


@server.tool()
@handle_http_errors("update_drive_permission", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def update_drive_permission(
    service,
    user_google_email: str,
    file_id: str,
    permission_id: str,
    role: str | None = None,
    expiration_time: str | None = None,
) -> str:
    """
    Updates an existing permission on a Google Drive file or folder.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file or folder. Required.
        permission_id (str): The ID of the permission to update (from get_drive_file_permissions). Required.
        role (Optional[str]): New role - 'reader', 'commenter', or 'writer'. If not provided, role unchanged.
        expiration_time (Optional[str]): Expiration time in RFC 3339 format (e.g., "2025-01-15T00:00:00Z"). Set or update when permission expires.

    Returns:
        str: Confirmation with updated permission details.
    """
    logger.info(
        f"[update_drive_permission] Invoked. Email: '{user_google_email}', File ID: '{file_id}', Permission ID: '{permission_id}', Role: '{role}'"
    )

    if not role and not expiration_time:
        raise ValueError("Must provide at least one of: role, expiration_time")

    if role:
        validate_share_role(role)
    if expiration_time:
        validate_expiration_time(expiration_time)

    resolved_file_id, file_metadata = await resolve_drive_item(service, file_id, extra_fields="name")
    file_id = resolved_file_id

    if not role:
        current_permission = await asyncio.to_thread(
            service.permissions()
            .get(
                fileId=file_id,
                permissionId=permission_id,
                supportsAllDrives=True,
                fields="role",
            )
            .execute
        )
        role = current_permission.get("role")

    update_body: dict = {"role": role}
    if expiration_time:
        update_body["expirationTime"] = expiration_time

    updated_permission = await asyncio.to_thread(
        service.permissions()
        .update(
            fileId=file_id,
            permissionId=permission_id,
            body=update_body,
            supportsAllDrives=True,
            fields="id, type, role, emailAddress, domain, expirationTime",
        )
        .execute
    )

    output_parts = [
        f"Successfully updated permission on '{file_metadata.get('name', 'Unknown')}'",
        "",
        "Updated permission:",
        f"  - {format_permission_info(updated_permission)}",
    ]

    return "\n".join(output_parts)


@server.tool()
@handle_http_errors("remove_drive_permission", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def remove_drive_permission(
    service,
    user_google_email: str,
    file_id: str,
    permission_id: str,
) -> str:
    """
    Removes a permission from a Google Drive file or folder, revoking access.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file or folder. Required.
        permission_id (str): The ID of the permission to remove (from get_drive_file_permissions). Required.

    Returns:
        str: Confirmation of the removed permission.
    """
    logger.info(
        f"[remove_drive_permission] Invoked. Email: '{user_google_email}', File ID: '{file_id}', Permission ID: '{permission_id}'"
    )

    resolved_file_id, file_metadata = await resolve_drive_item(service, file_id, extra_fields="name")
    file_id = resolved_file_id

    await asyncio.to_thread(
        service.permissions().delete(fileId=file_id, permissionId=permission_id, supportsAllDrives=True).execute
    )

    output_parts = [
        f"Successfully removed permission from '{file_metadata.get('name', 'Unknown')}'",
        "",
        f"Permission ID '{permission_id}' has been revoked.",
    ]

    return "\n".join(output_parts)


@server.tool()
@handle_http_errors("transfer_drive_ownership", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def transfer_drive_ownership(
    service,
    user_google_email: str,
    file_id: str,
    new_owner_email: str,
    move_to_new_owners_root: bool = False,
) -> str:
    """
    Transfers ownership of a Google Drive file or folder to another user.

    This is an irreversible operation. The current owner will become an editor.
    Only works within the same Google Workspace domain or for personal accounts.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file or folder to transfer. Required.
        new_owner_email (str): Email address of the new owner. Required.
        move_to_new_owners_root (bool): If True, moves the file to the new owner's My Drive root. Defaults to False.

    Returns:
        str: Confirmation of the ownership transfer.
    """
    logger.info(
        f"[transfer_drive_ownership] Invoked. Email: '{user_google_email}', File ID: '{file_id}', New owner: '{new_owner_email}'"
    )

    resolved_file_id, file_metadata = await resolve_drive_item(service, file_id, extra_fields="name, owners")
    file_id = resolved_file_id

    current_owners = file_metadata.get("owners", [])
    current_owner_emails = [o.get("emailAddress", "") for o in current_owners]

    permission_body = {
        "type": "user",
        "role": "owner",
        "emailAddress": new_owner_email,
    }

    await asyncio.to_thread(
        service.permissions()
        .create(
            fileId=file_id,
            body=permission_body,
            transferOwnership=True,
            moveToNewOwnersRoot=move_to_new_owners_root,
            supportsAllDrives=True,
            fields="id, type, role, emailAddress",
        )
        .execute
    )

    output_parts = [
        f"Successfully transferred ownership of '{file_metadata.get('name', 'Unknown')}'",
        "",
        f"New owner: {new_owner_email}",
        f"Previous owner(s): {', '.join(current_owner_emails) or 'Unknown'}",
    ]

    if move_to_new_owners_root:
        output_parts.append(f"File moved to {new_owner_email}'s My Drive root.")

    output_parts.extend(["", "Note: Previous owner now has editor access."])

    return "\n".join(output_parts)
