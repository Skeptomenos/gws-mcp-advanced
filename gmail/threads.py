"""
Gmail Thread Tools

This module provides MCP tools for retrieving Gmail conversation threads.
"""

import asyncio
import logging
import ssl

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

from .helpers import _format_thread_content

logger = logging.getLogger(__name__)

GMAIL_BATCH_SIZE = 25
GMAIL_REQUEST_DELAY = 0.1


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
