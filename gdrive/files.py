"""
Google Drive File Tools

This module provides MCP tools for reading, creating, and updating files in Google Drive.
"""

import asyncio
import base64
import io
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from urllib.request import url2pathname

import httpx
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from auth.config import is_stateless_mode
from auth.service_decorator import require_google_service
from core.attachment_storage import get_attachment_storage, get_attachment_url
from core.config import get_transport_mode
from core.errors import ValidationError
from core.server import server
from core.utils import extract_office_xml_text, handle_http_errors
from gdrive.drive_helpers import (
    resolve_drive_item,
    resolve_folder_id,
)

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE_BYTES = 256 * 1024  # 256 KB
UPLOAD_CHUNK_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB (Google recommended minimum)


@server.tool()
@handle_http_errors("get_drive_file_content", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def get_drive_file_content(
    service,
    user_google_email: str,
    file_id: str,
) -> str:
    """
    Retrieves the content of a specific Google Drive file by ID, supporting files in shared drives.

    • Native Google Docs, Sheets, Slides → exported as text / CSV.
    • Office files (.docx, .xlsx, .pptx) → unzipped & parsed with std-lib to
      extract readable text.
    • Any other file → downloaded; tries UTF-8 decode, else notes binary.

    Args:
        user_google_email: The user's Google email address.
        file_id: Drive file ID.

    Returns:
        str: The file content as plain text with metadata header.
    """
    logger.info(f"[get_drive_file_content] Invoked. File ID: '{file_id}'")

    resolved_file_id, file_metadata = await resolve_drive_item(
        service,
        file_id,
        extra_fields="name, webViewLink",
    )
    file_id = resolved_file_id
    mime_type = file_metadata.get("mimeType", "")
    file_name = file_metadata.get("name", "Unknown File")
    export_mime_type = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }.get(mime_type)

    request_obj = (
        service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        if export_mime_type
        else service.files().get_media(fileId=file_id)
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_obj)
    loop = asyncio.get_event_loop()
    done = False
    while not done:
        status, done = await loop.run_in_executor(None, downloader.next_chunk)

    file_content_bytes = fh.getvalue()

    office_mime_types = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    if mime_type in office_mime_types:
        office_text = extract_office_xml_text(file_content_bytes, mime_type)
        if office_text:
            body_text = office_text
        else:
            try:
                body_text = file_content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                body_text = (
                    f"[Binary or unsupported text encoding for mimeType '{mime_type}' - "
                    f"{len(file_content_bytes)} bytes]"
                )
    else:
        try:
            body_text = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body_text = (
                f"[Binary or unsupported text encoding for mimeType '{mime_type}' - {len(file_content_bytes)} bytes]"
            )

    header = (
        f'File: "{file_name}" (ID: {file_id}, Type: {mime_type})\n'
        f"Link: {file_metadata.get('webViewLink', '#')}\n\n--- CONTENT ---\n"
    )
    return header + body_text


@server.tool()
@handle_http_errors("get_drive_file_download_url", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def get_drive_file_download_url(
    service,
    user_google_email: str,
    file_id: str,
    export_format: str | None = None,
) -> str:
    """
    Gets a download URL for a Google Drive file. The file is prepared and made available via HTTP URL.

    For Google native files (Docs, Sheets, Slides), exports to a useful format:
    • Google Docs → PDF (default) or DOCX if export_format='docx'
    • Google Sheets → XLSX (default) or CSV if export_format='csv'
    • Google Slides → PDF (default) or PPTX if export_format='pptx'

    For other files, downloads the original file format.

    Args:
        user_google_email: The user's Google email address. Required.
        file_id: The Google Drive file ID to get a download URL for.
        export_format: Optional export format for Google native files.
                      Options: 'pdf', 'docx', 'xlsx', 'csv', 'pptx'.
                      If not specified, uses sensible defaults (PDF for Docs/Slides, XLSX for Sheets).

    Returns:
        str: Download URL and file metadata. The file is available at the URL for 1 hour.
    """
    logger.info(f"[get_drive_file_download_url] Invoked. File ID: '{file_id}', Export format: {export_format}")

    resolved_file_id, file_metadata = await resolve_drive_item(
        service,
        file_id,
        extra_fields="name, webViewLink, mimeType",
    )
    file_id = resolved_file_id
    mime_type = file_metadata.get("mimeType", "")
    file_name = file_metadata.get("name", "Unknown File")

    export_mime_type = None
    output_filename = file_name
    output_mime_type = mime_type

    if mime_type == "application/vnd.google-apps.document":
        if export_format == "docx":
            export_mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            output_mime_type = export_mime_type
            if not output_filename.endswith(".docx"):
                output_filename = f"{Path(output_filename).stem}.docx"
        else:
            export_mime_type = "application/pdf"
            output_mime_type = export_mime_type
            if not output_filename.endswith(".pdf"):
                output_filename = f"{Path(output_filename).stem}.pdf"

    elif mime_type == "application/vnd.google-apps.spreadsheet":
        if export_format == "csv":
            export_mime_type = "text/csv"
            output_mime_type = export_mime_type
            if not output_filename.endswith(".csv"):
                output_filename = f"{Path(output_filename).stem}.csv"
        else:
            export_mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            output_mime_type = export_mime_type
            if not output_filename.endswith(".xlsx"):
                output_filename = f"{Path(output_filename).stem}.xlsx"

    elif mime_type == "application/vnd.google-apps.presentation":
        if export_format == "pptx":
            export_mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            output_mime_type = export_mime_type
            if not output_filename.endswith(".pptx"):
                output_filename = f"{Path(output_filename).stem}.pptx"
        else:
            export_mime_type = "application/pdf"
            output_mime_type = export_mime_type
            if not output_filename.endswith(".pdf"):
                output_filename = f"{Path(output_filename).stem}.pdf"

    request_obj = (
        service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        if export_mime_type
        else service.files().get_media(fileId=file_id)
    )

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_obj)
    loop = asyncio.get_event_loop()
    done = False
    while not done:
        status, done = await loop.run_in_executor(None, downloader.next_chunk)

    file_content_bytes = fh.getvalue()
    size_bytes = len(file_content_bytes)
    size_kb = size_bytes / 1024 if size_bytes else 0

    if is_stateless_mode():
        result_lines = [
            "File downloaded successfully!",
            f"File: {file_name}",
            f"File ID: {file_id}",
            f"Size: {size_kb:.1f} KB ({size_bytes} bytes)",
            f"MIME Type: {output_mime_type}",
            "\nStateless mode: File storage disabled.",
            "\nBase64-encoded content (first 100 characters shown):",
            f"{base64.b64encode(file_content_bytes[:100]).decode('utf-8')}...",
        ]
        logger.info(f"[get_drive_file_download_url] Successfully downloaded {size_kb:.1f} KB file (stateless mode)")
        return "\n".join(result_lines)

    try:
        storage = get_attachment_storage()
        base64_data = base64.urlsafe_b64encode(file_content_bytes).decode("utf-8")

        saved_file_id = storage.save_attachment(
            base64_data=base64_data,
            filename=output_filename,
            mime_type=output_mime_type,
        )

        download_url = get_attachment_url(saved_file_id)

        result_lines = [
            "File downloaded successfully!",
            f"File: {file_name}",
            f"File ID: {file_id}",
            f"Size: {size_kb:.1f} KB ({size_bytes} bytes)",
            f"MIME Type: {output_mime_type}",
            f"\nDownload URL: {download_url}",
            "\nThe file has been saved and is available at the URL above.",
            "The file will expire after 1 hour.",
        ]

        if export_mime_type:
            result_lines.append(f"\nNote: Google native file exported to {output_mime_type} format.")

        logger.info(f"[get_drive_file_download_url] Successfully saved {size_kb:.1f} KB file as {saved_file_id}")
        return "\n".join(result_lines)

    except Exception as e:
        logger.error(f"[get_drive_file_download_url] Failed to save file: {e}")
        return (
            f"Error: Failed to save file for download.\n"
            f"File was downloaded successfully ({size_kb:.1f} KB) but could not be saved.\n\n"
            f"Error details: {str(e)}"
        )


@server.tool()
@handle_http_errors("create_drive_file", service_type="drive")
@require_google_service("drive", "drive_file")
async def create_drive_file(
    service,
    user_google_email: str,
    file_name: str,
    content: str | None = None,
    folder_id: str = "root",
    mime_type: str = "text/plain",
    fileUrl: str | None = None,
) -> str:
    """
    Creates a new file in Google Drive, supporting creation within shared drives.
    Accepts either direct content or a fileUrl to fetch the content from.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_name (str): The name for the new file.
        content (Optional[str]): If provided, the content to write to the file.
        folder_id (str): The ID of the parent folder. Defaults to 'root'. For shared drives, this must be a folder ID within the shared drive.
        mime_type (str): The MIME type of the file. Defaults to 'text/plain'.
        fileUrl (Optional[str]): If provided, fetches the file content from this URL. Supports file://, http://, and https:// protocols.

    Returns:
        str: Confirmation message of the successful file creation with file link.
    """
    logger.info(
        f"[create_drive_file] Invoked. Email: '{user_google_email}', File Name: {file_name}, Folder ID: {folder_id}, fileUrl: {fileUrl}"
    )

    if not content and not fileUrl:
        raise ValidationError("You must provide either 'content' or 'fileUrl'.")

    file_data = None
    created_file = None
    resolved_folder_id = await resolve_folder_id(service, folder_id)

    file_metadata = {
        "name": file_name,
        "parents": [resolved_folder_id],
        "mimeType": mime_type,
    }

    if fileUrl:
        logger.info(f"[create_drive_file] Fetching file from URL: {fileUrl}")

        parsed_url = urlparse(fileUrl)
        if parsed_url.scheme == "file":
            logger.info("[create_drive_file] Detected file:// URL, reading from local filesystem")
            transport_mode = get_transport_mode()
            running_streamable = transport_mode == "streamable-http"
            if running_streamable:
                logger.warning(
                    "[create_drive_file] file:// URL requested while server runs in streamable-http mode. Ensure the file path is accessible to the server (e.g., Docker volume) or use an HTTP(S) URL."
                )

            raw_path = parsed_url.path or ""
            netloc = parsed_url.netloc
            if netloc and netloc.lower() != "localhost":
                raw_path = f"//{netloc}{raw_path}"
            file_path = url2pathname(raw_path)

            path_obj = Path(file_path)
            if not path_obj.exists():
                extra = (
                    " The server is running via streamable-http, so file:// URLs must point to files inside the container or remote host."
                    if running_streamable
                    else ""
                )
                raise ValidationError(f"Local file does not exist: {file_path}.{extra}")
            if not path_obj.is_file():
                extra = (
                    " In streamable-http/Docker deployments, mount the file into the container or provide an HTTP(S) URL."
                    if running_streamable
                    else ""
                )
                raise ValidationError(f"Path is not a file: {file_path}.{extra}")

            logger.info(f"[create_drive_file] Reading local file: {file_path}")

            file_data = await asyncio.to_thread(path_obj.read_bytes)
            total_bytes = len(file_data)
            logger.info(f"[create_drive_file] Read {total_bytes} bytes from local file")

            media = MediaIoBaseUpload(
                io.BytesIO(file_data),
                mimetype=mime_type,
                resumable=True,
                chunksize=UPLOAD_CHUNK_SIZE_BYTES,
            )

            logger.info("[create_drive_file] Starting upload to Google Drive...")
            created_file = await asyncio.to_thread(
                service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, webViewLink",
                    supportsAllDrives=True,
                )
                .execute
            )
        elif parsed_url.scheme in ("http", "https"):
            if is_stateless_mode():
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    resp = await client.get(fileUrl)
                    if resp.status_code != 200:
                        raise ValidationError(f"Failed to fetch file from URL: {fileUrl} (status {resp.status_code})")
                    file_data = await resp.aread()
                    content_type = resp.headers.get("Content-Type")
                    if content_type and content_type != "application/octet-stream":
                        mime_type = content_type
                        file_metadata["mimeType"] = content_type
                        logger.info(f"[create_drive_file] Using MIME type from Content-Type header: {content_type}")

                media = MediaIoBaseUpload(
                    io.BytesIO(file_data),
                    mimetype=mime_type,
                    resumable=True,
                    chunksize=UPLOAD_CHUNK_SIZE_BYTES,
                )

                created_file = await asyncio.to_thread(
                    service.files()
                    .create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, name, webViewLink",
                        supportsAllDrives=True,
                    )
                    .execute
                )
            else:
                with NamedTemporaryFile() as temp_file:
                    total_bytes = 0
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        async with client.stream("GET", fileUrl) as resp:
                            if resp.status_code != 200:
                                raise ValidationError(
                                    f"Failed to fetch file from URL: {fileUrl} (status {resp.status_code})"
                                )

                            async for chunk in resp.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES):
                                await asyncio.to_thread(temp_file.write, chunk)
                                total_bytes += len(chunk)

                            logger.info(f"[create_drive_file] Downloaded {total_bytes} bytes from URL before upload.")

                            content_type = resp.headers.get("Content-Type")
                            if content_type and content_type != "application/octet-stream":
                                mime_type = content_type
                                file_metadata["mimeType"] = mime_type
                                logger.info(
                                    f"[create_drive_file] Using MIME type from Content-Type header: {mime_type}"
                                )

                    temp_file.seek(0)

                    media = MediaIoBaseUpload(
                        temp_file,
                        mimetype=mime_type,
                        resumable=True,
                        chunksize=UPLOAD_CHUNK_SIZE_BYTES,
                    )

                    logger.info("[create_drive_file] Starting upload to Google Drive...")
                    created_file = await asyncio.to_thread(
                        service.files()
                        .create(
                            body=file_metadata,
                            media_body=media,
                            fields="id, name, webViewLink",
                            supportsAllDrives=True,
                        )
                        .execute
                    )
        else:
            if not parsed_url.scheme:
                raise ValidationError("fileUrl is missing a URL scheme. Use file://, http://, or https://.")
            raise ValidationError(
                f"Unsupported URL scheme '{parsed_url.scheme}'. Only file://, http://, and https:// are supported."
            )
    elif content:
        file_data = content.encode("utf-8")
        media = io.BytesIO(file_data)

        created_file = await asyncio.to_thread(
            service.files()
            .create(
                body=file_metadata,
                media_body=MediaIoBaseUpload(media, mimetype=mime_type, resumable=True),
                fields="id, name, webViewLink",
                supportsAllDrives=True,
            )
            .execute
        )

    if created_file is None:
        raise ValidationError("Failed to create file - no content source was processed.")

    link = created_file.get("webViewLink", "No link available")
    confirmation_message = f"Successfully created file '{created_file.get('name', file_name)}' (ID: {created_file.get('id', 'N/A')}) in folder '{folder_id}' for {user_google_email}. Link: {link}"
    logger.info(f"Successfully created file. Link: {link}")
    return confirmation_message


@server.tool()
@handle_http_errors("update_drive_file", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def update_drive_file(
    service,
    user_google_email: str,
    file_id: str,
    name: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
    add_parents: str | None = None,
    remove_parents: str | None = None,
    starred: bool | None = None,
    trashed: bool | None = None,
    writers_can_share: bool | None = None,
    copy_requires_writer_permission: bool | None = None,
    properties: dict | None = None,
) -> str:
    """
    Updates metadata and properties of a Google Drive file.

    Args:
        user_google_email (str): The user's Google email address. Required.
        file_id (str): The ID of the file to update. Required.
        name (Optional[str]): New name for the file.
        description (Optional[str]): New description for the file.
        mime_type (Optional[str]): New MIME type (note: changing type may require content upload).
        add_parents (Optional[str]): Comma-separated folder IDs to add as parents.
        remove_parents (Optional[str]): Comma-separated folder IDs to remove from parents.
        starred (Optional[bool]): Whether to star/unstar the file.
        trashed (Optional[bool]): Whether to move file to/from trash.
        writers_can_share (Optional[bool]): Whether editors can share the file.
        copy_requires_writer_permission (Optional[bool]): Whether copying requires writer permission.
        properties (Optional[dict]): Custom key-value properties for the file.

    Returns:
        str: Confirmation message with details of the updates applied.
    """
    logger.info(f"[update_drive_file] Updating file {file_id} for {user_google_email}")

    current_file_fields = (
        "name, description, mimeType, parents, starred, trashed, webViewLink, "
        "writersCanShare, copyRequiresWriterPermission, properties"
    )
    resolved_file_id, current_file = await resolve_drive_item(
        service,
        file_id,
        extra_fields=current_file_fields,
    )
    file_id = resolved_file_id

    update_body: dict = {}
    if name is not None:
        update_body["name"] = name
    if description is not None:
        update_body["description"] = description
    if mime_type is not None:
        update_body["mimeType"] = mime_type
    if starred is not None:
        update_body["starred"] = starred
    if trashed is not None:
        update_body["trashed"] = trashed
    if writers_can_share is not None:
        update_body["writersCanShare"] = writers_can_share
    if copy_requires_writer_permission is not None:
        update_body["copyRequiresWriterPermission"] = copy_requires_writer_permission
    if properties is not None:
        update_body["properties"] = properties

    async def _resolve_parent_arguments(parent_arg: str | None) -> str | None:
        if not parent_arg:
            return None
        parent_ids = [part.strip() for part in parent_arg.split(",") if part.strip()]
        if not parent_ids:
            return None

        resolved_ids = []
        for parent in parent_ids:
            resolved_parent = await resolve_folder_id(service, parent)
            resolved_ids.append(resolved_parent)
        return ",".join(resolved_ids)

    resolved_add_parents = await _resolve_parent_arguments(add_parents)
    resolved_remove_parents = await _resolve_parent_arguments(remove_parents)

    query_params: dict = {
        "fileId": file_id,
        "supportsAllDrives": True,
        "fields": "id, name, description, mimeType, parents, starred, trashed, webViewLink, writersCanShare, copyRequiresWriterPermission, properties",
    }

    if resolved_add_parents:
        query_params["addParents"] = resolved_add_parents
    if resolved_remove_parents:
        query_params["removeParents"] = resolved_remove_parents

    if update_body:
        query_params["body"] = update_body

    updated_file = await asyncio.to_thread(service.files().update(**query_params).execute)

    output_parts = [f"Successfully updated file: {updated_file.get('name', current_file['name'])}"]
    output_parts.append(f"   File ID: {file_id}")

    changes = []
    if name is not None and name != current_file.get("name"):
        changes.append(f"   - Name: '{current_file.get('name')}' -> '{name}'")
    if description is not None:
        old_desc_value = current_file.get("description")
        new_desc_value = description
        should_report_change = (old_desc_value or "") != (new_desc_value or "")
        if should_report_change:
            old_desc_display = old_desc_value if old_desc_value not in (None, "") else "(empty)"
            new_desc_display = new_desc_value if new_desc_value not in (None, "") else "(empty)"
            changes.append(f"   - Description: {old_desc_display} -> {new_desc_display}")
    if add_parents:
        changes.append(f"   - Added to folder(s): {add_parents}")
    if remove_parents:
        changes.append(f"   - Removed from folder(s): {remove_parents}")
    current_starred = current_file.get("starred")
    if starred is not None and starred != current_starred:
        star_status = "starred" if starred else "unstarred"
        changes.append(f"   - File {star_status}")
    current_trashed = current_file.get("trashed")
    if trashed is not None and trashed != current_trashed:
        trash_status = "moved to trash" if trashed else "restored from trash"
        changes.append(f"   - File {trash_status}")
    current_writers_can_share = current_file.get("writersCanShare")
    if writers_can_share is not None and writers_can_share != current_writers_can_share:
        share_status = "can" if writers_can_share else "cannot"
        changes.append(f"   - Writers {share_status} share the file")
    current_copy_requires_writer_permission = current_file.get("copyRequiresWriterPermission")
    if (
        copy_requires_writer_permission is not None
        and copy_requires_writer_permission != current_copy_requires_writer_permission
    ):
        copy_status = "requires" if copy_requires_writer_permission else "doesn't require"
        changes.append(f"   - Copying {copy_status} writer permission")
    if properties:
        changes.append(f"   - Updated custom properties: {properties}")

    if changes:
        output_parts.append("")
        output_parts.append("Changes applied:")
        output_parts.extend(changes)
    else:
        output_parts.append("   (No changes were made)")

    output_parts.append("")
    output_parts.append(f"View file: {updated_file.get('webViewLink', '#')}")

    return "\n".join(output_parts)
