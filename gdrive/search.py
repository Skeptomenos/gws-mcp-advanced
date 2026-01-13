"""
Google Drive Search Tools

This module provides MCP tools for searching and listing files in Google Drive.
"""

import asyncio
import logging

from auth.service_decorator import require_google_service
from core.managers import search_manager
from core.server import server
from core.utils import handle_http_errors
from gdrive.drive_helpers import (
    DRIVE_QUERY_PATTERNS,
    build_drive_list_params,
    check_public_link_permission,
    get_drive_image_url,
    resolve_drive_item,
    resolve_folder_id,
)

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("search_drive_files", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def search_drive_files(
    service,
    user_google_email: str,
    query: str,
    page_size: int = 10,
    drive_id: str | None = None,
    include_items_from_all_drives: bool = True,
    corpora: str | None = None,
) -> str:
    """
    Searches for files and folders within a user's Google Drive, including shared drives.

    Args:
        user_google_email (str): The user's Google email address. Required.
        query (str): The search query string. Supports Google Drive search operators.
        page_size (int): The maximum number of files to return. Defaults to 10.
        drive_id (Optional[str]): ID of the shared drive to search. If None, behavior depends on `corpora` and `include_items_from_all_drives`.
        include_items_from_all_drives (bool): Whether shared drive items should be included in results. Defaults to True. This is effective when not specifying a `drive_id`.
        corpora (Optional[str]): Bodies of items to query (e.g., 'user', 'domain', 'drive', 'allDrives').
                                 If 'drive_id' is specified and 'corpora' is None, it defaults to 'drive'.
                                 Otherwise, Drive API default behavior applies. Prefer 'user' or 'drive' over 'allDrives' for efficiency.

    Returns:
        str: A formatted list of found files/folders with their details (ID, name, type, size, modified time, link).
    """
    logger.info(f"[search_drive_files] Invoked. Email: '{user_google_email}', Query: '{query}'")

    # Check if the query looks like a structured Drive query or free text
    # Look for Drive API operators and structured query patterns
    is_structured_query = any(pattern.search(query) for pattern in DRIVE_QUERY_PATTERNS)

    if is_structured_query:
        final_query = query
        logger.info(f"[search_drive_files] Using structured query as-is: '{final_query}'")
    else:
        # For free text queries, wrap in fullText contains
        escaped_query = query.replace("'", "\\'")
        final_query = f"fullText contains '{escaped_query}'"
        logger.info(f"[search_drive_files] Reformatting free text query '{query}' to '{final_query}'")

    list_params = build_drive_list_params(
        query=final_query,
        page_size=page_size,
        drive_id=drive_id,
        include_items_from_all_drives=include_items_from_all_drives,
        corpora=corpora,
    )

    results = await asyncio.to_thread(service.files().list(**list_params).execute)
    files = results.get("files", [])
    if not files:
        return f"No files found for '{query}'."

    # Cache results with aliases (A, B, C...)
    cached_files = search_manager.cache_results(files)

    formatted_files_text_parts = [f"Found {len(cached_files)} files for {user_google_email} matching '{query}':"]
    for item in cached_files:
        alias = item.get("alias", "")
        size_str = f", Size: {item.get('size', 'N/A')}" if "size" in item else ""
        formatted_files_text_parts.append(
            f'[{alias}] Name: "{item["name"]}" (ID: {item["id"]}, Type: {item["mimeType"]}{size_str}, Modified: {item.get("modifiedTime", "N/A")}) Link: {item.get("webViewLink", "#")}'
        )
    text_output = "\n".join(formatted_files_text_parts)
    return text_output


@server.tool()
@handle_http_errors("list_drive_items", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def list_drive_items(
    service,
    user_google_email: str,
    folder_id: str = "root",
    page_size: int = 100,
    drive_id: str | None = None,
    include_items_from_all_drives: bool = True,
    corpora: str | None = None,
) -> str:
    """
    Lists files and folders, supporting shared drives.
    If `drive_id` is specified, lists items within that shared drive. `folder_id` is then relative to that drive (or use drive_id as folder_id for root).
    If `drive_id` is not specified, lists items from user's "My Drive" and accessible shared drives (if `include_items_from_all_drives` is True).

    Args:
        user_google_email (str): The user's Google email address. Required.
        folder_id (str): The ID of the Google Drive folder. Defaults to 'root'. For a shared drive, this can be the shared drive's ID to list its root, or a folder ID within that shared drive.
        page_size (int): The maximum number of items to return. Defaults to 100.
        drive_id (Optional[str]): ID of the shared drive. If provided, the listing is scoped to this drive.
        include_items_from_all_drives (bool): Whether items from all accessible shared drives should be included if `drive_id` is not set. Defaults to True.
        corpora (Optional[str]): Corpus to query ('user', 'drive', 'allDrives'). If `drive_id` is set and `corpora` is None, 'drive' is used. If None and no `drive_id`, API defaults apply.

    Returns:
        str: A formatted list of files/folders in the specified folder.
    """
    logger.info(f"[list_drive_items] Invoked. Email: '{user_google_email}', Folder ID: '{folder_id}'")

    resolved_folder_id = await resolve_folder_id(service, folder_id)
    final_query = f"'{resolved_folder_id}' in parents and trashed=false"

    list_params = build_drive_list_params(
        query=final_query,
        page_size=page_size,
        drive_id=drive_id,
        include_items_from_all_drives=include_items_from_all_drives,
        corpora=corpora,
    )

    results = await asyncio.to_thread(service.files().list(**list_params).execute)
    files = results.get("files", [])
    if not files:
        return f"No items found in folder '{folder_id}'."

    formatted_items_text_parts = [f"Found {len(files)} items in folder '{folder_id}' for {user_google_email}:"]
    for item in files:
        size_str = f", Size: {item.get('size', 'N/A')}" if "size" in item else ""
        formatted_items_text_parts.append(
            f'- Name: "{item["name"]}" (ID: {item["id"]}, Type: {item["mimeType"]}{size_str}, Modified: {item.get("modifiedTime", "N/A")}) Link: {item.get("webViewLink", "#")}'
        )
    text_output = "\n".join(formatted_items_text_parts)
    return text_output


@server.tool()
@handle_http_errors("check_drive_file_public_access", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def check_drive_file_public_access(
    service,
    user_google_email: str,
    file_name: str,
) -> str:
    """
    Searches for a file by name and checks if it has public link sharing enabled.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_name (str): The name of the file to check.

    Returns:
        str: Information about the file's sharing status and whether it can be used in Google Docs.
    """
    logger.info(f"[check_drive_file_public_access] Searching for {file_name}")

    # Search for the file
    escaped_name = file_name.replace("'", "\\'")
    query = f"name = '{escaped_name}'"

    list_params = {
        "q": query,
        "pageSize": 10,
        "fields": "files(id, name, mimeType, webViewLink)",
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }

    results = await asyncio.to_thread(service.files().list(**list_params).execute)

    files = results.get("files", [])
    if not files:
        return f"No file found with name '{file_name}'"

    if len(files) > 1:
        output_parts = [f"Found {len(files)} files with name '{file_name}':"]
        for f in files:
            output_parts.append(f"  - {f['name']} (ID: {f['id']})")
        output_parts.append("\nChecking the first file...")
        output_parts.append("")
    else:
        output_parts = []

    # Check permissions for the first file
    file_id = files[0]["id"]
    resolved_file_id, _ = await resolve_drive_item(service, file_id)
    file_id = resolved_file_id

    # Get detailed permissions
    file_metadata = await asyncio.to_thread(
        service.files()
        .get(
            fileId=file_id,
            fields="id, name, mimeType, permissions, webViewLink, webContentLink, shared",
            supportsAllDrives=True,
        )
        .execute
    )

    permissions = file_metadata.get("permissions", [])

    has_public_link = check_public_link_permission(permissions)

    output_parts.extend(
        [
            f"File: {file_metadata['name']}",
            f"ID: {file_id}",
            f"Type: {file_metadata['mimeType']}",
            f"Shared: {file_metadata.get('shared', False)}",
            "",
        ]
    )

    if has_public_link:
        output_parts.extend(
            [
                "PUBLIC ACCESS ENABLED - This file can be inserted into Google Docs",
                f"Use with insert_doc_image_url: {get_drive_image_url(file_id)}",
            ]
        )
    else:
        output_parts.extend(
            [
                "NO PUBLIC ACCESS - Cannot insert into Google Docs",
                "Fix: Drive -> Share -> 'Anyone with the link' -> 'Viewer'",
            ]
        )

    return "\n".join(output_parts)
