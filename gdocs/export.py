"""
Google Docs Export Tools

This module provides MCP tools for exporting Google Docs to other formats.
"""

import asyncio
import io
import logging
from typing import Any

from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("export_doc_to_pdf", service_type="drive")
@require_google_service("drive", "drive_file")
async def export_doc_to_pdf(
    service: Any,
    user_google_email: str,
    document_id: str,
    pdf_filename: str = None,
    folder_id: str = None,
) -> str:
    """
    Exports a Google Doc to PDF format and saves it to Google Drive.

    Args:
        user_google_email: User's Google email address
        document_id: ID of the Google Doc to export
        pdf_filename: Name for the PDF file (optional - if not provided, uses original name + "_PDF")
        folder_id: Drive folder ID to save PDF in (optional - if not provided, saves in root)

    Returns:
        str: Confirmation message with PDF file details and links
    """
    logger.info(
        f"[export_doc_to_pdf] Email={user_google_email}, Doc={document_id}, pdf_filename={pdf_filename}, folder_id={folder_id}"
    )

    try:
        file_metadata = await asyncio.to_thread(
            service.files()
            .get(
                fileId=document_id,
                fields="id, name, mimeType, webViewLink",
                supportsAllDrives=True,
            )
            .execute
        )
    except Exception as e:
        return f"Error: Could not access document {document_id}: {str(e)}"

    mime_type = file_metadata.get("mimeType", "")
    original_name = file_metadata.get("name", "Unknown Document")
    web_view_link = file_metadata.get("webViewLink", "#")

    if mime_type != "application/vnd.google-apps.document":
        return f"Error: File '{original_name}' is not a Google Doc (MIME type: {mime_type}). Only native Google Docs can be exported to PDF."

    logger.info(f"[export_doc_to_pdf] Exporting '{original_name}' to PDF")

    try:
        request_obj = service.files().export_media(fileId=document_id, mimeType="application/pdf")

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_obj)

        done = False
        while not done:
            _, done = await asyncio.to_thread(downloader.next_chunk)

        pdf_content = fh.getvalue()
        pdf_size = len(pdf_content)

    except Exception as e:
        return f"Error: Failed to export document to PDF: {str(e)}"

    if not pdf_filename:
        pdf_filename = f"{original_name}_PDF.pdf"
    elif not pdf_filename.endswith(".pdf"):
        pdf_filename += ".pdf"

    try:
        fh.seek(0)
        media = MediaIoBaseUpload(fh, mimetype="application/pdf", resumable=True)

        upload_metadata = {"name": pdf_filename, "mimeType": "application/pdf"}

        if folder_id:
            upload_metadata["parents"] = [folder_id]

        uploaded_file = await asyncio.to_thread(
            service.files()
            .create(
                body=upload_metadata,
                media_body=media,
                fields="id, name, webViewLink, parents",
                supportsAllDrives=True,
            )
            .execute
        )

        pdf_file_id = uploaded_file.get("id")
        pdf_web_link = uploaded_file.get("webViewLink", "#")
        pdf_parents = uploaded_file.get("parents", [])

        logger.info(f"[export_doc_to_pdf] Successfully uploaded PDF to Drive: {pdf_file_id}")

        folder_info = ""
        if folder_id:
            folder_info = f" in folder {folder_id}"
        elif pdf_parents:
            folder_info = f" in folder {pdf_parents[0]}"

        return f"Successfully exported '{original_name}' to PDF and saved to Drive as '{pdf_filename}' (ID: {pdf_file_id}, {pdf_size:,} bytes){folder_info}. PDF: {pdf_web_link} | Original: {web_view_link}"

    except Exception as e:
        return f"Error: Failed to upload PDF to Drive: {str(e)}. PDF was generated successfully ({pdf_size:,} bytes) but could not be saved to Drive."
