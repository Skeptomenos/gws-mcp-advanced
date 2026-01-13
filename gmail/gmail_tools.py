"""
Google Gmail MCP Tools

This module provides MCP tools for interacting with the Gmail API.
"""

import asyncio
import logging
import ssl
from typing import Any, Literal

from fastapi import Body
from pydantic import Field

from auth.scopes import (
    GMAIL_COMPOSE_SCOPE,
    GMAIL_LABELS_SCOPE,
    GMAIL_MODIFY_SCOPE,
    GMAIL_SEND_SCOPE,
)
from auth.service_decorator import require_google_service
from core.errors import ValidationError
from core.server import server
from core.utils import handle_http_errors

from .helpers import (
    _extract_attachments,
    _extract_headers,
    _extract_message_bodies,
    _format_body_content,
    _format_gmail_results_plain,
    _format_thread_content,
    _generate_gmail_web_url,
    _prepare_gmail_message,
)

logger = logging.getLogger(__name__)

GMAIL_BATCH_SIZE = 25
GMAIL_REQUEST_DELAY = 0.1
GMAIL_METADATA_HEADERS = ["Subject", "From", "To", "Cc", "Message-ID"]


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


@server.tool()
@require_google_service("gmail", "gmail_read")
@handle_http_errors("get_gmail_thread_content", is_read_only=True, service_type="gmail")
async def get_gmail_thread_content(service, thread_id: str, user_google_email: str) -> str:
    """
    Retrieves the complete content of a Gmail conversation thread, including all messages.

    Args:
        thread_id (str): The unique ID of the Gmail thread to retrieve.
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: The complete thread content with all messages formatted for reading.
    """
    logger.info(f"[get_gmail_thread_content] Invoked. Thread ID: '{thread_id}', Email: '{user_google_email}'")

    thread_response = await asyncio.to_thread(
        service.users().threads().get(userId="me", id=thread_id, format="full").execute
    )

    return _format_thread_content(thread_response, thread_id)


@server.tool()
@require_google_service("gmail", "gmail_read")
@handle_http_errors("get_gmail_threads_content_batch", is_read_only=True, service_type="gmail")
async def get_gmail_threads_content_batch(
    service,
    thread_ids: list[str],
    user_google_email: str,
) -> str:
    """
    Retrieves the content of multiple Gmail threads in a single batch request.
    Supports up to 25 threads per batch to prevent SSL connection exhaustion.

    Args:
        thread_ids (List[str]): A list of Gmail thread IDs to retrieve. The function will automatically batch requests in chunks of 25.
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: A formatted list of thread contents with separators.
    """
    logger.info(
        f"[get_gmail_threads_content_batch] Invoked. Thread count: {len(thread_ids)}, Email: '{user_google_email}'"
    )

    if not thread_ids:
        raise ValueError("No thread IDs provided")

    output_threads = []
    results: dict[str, dict] = {}

    def _batch_callback(request_id, response, exception):
        results[request_id] = {"data": response, "error": exception}

    for chunk_start in range(0, len(thread_ids), GMAIL_BATCH_SIZE):
        chunk_ids = thread_ids[chunk_start : chunk_start + GMAIL_BATCH_SIZE]
        results.clear()

        try:
            batch = service.new_batch_http_request(callback=_batch_callback)

            for tid in chunk_ids:
                req = service.users().threads().get(userId="me", id=tid, format="full")
                batch.add(req, request_id=tid)

            await asyncio.to_thread(batch.execute)

        except Exception as batch_error:
            logger.warning(
                f"[get_gmail_threads_content_batch] Batch API failed, falling back to sequential processing: {batch_error}"
            )

            async def fetch_thread_with_retry(tid: str, max_retries: int = 3):
                for attempt in range(max_retries):
                    try:
                        thread = await asyncio.to_thread(
                            service.users().threads().get(userId="me", id=tid, format="full").execute
                        )
                        return tid, thread, None
                    except ssl.SSLError as ssl_error:
                        if attempt < max_retries - 1:
                            delay = 2**attempt
                            logger.warning(
                                f"[get_gmail_threads_content_batch] SSL error for thread {tid} on attempt {attempt + 1}: {ssl_error}. Retrying in {delay}s..."
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                f"[get_gmail_threads_content_batch] SSL error for thread {tid} on final attempt: {ssl_error}"
                            )
                            return tid, None, ssl_error
                    except Exception as e:
                        return tid, None, e

            for tid in chunk_ids:
                tid_result, thread_data, error = await fetch_thread_with_retry(tid)
                results[tid_result] = {"data": thread_data, "error": error}
                await asyncio.sleep(GMAIL_REQUEST_DELAY)

        for tid in chunk_ids:
            entry = results.get(tid, {"data": None, "error": "No result"})

            if entry["error"]:
                output_threads.append(f"⚠️ Thread {tid}: {entry['error']}\n")
            else:
                thread = entry["data"]
                if not thread:
                    output_threads.append(f"⚠️ Thread {tid}: No data returned\n")
                    continue

                output_threads.append(_format_thread_content(thread, tid))

    header = f"Retrieved {len(thread_ids)} threads:"
    return header + "\n\n" + "\n---\n\n".join(output_threads)


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
