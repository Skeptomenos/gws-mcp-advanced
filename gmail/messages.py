"""
Gmail Message Tools

This module provides MCP tools for reading, sending, and drafting Gmail messages.
"""

import asyncio
import logging
import ssl
from typing import Any, Literal

from fastapi import Body

from auth.scopes import GMAIL_COMPOSE_SCOPE, GMAIL_SEND_SCOPE
from auth.service_decorator import require_google_service
from core.errors import ValidationError
from core.server import server
from core.utils import handle_http_errors

from .helpers import (
    _extract_attachments,
    _extract_headers,
    _extract_message_bodies,
    _format_body_content,
    _generate_gmail_web_url,
    _prepare_gmail_message,
)

logger = logging.getLogger(__name__)

GMAIL_BATCH_SIZE = 25
GMAIL_REQUEST_DELAY = 0.1
GMAIL_METADATA_HEADERS = ["Subject", "From", "To", "Cc", "Message-ID"]


@server.tool()
@handle_http_errors("get_gmail_message_content", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_read")
async def get_gmail_message_content(service, message_id: str, user_google_email: str) -> str:
    """
    Retrieves the full content (subject, sender, recipients, plain text body) of a specific Gmail message.

    Args:
        message_id (str): The unique ID of the Gmail message to retrieve.
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: The message details including subject, sender, recipients (To, Cc), and body content.
    """
    logger.info(f"[get_gmail_message_content] Invoked. Message ID: '{message_id}', Email: '{user_google_email}'")

    logger.info(f"[get_gmail_message_content] Using service for: {user_google_email}")

    message_metadata = await asyncio.to_thread(
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=GMAIL_METADATA_HEADERS,
        )
        .execute
    )

    headers = _extract_headers(message_metadata.get("payload", {}), GMAIL_METADATA_HEADERS)
    subject = headers.get("Subject", "(no subject)")
    sender = headers.get("From", "(unknown sender)")
    to = headers.get("To", "")
    cc = headers.get("Cc", "")
    rfc822_msg_id = headers.get("Message-ID", "")

    message_full = await asyncio.to_thread(
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full",
        )
        .execute
    )

    payload = message_full.get("payload", {})
    bodies = _extract_message_bodies(payload)
    text_body = bodies.get("text", "")
    html_body = bodies.get("html", "")

    body_data = _format_body_content(text_body, html_body)

    attachments = _extract_attachments(payload)

    content_lines = [
        f"Subject: {subject}",
        f"From:    {sender}",
    ]

    if rfc822_msg_id:
        content_lines.append(f"Message-ID: {rfc822_msg_id}")

    if to:
        content_lines.append(f"To:      {to}")
    if cc:
        content_lines.append(f"Cc:      {cc}")

    content_lines.append(f"\n--- BODY ---\n{body_data or '[No text/plain body found]'}")

    if attachments:
        content_lines.append("\n--- ATTACHMENTS ---")
        for i, att in enumerate(attachments, 1):
            size_kb = att["size"] / 1024
            content_lines.append(
                f"{i}. {att['filename']} ({att['mimeType']}, {size_kb:.1f} KB)\n"
                f"   Attachment ID: {att['attachmentId']}\n"
                f"   Use get_gmail_attachment_content(message_id='{message_id}', attachment_id='{att['attachmentId']}') to download"
            )

    return "\n".join(content_lines)


@server.tool()
@handle_http_errors("get_gmail_messages_content_batch", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_read")
async def get_gmail_messages_content_batch(
    service,
    message_ids: list[str],
    user_google_email: str,
    format: Literal["full", "metadata"] = "full",
) -> str:
    """
    Retrieves the content of multiple Gmail messages in a single batch request.
    Supports up to 25 messages per batch to prevent SSL connection exhaustion.

    Args:
        message_ids (List[str]): List of Gmail message IDs to retrieve (max 25 per batch).
        user_google_email (str): The user's Google email address. Required.
        format (Literal["full", "metadata"]): Message format. "full" includes body, "metadata" only headers.

    Returns:
        str: A formatted list of message contents including subject, sender, recipients (To, Cc), and body (if full format).
    """
    logger.info(
        f"[get_gmail_messages_content_batch] Invoked. Message count: {len(message_ids)}, Email: '{user_google_email}'"
    )

    if not message_ids:
        raise ValidationError("No message IDs provided")

    output_messages = []

    for chunk_start in range(0, len(message_ids), GMAIL_BATCH_SIZE):
        chunk_ids = message_ids[chunk_start : chunk_start + GMAIL_BATCH_SIZE]
        results: dict[str, dict] = {}

        def _batch_callback(request_id, response, exception, results=results):
            results[request_id] = {"data": response, "error": exception}

        try:
            batch = service.new_batch_http_request(callback=_batch_callback)

            for mid in chunk_ids:
                if format == "metadata":
                    req = (
                        service.users()
                        .messages()
                        .get(
                            userId="me",
                            id=mid,
                            format="metadata",
                            metadataHeaders=GMAIL_METADATA_HEADERS,
                        )
                    )
                else:
                    req = service.users().messages().get(userId="me", id=mid, format="full")
                batch.add(req, request_id=mid)

            await asyncio.to_thread(batch.execute)

        except Exception as batch_error:
            logger.warning(
                f"[get_gmail_messages_content_batch] Batch API failed, falling back to sequential processing: {batch_error}"
            )

            async def fetch_message_with_retry(mid: str, max_retries: int = 3):
                for attempt in range(max_retries):
                    try:
                        if format == "metadata":
                            msg = await asyncio.to_thread(
                                service.users()
                                .messages()
                                .get(
                                    userId="me",
                                    id=mid,
                                    format="metadata",
                                    metadataHeaders=GMAIL_METADATA_HEADERS,
                                )
                                .execute
                            )
                        else:
                            msg = await asyncio.to_thread(
                                service.users().messages().get(userId="me", id=mid, format="full").execute
                            )
                        return mid, msg, None
                    except ssl.SSLError as ssl_error:
                        if attempt < max_retries - 1:
                            delay = 2**attempt
                            logger.warning(
                                f"[get_gmail_messages_content_batch] SSL error for message {mid} on attempt {attempt + 1}: {ssl_error}. Retrying in {delay}s..."
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                f"[get_gmail_messages_content_batch] SSL error for message {mid} on final attempt: {ssl_error}"
                            )
                            return mid, None, ssl_error
                    except Exception as e:
                        return mid, None, e

            for mid in chunk_ids:
                mid_result, msg_data, error = await fetch_message_with_retry(mid)
                results[mid_result] = {"data": msg_data, "error": error}
                await asyncio.sleep(GMAIL_REQUEST_DELAY)

        for mid in chunk_ids:
            entry = results.get(mid, {"data": None, "error": "No result"})

            if entry["error"]:
                output_messages.append(f"⚠️ Message {mid}: {entry['error']}\n")
            else:
                message = entry["data"]
                if not message:
                    output_messages.append(f"⚠️ Message {mid}: No data returned\n")
                    continue

                payload = message.get("payload", {})

                if format == "metadata":
                    headers = _extract_headers(payload, GMAIL_METADATA_HEADERS)
                    subject = headers.get("Subject", "(no subject)")
                    sender = headers.get("From", "(unknown sender)")
                    to = headers.get("To", "")
                    cc = headers.get("Cc", "")
                    rfc822_msg_id = headers.get("Message-ID", "")

                    msg_output = f"Message ID: {mid}\nSubject: {subject}\nFrom: {sender}\n"
                    if rfc822_msg_id:
                        msg_output += f"Message-ID: {rfc822_msg_id}\n"

                    if to:
                        msg_output += f"To: {to}\n"
                    if cc:
                        msg_output += f"Cc: {cc}\n"
                    msg_output += f"Web Link: {_generate_gmail_web_url(mid)}\n"

                    output_messages.append(msg_output)
                else:
                    headers = _extract_headers(payload, GMAIL_METADATA_HEADERS)
                    subject = headers.get("Subject", "(no subject)")
                    sender = headers.get("From", "(unknown sender)")
                    to = headers.get("To", "")
                    cc = headers.get("Cc", "")
                    rfc822_msg_id = headers.get("Message-ID", "")

                    bodies = _extract_message_bodies(payload)
                    text_body = bodies.get("text", "")
                    html_body = bodies.get("html", "")

                    body_data = _format_body_content(text_body, html_body)

                    msg_output = f"Message ID: {mid}\nSubject: {subject}\nFrom: {sender}\n"
                    if rfc822_msg_id:
                        msg_output += f"Message-ID: {rfc822_msg_id}\n"

                    if to:
                        msg_output += f"To: {to}\n"
                    if cc:
                        msg_output += f"Cc: {cc}\n"
                    msg_output += f"Web Link: {_generate_gmail_web_url(mid)}\n\n{body_data}\n"

                    output_messages.append(msg_output)

    final_output = f"Retrieved {len(message_ids)} messages:\n\n"
    final_output += "\n---\n\n".join(output_messages)

    return final_output


@server.tool()
@handle_http_errors("get_gmail_attachment_content", is_read_only=True, service_type="gmail")
@require_google_service("gmail", "gmail_read")
async def get_gmail_attachment_content(
    service,
    message_id: str,
    attachment_id: str,
    user_google_email: str,
) -> str:
    """
    Downloads the content of a specific email attachment.

    Args:
        message_id (str): The ID of the Gmail message containing the attachment.
        attachment_id (str): The ID of the attachment to download.
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: Attachment metadata and base64-encoded content that can be decoded and saved.
    """
    logger.info(f"[get_gmail_attachment_content] Invoked. Message ID: '{message_id}', Email: '{user_google_email}'")

    try:
        attachment = await asyncio.to_thread(
            service.users().messages().attachments().get(userId="me", messageId=message_id, id=attachment_id).execute
        )
    except Exception as e:
        logger.error(f"[get_gmail_attachment_content] Failed to download attachment: {e}")
        return (
            f"Error: Failed to download attachment. The attachment ID may have changed.\n"
            f"Please fetch the message content again to get an updated attachment ID.\n\n"
            f"Error details: {str(e)}"
        )

    size_bytes = attachment.get("size", 0)
    size_kb = size_bytes / 1024 if size_bytes else 0
    base64_data = attachment.get("data", "")

    from auth.config import is_stateless_mode

    if is_stateless_mode():
        result_lines = [
            "Attachment downloaded successfully!",
            f"Message ID: {message_id}",
            f"Size: {size_kb:.1f} KB ({size_bytes} bytes)",
            "\n⚠️ Stateless mode: File storage disabled.",
            "\nBase64-encoded content (first 100 characters shown):",
            f"{base64_data[:100]}...",
            "\nNote: Attachment IDs are ephemeral. Always use IDs from the most recent message fetch.",
        ]
        logger.info(
            f"[get_gmail_attachment_content] Successfully downloaded {size_kb:.1f} KB attachment (stateless mode)"
        )
        return "\n".join(result_lines)

    try:
        from core.attachment_storage import get_attachment_storage, get_attachment_url

        storage = get_attachment_storage()

        filename = None
        mime_type = None
        try:
            message_metadata = await asyncio.to_thread(
                service.users().messages().get(userId="me", id=message_id, format="metadata").execute
            )
            payload = message_metadata.get("payload", {})
            attachments = _extract_attachments(payload)
            for att in attachments:
                if att.get("attachmentId") == attachment_id:
                    filename = att.get("filename")
                    mime_type = att.get("mimeType")
                    break
        except Exception:
            logger.debug(f"Could not fetch attachment metadata for {attachment_id}, using defaults")

        file_id = storage.save_attachment(base64_data=base64_data, filename=filename, mime_type=mime_type)

        attachment_url = get_attachment_url(file_id)

        result_lines = [
            "Attachment downloaded successfully!",
            f"Message ID: {message_id}",
            f"Size: {size_kb:.1f} KB ({size_bytes} bytes)",
            f"\n📎 Download URL: {attachment_url}",
            "\nThe attachment has been saved and is available at the URL above.",
            "The file will expire after 1 hour.",
            "\nNote: Attachment IDs are ephemeral. Always use IDs from the most recent message fetch.",
        ]

        logger.info(f"[get_gmail_attachment_content] Successfully saved {size_kb:.1f} KB attachment as {file_id}")
        return "\n".join(result_lines)

    except Exception as e:
        logger.error(
            f"[get_gmail_attachment_content] Failed to save attachment: {e}",
            exc_info=True,
        )
        result_lines = [
            "Attachment downloaded successfully!",
            f"Message ID: {message_id}",
            f"Size: {size_kb:.1f} KB ({size_bytes} bytes)",
            "\n⚠️ Failed to save attachment file. Showing preview instead.",
            "\nBase64-encoded content (first 100 characters shown):",
            f"{base64_data[:100]}...",
            f"\nError: {str(e)}",
            "\nNote: Attachment IDs are ephemeral. Always use IDs from the most recent message fetch.",
        ]
        return "\n".join(result_lines)


@server.tool()
@handle_http_errors("send_gmail_message", service_type="gmail")
@require_google_service("gmail", GMAIL_SEND_SCOPE)
async def send_gmail_message(
    service,
    user_google_email: str,
    to: str = Body(..., description="Recipient email address."),
    subject: str = Body(..., description="Email subject."),
    body: str = Body(..., description="Email body content (plain text or HTML)."),
    body_format: Literal["plain", "html"] = Body(
        "plain",
        description="Email body format. Use 'plain' for plaintext or 'html' for HTML content.",
    ),
    cc: str | None = Body(None, description="Optional CC email address."),
    bcc: str | None = Body(None, description="Optional BCC email address."),
    thread_id: str | None = Body(None, description="Optional Gmail thread ID to reply within."),
    in_reply_to: str | None = Body(None, description="Optional Message-ID of the message being replied to."),
    references: str | None = Body(None, description="Optional chain of Message-IDs for proper threading."),
) -> str:
    """
    Sends an email using the user's Gmail account. Supports both new emails and replies.

    Args:
        to (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body content.
        body_format (Literal['plain', 'html']): Email body format. Defaults to 'plain'.
        cc (Optional[str]): Optional CC email address.
        bcc (Optional[str]): Optional BCC email address.
        user_google_email (str): The user's Google email address. Required.
        thread_id (Optional[str]): Optional Gmail thread ID to reply within. When provided, sends a reply.
        in_reply_to (Optional[str]): Optional Message-ID of the message being replied to. Used for proper threading.
        references (Optional[str]): Optional chain of Message-IDs for proper threading. Should include all previous Message-IDs.

    Returns:
        str: Confirmation message with the sent email's message ID.

    Examples:
        # Send a new email
        send_gmail_message(to="user@example.com", subject="Hello", body="Hi there!")

        # Send an HTML email
        send_gmail_message(
            to="user@example.com",
            subject="Hello",
            body="<strong>Hi there!</strong>",
            body_format="html"
        )

        # Send an email with CC and BCC
        send_gmail_message(
            to="user@example.com",
            cc="manager@example.com",
            bcc="archive@example.com",
            subject="Project Update",
            body="Here's the latest update..."
        )

        # Send a reply
        send_gmail_message(
            to="user@example.com",
            subject="Re: Meeting tomorrow",
            body="Thanks for the update!",
            thread_id="thread_123",
            in_reply_to="<message123@gmail.com>",
            references="<original@gmail.com> <message123@gmail.com>"
        )
    """
    logger.info(f"[send_gmail_message] Invoked. Email: '{user_google_email}', Subject: '{subject}'")

    raw_message, thread_id_final = _prepare_gmail_message(
        subject=subject,
        body=body,
        to=to,
        cc=cc,
        bcc=bcc,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        references=references,
        body_format=body_format,
        from_email=user_google_email,
    )

    send_body: dict[str, Any] = {"raw": raw_message}

    if thread_id_final:
        send_body["threadId"] = thread_id_final

    sent_message = await asyncio.to_thread(service.users().messages().send(userId="me", body=send_body).execute)
    message_id = sent_message.get("id")
    return f"Email sent! Message ID: {message_id}"


@server.tool()
@handle_http_errors("draft_gmail_message", service_type="gmail")
@require_google_service("gmail", GMAIL_COMPOSE_SCOPE)
async def draft_gmail_message(
    service,
    user_google_email: str,
    subject: str = Body(..., description="Email subject."),
    body: str = Body(..., description="Email body (plain text)."),
    body_format: Literal["plain", "html"] = Body(
        "plain",
        description="Email body format. Use 'plain' for plaintext or 'html' for HTML content.",
    ),
    to: str | None = Body(None, description="Optional recipient email address."),
    cc: str | None = Body(None, description="Optional CC email address."),
    bcc: str | None = Body(None, description="Optional BCC email address."),
    thread_id: str | None = Body(None, description="Optional Gmail thread ID to reply within."),
    in_reply_to: str | None = Body(None, description="Optional Message-ID of the message being replied to."),
    references: str | None = Body(None, description="Optional chain of Message-IDs for proper threading."),
) -> str:
    """
    Creates a draft email in the user's Gmail account. Supports both new drafts and reply drafts.

    Args:
        user_google_email (str): The user's Google email address. Required.
        subject (str): Email subject.
        body (str): Email body (plain text).
        body_format (Literal['plain', 'html']): Email body format. Defaults to 'plain'.
        to (Optional[str]): Optional recipient email address. Can be left empty for drafts.
        cc (Optional[str]): Optional CC email address.
        bcc (Optional[str]): Optional BCC email address.
        thread_id (Optional[str]): Optional Gmail thread ID to reply within. When provided, creates a reply draft.
        in_reply_to (Optional[str]): Optional Message-ID of the message being replied to. Used for proper threading.
        references (Optional[str]): Optional chain of Message-IDs for proper threading. Should include all previous Message-IDs.

    Returns:
        str: Confirmation message with the created draft's ID.

    Examples:
        # Create a new draft
        draft_gmail_message(subject="Hello", body="Hi there!", to="user@example.com")

        # Create a plaintext draft with CC and BCC
        draft_gmail_message(
            subject="Project Update",
            body="Here's the latest update...",
            to="user@example.com",
            cc="manager@example.com",
            bcc="archive@example.com"
        )

        # Create a HTML draft with CC and BCC
        draft_gmail_message(
            subject="Project Update",
            body="<strong>Hi there!</strong>",
            body_format="html",
            to="user@example.com",
            cc="manager@example.com",
            bcc="archive@example.com"
        )

        # Create a reply draft in plaintext
        draft_gmail_message(
            subject="Re: Meeting tomorrow",
            body="Thanks for the update!",
            to="user@example.com",
            thread_id="thread_123",
            in_reply_to="<message123@gmail.com>",
            references="<original@gmail.com> <message123@gmail.com>"
        )

        # Create a reply draft in HTML
        draft_gmail_message(
            subject="Re: Meeting tomorrow",
            body="<strong>Thanks for the update!</strong>",
            body_format="html,
            to="user@example.com",
            thread_id="thread_123",
            in_reply_to="<message123@gmail.com>",
            references="<original@gmail.com> <message123@gmail.com>"
        )
    """
    logger.info(f"[draft_gmail_message] Invoked. Email: '{user_google_email}', Subject: '{subject}'")

    raw_message, thread_id_final = _prepare_gmail_message(
        subject=subject,
        body=body,
        body_format=body_format,
        to=to,
        cc=cc,
        bcc=bcc,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        references=references,
        from_email=user_google_email,
    )

    draft_body: dict[str, Any] = {"message": {"raw": raw_message}}

    if thread_id_final:
        draft_body["message"]["threadId"] = thread_id_final

    created_draft = await asyncio.to_thread(service.users().drafts().create(userId="me", body=draft_body).execute)
    draft_id = created_draft.get("id")
    return f"Draft created! Draft ID: {draft_id}"
