"""
Google Drive Sync Tools - Bidirectional synchronization between local files and Google Drive.

This module provides MCP tools for:
- Linking local files to Google Drive files
- Uploading local content to linked Drive files (with dry-run safety)
- Downloading Drive content to local files (with dry-run safety)
- Folder upload/download operations
- Multi-tab document handling

Ported from drive-synapsis with async adaptation for google_workspace_mcp patterns.
"""

import asyncio
import difflib
import logging
import os
import re
from collections import deque

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from auth.service_decorator import require_google_service, require_multiple_services
from core.errors import (
    GDriveError,
    LinkNotFoundError,
    LocalFileNotFoundError,
    SyncConflictError,
    format_error,
    handle_http_error,
)
from core.managers import search_manager, sync_manager
from core.server import server
from core.utils import handle_http_errors, validate_path_within_base

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


async def get_file_version(service, file_id: str) -> int:
    """Get the current version number of a Drive file."""
    result = await asyncio.to_thread(
        service.files().get(fileId=file_id, fields="version", supportsAllDrives=True).execute
    )
    return int(result.get("version", 0))


async def download_doc_as_text(service, file_id: str, mime_type: str = "text/plain") -> str:
    """Download a Google Doc as text/markdown."""
    result = await asyncio.to_thread(service.files().export(fileId=file_id, mimeType=mime_type).execute)
    if isinstance(result, bytes):
        return result.decode("utf-8")
    return result


def _is_binary_content(content: bytes | str) -> bool:
    """Determine if content should be written as binary (non-UTF-8 decodable bytes)."""
    if isinstance(content, str):
        return False
    try:
        content.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def _write_file_content(path: str, content: bytes | str, binary_mode: bool) -> None:
    """Write content to file in appropriate mode (binary or text)."""
    if binary_mode:
        with open(path, "wb") as f:
            f.write(content if isinstance(content, bytes) else content.encode("utf-8"))
    else:
        text = content if isinstance(content, str) else content.decode("utf-8")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


async def get_doc_structure(docs_service, file_id: str) -> dict:
    """Get the structure of a Google Doc including tabs."""
    result = await asyncio.to_thread(docs_service.documents().get(documentId=file_id, includeTabsContent=True).execute)
    return result


def resolve_file_id_or_alias(file_id_or_alias: str) -> str:
    """Resolve alias (A-Z) or file ID to actual file ID."""
    return search_manager.resolve_alias(file_id_or_alias)


# =============================================================================
# MCP Tools
# =============================================================================


@server.tool()
@handle_http_errors("link_local_file", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_read")
async def link_local_file(
    service,
    user_google_email: str,
    local_path: str,
    file_id: str,
) -> str:
    """
    Link a local file to a Google Drive file ID for synchronization.

    Args:
        user_google_email: The user's Google email address. Required.
        local_path: The relative path to the local file (e.g. "docs/notes.md").
        file_id: The Google Drive file ID or its search alias (e.g. "A").
    """
    try:
        real_id = resolve_file_id_or_alias(file_id)
        version = await get_file_version(service, real_id)
        sync_manager.link_file(local_path, real_id, version)
        return f"Linked {local_path} to {real_id} (Version {version})"
    except HttpError as e:
        return format_error("Link file", handle_http_error(e, file_id))
    except GDriveError as e:
        return format_error("Link file", e)
    except Exception as e:
        return f"Link file failed: Unexpected error ({type(e).__name__}: {e})"


@server.tool()
@handle_http_errors("update_google_doc", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_write")
async def update_google_doc(
    service,
    user_google_email: str,
    local_path: str,
    force: bool = False,
    dry_run: bool = True,
) -> str:
    """
    Upload content from a local file to its linked Google Doc.
    SAFETY: Defaults to dry_run=True. Usage must explicitly set dry_run=False to apply changes.

    Args:
        user_google_email: The user's Google email address. Required.
        local_path: Path to the local file.
        force: If True, overwrite even if the remote file has changed since last sync.
        dry_run: If True (default), return a diff of changes instead of updating. Set to False to apply.
    """
    try:
        link = sync_manager.get_link(local_path)
        if not link:
            raise LinkNotFoundError(local_path=local_path)

        file_id = link["id"]
        known_version = link.get("last_synced_version", 0)

        current_remote_version = await get_file_version(service, file_id)

        if not force and not dry_run and current_remote_version > known_version:
            raise SyncConflictError(
                message=f"Remote file (v{current_remote_version}) is newer than last synced (v{known_version}). Use force=True to overwrite.",
                local_version=known_version,
                remote_version=current_remote_version,
                file_id=file_id,
            )

        if not os.path.exists(local_path):
            raise LocalFileNotFoundError(local_path=local_path)

        with open(local_path) as f:
            content = f.read()

        if dry_run:
            # Download current remote content for diff
            remote_content = await download_doc_as_text(service, file_id, "text/plain")

            diff = difflib.unified_diff(
                remote_content.splitlines(),
                content.splitlines(),
                fromfile=f"Remote (v{current_remote_version})",
                tofile="Local (Proposed)",
                lineterm="",
            )
            diff_text = "\n".join(diff)
            if not diff_text:
                return "No changes detected."
            return f"DRY RUN (No changes made):\n\n```diff\n{diff_text}\n```"

        def link_replacer(match):
            """Replace local file links with Google Docs URLs.

            Args:
                match: Regex match object containing the link to replace.

            Returns:
                Replacement string with Google Docs URL, or original if not linked.
            """
            rel_path = match.group(1)
            base_dir = os.path.dirname(os.path.abspath(local_path))
            try:
                abs_target = validate_path_within_base(base_dir, rel_path)
            except Exception:
                return match.group(0)

            link_info = sync_manager.get_link(abs_target)
            if link_info:
                fid = link_info["id"]
                if ":" in fid:
                    fid = fid.split(":")[0]
                return f"(https://docs.google.com/document/d/{fid})"
            return match.group(0)

        pattern = r"\(((?:\.\.|\./|[\w\s-]+/)[^\)]+\.(?:md|txt|doc))\)"
        content = re.sub(pattern, link_replacer, content)

        # Upload the content - use media upload for text content
        from io import BytesIO

        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=True)

        await asyncio.to_thread(
            service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute
        )

        new_version = await get_file_version(service, file_id)
        sync_manager.update_version(local_path, new_version)

        return f"Successfully updated Google Doc (new version: {new_version})"

    except (LinkNotFoundError, LocalFileNotFoundError, SyncConflictError) as e:
        return format_error("Update doc", e)
    except HttpError as e:
        return format_error("Update doc", handle_http_error(e))
    except GDriveError as e:
        return format_error("Update doc", e)
    except Exception as e:
        return f"Update doc failed: Unexpected error ({type(e).__name__}: {e})"


@server.tool()
@handle_http_errors("download_google_doc", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_read")
async def download_google_doc(
    service,
    user_google_email: str,
    local_path: str,
    format: str = "markdown",
    include_comments: bool = False,
    rewrite_links: bool = True,
    dry_run: bool = True,
) -> str:
    """
    Download content from a linked Google Doc and SAVE it to a local file.
    SAFETY: Defaults to dry_run=True. Usage must explicitly set dry_run=False to apply changes.

    Args:
        user_google_email: The user's Google email address. Required.
        local_path: Path to the local file.
        format: Output format ('markdown', 'html', 'pdf', 'docx').
        include_comments: If True, append comments to the end.
        rewrite_links: If True, rewrite internal doc links to local file links.
        dry_run: If True (default), return a diff of changes (for text/markdown) or preview. Set False to save.
    """
    try:
        link = sync_manager.get_link(local_path)
        if not link:
            raise LinkNotFoundError(local_path=local_path)

        file_id = link["id"]

        # Determine export MIME type
        mime_map = {
            "markdown": "text/plain",
            "html": "text/html",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        export_mime = mime_map.get(format, "text/plain")

        content = await download_doc_as_text(service, file_id, export_mime)

        if rewrite_links and format == "markdown":

            def replace_callback(match):
                url = match.group(2)
                if "docs.google.com/document/d/" in url:
                    doc_id = url.split("/d/")[1].split("/")[0]

                    # Search through sync map for matching file
                    for lpath in sync_manager.file_map.keys():
                        link_info = sync_manager.get_link(lpath)
                        if link_info:
                            fid = link_info["id"]
                            if ":" in fid:
                                fid = fid.split(":")[0]
                            if fid == doc_id:
                                current_dir = os.path.dirname(os.path.abspath(local_path))
                                target_abs = os.path.abspath(lpath)
                                rel_path = os.path.relpath(target_abs, current_dir)
                                return f"[{match.group(1)}]({rel_path})"
                return match.group(0)

            link_pattern = r"\[([^\]]+)\]\((https?://[^\)]+)\)"
            content = re.sub(link_pattern, replace_callback, content)

        if dry_run:
            if format in ("markdown", "html"):
                if os.path.exists(local_path):
                    with open(local_path, encoding="utf-8") as f:
                        local_content = f.read()

                    diff = difflib.unified_diff(
                        local_content.splitlines(),
                        content.splitlines(),
                        fromfile="Local (Current)",
                        tofile="Remote (Proposed)",
                        lineterm="",
                    )
                    diff_text = "\n".join(diff)
                    if not diff_text:
                        return "No changes detected."
                    return f"DRY RUN (No changes made):\n\n```diff\n{diff_text}\n```"
                else:
                    preview = content[:500] + "..." if len(content) > 500 else content
                    return f"DRY RUN: Would create new file with content:\n\n{preview}"
            else:
                return f"DRY RUN: Would save {format.upper()} file to {local_path}"

        # Create directory if needed
        dir_path = os.path.dirname(local_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        if format in ("pdf", "docx"):
            with open(local_path, "wb") as fb:
                fb.write(content if isinstance(content, bytes) else content.encode("utf-8"))
        else:
            with open(local_path, "w") as ft:
                ft.write(content if isinstance(content, str) else content.decode("utf-8"))

        new_version = await get_file_version(service, file_id)
        sync_manager.update_version(local_path, new_version)

        return f"Successfully downloaded to {local_path} (synced at version {new_version})"

    except LinkNotFoundError as e:
        return format_error("Download doc", e)
    except HttpError as e:
        return format_error("Download doc", handle_http_error(e))
    except GDriveError as e:
        return format_error("Download doc", e)
    except Exception as e:
        return f"Download doc failed: Unexpected error ({type(e).__name__}: {e})"


@server.tool()
@handle_http_errors("upload_folder", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_write")
async def upload_folder(
    service,
    user_google_email: str,
    local_path: str,
    parent_folder_id: str | None = None,
) -> str:
    """
    Recursively upload a local folder to Google Drive using BFS traversal.
    More robust than recursion - handles deep trees and reports errors gracefully.

    Args:
        user_google_email: The user's Google email address. Required.
        local_path: Path to the local folder to upload.
        parent_folder_id: Optional parent folder ID in Drive. If None, uploads to root.
    """
    try:
        if not os.path.exists(local_path) or not os.path.isdir(local_path):
            return f"Upload folder failed: {local_path} is not a directory."

        dir_name = os.path.basename(os.path.normpath(local_path))
        folder_metadata: dict[str, str | list[str]] = {
            "name": dir_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            folder_metadata["parents"] = [parent_folder_id]

        root_folder = await asyncio.to_thread(
            service.files().create(body=folder_metadata, fields="id", supportsAllDrives=True).execute
        )
        root_id = root_folder.get("id")

        queue: deque[tuple[str, str | None]] = deque()

        for item in os.listdir(local_path):
            item_path = os.path.join(local_path, item)
            queue.append((item_path, root_id))

        uploaded_files = 0
        created_folders = 1
        errors = []

        while queue:
            current_path, current_parent_id = queue.popleft()

            if os.path.isdir(current_path):
                try:
                    sub_dir_name = os.path.basename(current_path)
                    sub_folder_meta = {
                        "name": sub_dir_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [current_parent_id],
                    }
                    sub_folder = await asyncio.to_thread(
                        service.files().create(body=sub_folder_meta, fields="id", supportsAllDrives=True).execute
                    )
                    sub_folder_id = sub_folder.get("id")
                    created_folders += 1

                    for item in os.listdir(current_path):
                        queue.append((os.path.join(current_path, item), sub_folder_id))
                except HttpError as e:
                    err = handle_http_error(e)
                    errors.append(f"Folder {current_path}: {err.message}")
                except Exception as e:
                    errors.append(f"Folder {current_path}: {str(e)}")
            else:
                try:
                    file_name = os.path.basename(current_path)
                    file_metadata = {
                        "name": file_name,
                        "parents": [current_parent_id],
                    }
                    media = MediaFileUpload(current_path, resumable=True)

                    result = await asyncio.to_thread(
                        service.files()
                        .create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True)
                        .execute
                    )

                    version = await get_file_version(service, result["id"])
                    sync_manager.link_file(current_path, result["id"], version)
                    uploaded_files += 1
                except HttpError as e:
                    err = handle_http_error(e)
                    errors.append(f"File {current_path}: {err.message}")
                except Exception as e:
                    errors.append(f"File {current_path}: {str(e)}")

        summary = f"Created {created_folders} folders and uploaded {uploaded_files} files."
        if errors:
            summary += f"\n\n{len(errors)} errors:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                summary += f"\n... and {len(errors) - 10} more"

        return summary

    except HttpError as e:
        return format_error("Upload folder", handle_http_error(e))
    except GDriveError as e:
        return format_error("Upload folder", e)
    except Exception as e:
        return f"Upload folder failed: Unexpected error ({type(e).__name__}: {e})"


@server.tool()
@handle_http_errors("mirror_drive_folder", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_read")
async def mirror_drive_folder(
    service,
    user_google_email: str,
    local_parent_dir: str,
    folder_query: str,
    recursive: bool = True,
) -> str:
    """
    Recursively download a Google Drive folder to a local directory.
    Maintains directory structure and links downloaded files for future sync.

    Args:
        user_google_email: The user's Google email address. Required.
        local_parent_dir: The local directory to download into. Created if missing.
        folder_query: The Name or ID of the Drive folder.
        recursive: Whether to download subfolders.
    """
    try:
        folder_id = resolve_file_id_or_alias(folder_query)

        # Get folder metadata
        folder_meta = await asyncio.to_thread(
            service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute
        )
        folder_name = folder_meta.get("name", "Downloaded")

        local_base = os.path.join(local_parent_dir, folder_name)
        os.makedirs(local_base, exist_ok=True)

        downloaded_files = 0
        created_folders = 1
        errors = []

        async def process_folder(f_id: str, current_local_path: str):
            nonlocal downloaded_files, created_folders, errors

            # List folder contents
            results = await asyncio.to_thread(
                service.files()
                .list(
                    q=f"'{f_id}' in parents and trashed=false",
                    fields="files(id, name, mimeType)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute
            )
            items = results.get("files", [])

            for item in items:
                item_name = item["name"]
                item_id = item["id"]
                mime_type = item.get("mimeType", "")

                if mime_type == "application/vnd.google-apps.folder":
                    if recursive:
                        sub_path = os.path.join(current_local_path, item_name)
                        os.makedirs(sub_path, exist_ok=True)
                        created_folders += 1
                        await process_folder(item_id, sub_path)
                else:
                    try:
                        if "google-apps" in mime_type:
                            content = await download_doc_as_text(service, item_id, "text/plain")
                            file_name = item_name + ".md"
                            write_binary = False
                        else:
                            content = await asyncio.to_thread(service.files().get_media(fileId=item_id).execute)
                            file_name = item_name
                            write_binary = _is_binary_content(content)

                        local_file_path = os.path.join(current_local_path, file_name)
                        _write_file_content(local_file_path, content, write_binary)

                        version = await get_file_version(service, item_id)
                        sync_manager.link_file(local_file_path, item_id, version)
                        downloaded_files += 1
                    except HttpError as e:
                        err = handle_http_error(e, item_id)
                        errors.append(f"{item_name}: {err.message}")
                    except Exception as e:
                        errors.append(f"{item_name}: {str(e)}")

        await process_folder(folder_id, local_base)

        summary = f"Downloaded {downloaded_files} files into {created_folders} folders at {local_base}."
        if errors:
            summary += f"\n\n{len(errors)} errors:\n" + "\n".join(errors[:5])

        return summary

    except HttpError as e:
        return format_error("Mirror folder", handle_http_error(e))
    except GDriveError as e:
        return format_error("Mirror folder", e)
    except Exception as e:
        return f"Mirror folder failed: Unexpected error ({type(e).__name__}: {e})"


@server.tool()
@handle_http_errors("download_doc_tabs", is_read_only=False, service_type="drive")
@require_multiple_services(
    [
        {"service_type": "drive", "scopes": "drive_read", "param_name": "drive_service"},
        {"service_type": "docs", "scopes": "docs_read", "param_name": "docs_service"},
    ]
)
async def download_doc_tabs(
    drive_service,
    docs_service,
    user_google_email: str,
    local_dir: str,
    file_id: str,
) -> str:
    """
    Download a Google Doc using "Hybrid Split-Sync".
    Creates a folder containing:
    1. _Full_Export.md: The entire doc as Markdown (High Fidelity).
    2. [TabName].md: Raw text content of each individual tab.

    Args:
        user_google_email: The user's Google email address. Required.
        local_dir: Local directory to save files into.
        file_id: The Google Drive file ID or its search alias (e.g. "A").
    """
    try:
        real_id = resolve_file_id_or_alias(file_id)

        os.makedirs(local_dir, exist_ok=True)

        # Download full export as markdown (high fidelity)
        full_content = await download_doc_as_text(drive_service, real_id, "text/plain")
        full_export_path = os.path.join(local_dir, "_Full_Export.md")
        with open(full_export_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        # Get document structure with tabs using Docs API
        doc_data = await asyncio.to_thread(
            docs_service.documents().get(documentId=real_id, includeTabsContent=True).execute
        )

        # Extract text from document elements (paragraphs, tables)
        def extract_text_from_elements(elements: list, depth: int = 0) -> str:
            """Extract text from document elements (paragraphs, tables, etc.)"""
            if depth > 5:  # Prevent infinite recursion
                return ""
            text_parts = []
            for element in elements:
                if "paragraph" in element:
                    paragraph = element.get("paragraph", {})
                    para_elements = paragraph.get("elements", [])
                    line_text = ""
                    for pe in para_elements:
                        text_run = pe.get("textRun", {})
                        if text_run and "content" in text_run:
                            line_text += text_run["content"]
                    if line_text.strip():
                        text_parts.append(line_text)
                elif "table" in element:
                    table = element.get("table", {})
                    table_rows = table.get("tableRows", [])
                    for row in table_rows:
                        row_cells = row.get("tableCells", [])
                        for cell in row_cells:
                            cell_content = cell.get("content", [])
                            cell_text = extract_text_from_elements(cell_content, depth=depth + 1)
                            if cell_text.strip():
                                text_parts.append(cell_text)
            return "".join(text_parts)

        def process_tab(tab: dict, level: int = 0) -> tuple[str, str]:
            """Process a tab and return (tab_title, tab_content)."""
            tab_title = "Untitled Tab"
            tab_content = ""

            if "documentTab" in tab:
                props = tab.get("tabProperties", {})
                tab_title = props.get("title", "Untitled Tab")
                tab_body = tab.get("documentTab", {}).get("body", {}).get("content", [])
                tab_content = extract_text_from_elements(tab_body)

            return tab_title, tab_content

        def collect_all_tabs(tabs: list, level: int = 0) -> list[tuple[str, str]]:
            """Recursively collect all tabs and their content."""
            result = []
            for tab in tabs:
                tab_title, tab_content = process_tab(tab, level)
                if tab_content.strip():
                    result.append((tab_title, tab_content))
                child_tabs = tab.get("childTabs", [])
                if child_tabs:
                    result.extend(collect_all_tabs(child_tabs, level + 1))
            return result

        # Get all tabs from document
        tabs = doc_data.get("tabs", [])
        all_tabs = collect_all_tabs(tabs)

        # Save each tab as a separate file
        saved_tabs = []
        tab_name_counts: dict[str, int] = {}

        for tab_title, tab_content in all_tabs:
            # Sanitize filename (remove invalid characters)
            safe_name = re.sub(r'[<>:"/\\|?*]', "_", tab_title)
            safe_name = safe_name.strip() or "Untitled"

            # Handle duplicate tab names
            if safe_name in tab_name_counts:
                tab_name_counts[safe_name] += 1
                safe_name = f"{safe_name}_{tab_name_counts[safe_name]}"
            else:
                tab_name_counts[safe_name] = 0

            tab_file_path = os.path.join(local_dir, f"{safe_name}.md")
            with open(tab_file_path, "w", encoding="utf-8") as f:
                f.write(tab_content)
            saved_tabs.append(safe_name)

        # Link files for sync tracking
        version = await get_file_version(drive_service, real_id)
        sync_manager.link_file(local_dir, real_id, version)
        sync_manager.link_file(full_export_path, real_id, version)

        # Build result message
        if saved_tabs:
            tab_list = ", ".join(saved_tabs)
            return (
                f"Hybrid Sync Complete in '{local_dir}'. Saved _Full_Export.md and {len(saved_tabs)} tab(s): {tab_list}"
            )
        else:
            return f"Hybrid Sync Complete in '{local_dir}'. Saved _Full_Export.md. (No tabs found or document uses legacy structure)"

    except HttpError as e:
        return format_error("Download tabs", handle_http_error(e, file_id))
    except GDriveError as e:
        return format_error("Download tabs", e)
    except Exception as e:
        return f"Download tabs failed: Unexpected error ({type(e).__name__}: {e})"
