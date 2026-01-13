"""
Gmail Helper Functions

Internal helper functions for Gmail tools. These are shared across multiple
Gmail tool modules and handle message parsing, formatting, and preparation.
"""

import base64
import logging
from email.mime.text import MIMEText
from html.parser import HTMLParser
from typing import Any, Literal

logger = logging.getLogger(__name__)

HTML_BODY_TRUNCATE_LIMIT = 20000


class _HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML using stdlib."""

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        self._skip = tag in ("script", "style")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self) -> str:
        return " ".join("".join(self._text).split())


def _html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    try:
        parser = _HTMLTextExtractor()
        parser.feed(html)
        return parser.get_text()
    except Exception as e:
        logger.warning(f"Failed to parse HTML, returning raw content: {e}")
        return html


def _extract_message_body(payload):
    """
    Helper function to extract plain text body from a Gmail message payload.
    (Maintained for backward compatibility)

    Args:
        payload (dict): The message payload from Gmail API

    Returns:
        str: The plain text body content, or empty string if not found
    """
    bodies = _extract_message_bodies(payload)
    return bodies.get("text", "")


def _extract_message_bodies(payload):
    """
    Helper function to extract both plain text and HTML bodies from a Gmail message payload.

    Args:
        payload (dict): The message payload from Gmail API

    Returns:
        dict: Dictionary with 'text' and 'html' keys containing body content
    """
    text_body = ""
    html_body = ""
    parts = [payload] if "parts" not in payload else payload.get("parts", [])

    part_queue = list(parts)  # Use a queue for BFS traversal of parts
    while part_queue:
        part = part_queue.pop(0)
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")

        if body_data:
            try:
                decoded_data = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                if mime_type == "text/plain" and not text_body:
                    text_body = decoded_data
                elif mime_type == "text/html" and not html_body:
                    html_body = decoded_data
            except Exception as e:
                logger.warning(f"Failed to decode body part: {e}")

        # Add sub-parts to queue for multipart messages
        if mime_type.startswith("multipart/") and "parts" in part:
            part_queue.extend(part.get("parts", []))

    # Check the main payload if it has body data directly
    if payload.get("body", {}).get("data"):
        try:
            decoded_data = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
            mime_type = payload.get("mimeType", "")
            if mime_type == "text/plain" and not text_body:
                text_body = decoded_data
            elif mime_type == "text/html" and not html_body:
                html_body = decoded_data
        except Exception as e:
            logger.warning(f"Failed to decode main payload body: {e}")

    return {"text": text_body, "html": html_body}


def _format_body_content(text_body: str, html_body: str) -> str:
    """
    Helper function to format message body content with HTML fallback and truncation.
    Detects useless text/plain fallbacks (e.g., "Your client does not support HTML").

    Args:
        text_body: Plain text body content
        html_body: HTML body content

    Returns:
        Formatted body content string
    """
    text_stripped = text_body.strip()
    html_stripped = html_body.strip()

    # Detect useless fallback: HTML comments in text, or HTML is 50x+ longer
    use_html = html_stripped and (
        not text_stripped or "<!--" in text_stripped or len(html_stripped) > len(text_stripped) * 50
    )

    if use_html:
        content = _html_to_text(html_stripped)
        if len(content) > HTML_BODY_TRUNCATE_LIMIT:
            content = content[:HTML_BODY_TRUNCATE_LIMIT] + "\n\n[Content truncated...]"
        return content
    elif text_stripped:
        return text_body
    else:
        return "[No readable content found]"


def _extract_attachments(payload: dict) -> list[dict[str, Any]]:
    """
    Extract attachment metadata from a Gmail message payload.

    Args:
        payload: The message payload from Gmail API

    Returns:
        List of attachment dictionaries with filename, mimeType, size, and attachmentId
    """
    attachments = []

    def search_parts(part):
        """Recursively search for attachments in message parts"""
        # Check if this part is an attachment
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            attachments.append(
                {
                    "filename": part["filename"],
                    "mimeType": part.get("mimeType", "application/octet-stream"),
                    "size": part.get("body", {}).get("size", 0),
                    "attachmentId": part["body"]["attachmentId"],
                }
            )

        # Recursively search sub-parts
        if "parts" in part:
            for subpart in part["parts"]:
                search_parts(subpart)

    # Start searching from the root payload
    search_parts(payload)
    return attachments


def _extract_headers(payload: dict, header_names: list[str]) -> dict[str, str]:
    """
    Extract specified headers from a Gmail message payload.

    Args:
        payload: The message payload from Gmail API
        header_names: List of header names to extract

    Returns:
        Dict mapping header names to their values
    """
    headers = {}
    target_headers = {name.lower(): name for name in header_names}
    for header in payload.get("headers", []):
        header_name_lower = header["name"].lower()
        if header_name_lower in target_headers:
            # Store using the original requested casing
            headers[target_headers[header_name_lower]] = header["value"]
    return headers


def _prepare_gmail_message(
    subject: str,
    body: str,
    to: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    body_format: Literal["plain", "html"] = "plain",
    from_email: str | None = None,
) -> tuple[str, str | None]:
    """
    Prepare a Gmail message with threading support.

    Args:
        subject: Email subject
        body: Email body content
        to: Optional recipient email address
        cc: Optional CC email address
        bcc: Optional BCC email address
        thread_id: Optional Gmail thread ID to reply within
        in_reply_to: Optional Message-ID of the message being replied to
        references: Optional chain of Message-IDs for proper threading
        body_format: Content type for the email body ('plain' or 'html')
        from_email: Optional sender email address

    Returns:
        Tuple of (raw_message, thread_id) where raw_message is base64 encoded
    """
    # Handle reply subject formatting
    reply_subject = subject
    if in_reply_to and not subject.lower().startswith("re:"):
        reply_subject = f"Re: {subject}"

    # Prepare the email
    normalized_format = body_format.lower()
    if normalized_format not in {"plain", "html"}:
        raise ValueError("body_format must be either 'plain' or 'html'.")

    message = MIMEText(body, normalized_format)
    message["Subject"] = reply_subject

    # Add sender if provided
    if from_email:
        message["From"] = from_email

    # Add recipients if provided
    if to:
        message["To"] = to
    if cc:
        message["Cc"] = cc
    if bcc:
        message["Bcc"] = bcc

    # Add reply headers for threading
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to

    if references:
        message["References"] = references

    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return raw_message, thread_id


def _generate_gmail_web_url(item_id: str, account_index: int = 0) -> str:
    """
    Generate Gmail web interface URL for a message or thread ID.
    Uses #all to access messages from any Gmail folder/label (not just inbox).

    Args:
        item_id: Gmail message ID or thread ID
        account_index: Google account index (default 0 for primary account)

    Returns:
        Gmail web interface URL that opens the message/thread in Gmail web interface
    """
    return f"https://mail.google.com/mail/u/{account_index}/#all/{item_id}"


def _format_gmail_results_plain(messages: list, query: str, next_page_token: str | None = None) -> str:
    """Format Gmail search results in clean, LLM-friendly plain text."""
    if not messages:
        return f"No messages found for query: '{query}'"

    lines = [
        f"Found {len(messages)} messages matching '{query}':",
        "",
        "\U0001f4e7 MESSAGES:",
    ]

    for i, msg in enumerate(messages, 1):
        # Handle potential null/undefined message objects
        if not msg or not isinstance(msg, dict):
            lines.extend(
                [
                    f"  {i}. Message: Invalid message data",
                    "     Error: Message object is null or malformed",
                    "",
                ]
            )
            continue

        # Handle potential null/undefined values from Gmail API
        message_id = msg.get("id")
        thread_id = msg.get("threadId")

        # Convert None, empty string, or missing values to "unknown"
        if not message_id:
            message_id = "unknown"
        if not thread_id:
            thread_id = "unknown"

        if message_id != "unknown":
            message_url = _generate_gmail_web_url(message_id)
        else:
            message_url = "N/A"

        if thread_id != "unknown":
            thread_url = _generate_gmail_web_url(thread_id)
        else:
            thread_url = "N/A"

        lines.extend(
            [
                f"  {i}. Message ID: {message_id}",
                f"     Web Link: {message_url}",
                f"     Thread ID: {thread_id}",
                f"     Thread Link: {thread_url}",
                "",
            ]
        )

    lines.extend(
        [
            "\U0001f4a1 USAGE:",
            "  \u2022 Pass the Message IDs **as a list** to get_gmail_messages_content_batch()",
            "    e.g. get_gmail_messages_content_batch(message_ids=[...])",
            "  \u2022 Pass the Thread IDs to get_gmail_thread_content() (single) or get_gmail_threads_content_batch() (batch)",
        ]
    )

    # Add pagination info if there's a next page
    if next_page_token:
        lines.append("")
        lines.append(
            f"\U0001f4c4 PAGINATION: To get the next page, call search_gmail_messages again with page_token='{next_page_token}'"
        )

    return "\n".join(lines)


def _format_thread_content(thread_data: dict, thread_id: str) -> str:
    """
    Helper function to format thread content from Gmail API response.

    Args:
        thread_data (dict): Thread data from Gmail API
        thread_id (str): Thread ID for display

    Returns:
        str: Formatted thread content
    """
    messages = thread_data.get("messages", [])
    if not messages:
        return f"No messages found in thread '{thread_id}'."

    # Extract thread subject from the first message
    first_message = messages[0]
    first_headers = {h["name"]: h["value"] for h in first_message.get("payload", {}).get("headers", [])}
    thread_subject = first_headers.get("Subject", "(no subject)")

    # Build the thread content
    content_lines = [
        f"Thread ID: {thread_id}",
        f"Subject: {thread_subject}",
        f"Messages: {len(messages)}",
        "",
    ]

    # Process each message in the thread
    for i, message in enumerate(messages, 1):
        # Extract headers
        headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}

        sender = headers.get("From", "(unknown sender)")
        date = headers.get("Date", "(unknown date)")
        subject = headers.get("Subject", "(no subject)")

        # Extract both text and HTML bodies
        payload = message.get("payload", {})
        bodies = _extract_message_bodies(payload)
        text_body = bodies.get("text", "")
        html_body = bodies.get("html", "")

        # Format body content with HTML fallback
        body_data = _format_body_content(text_body, html_body)

        # Add message to content
        content_lines.extend(
            [
                f"=== Message {i} ===",
                f"From: {sender}",
                f"Date: {date}",
            ]
        )

        # Only show subject if it's different from thread subject
        if subject != thread_subject:
            content_lines.append(f"Subject: {subject}")

        content_lines.extend(
            [
                "",
                body_data,
                "",
            ]
        )

    return "\n".join(content_lines)
