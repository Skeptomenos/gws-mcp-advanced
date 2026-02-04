"""
Helper functions for Google Calendar tools.

This module contains pure utility functions that don't depend on
the MCP server or authentication decorators, enabling easier testing.
"""

import datetime
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _parse_reminders_json(reminders_input: str | None, function_name: str) -> list[dict[str, Any]]:
    """
    Parse reminders from JSON string or list object and validate them.

    Args:
        reminders_input: JSON string containing reminder objects or list of reminder objects
        function_name: Name of calling function for logging

    Returns:
        List of validated reminder objects
    """
    if not reminders_input:
        return []

    try:
        reminders = json.loads(reminders_input)
        if not isinstance(reminders, list):
            logger.warning(f"[{function_name}] Reminders must be a JSON array, got {type(reminders).__name__}")
            return []
    except json.JSONDecodeError as e:
        logger.warning(f"[{function_name}] Invalid JSON for reminders: {e}")
        return []

    if len(reminders) > 5:
        logger.warning(f"[{function_name}] More than 5 reminders provided, truncating to first 5")
        reminders = reminders[:5]

    validated_reminders = []
    for reminder in reminders:
        if not isinstance(reminder, dict) or "method" not in reminder or "minutes" not in reminder:
            logger.warning(f"[{function_name}] Invalid reminder format: {reminder}, skipping")
            continue

        method = reminder["method"].lower()
        if method not in ["popup", "email"]:
            logger.warning(
                f"[{function_name}] Invalid reminder method '{method}', must be 'popup' or 'email', skipping"
            )
            continue

        minutes = reminder["minutes"]
        if not isinstance(minutes, int) or minutes < 0 or minutes > 40320:
            logger.warning(f"[{function_name}] Invalid reminder minutes '{minutes}', must be integer 0-40320, skipping")
            continue

        validated_reminders.append({"method": method, "minutes": minutes})

    return validated_reminders


def _apply_transparency_if_valid(
    event_body: dict[str, Any],
    transparency: str | None,
    function_name: str,
) -> None:
    """
    Apply transparency to the event body if the provided value is valid.

    Args:
        event_body: Event payload being constructed.
        transparency: Provided transparency value.
        function_name: Name of the calling function for logging context.
    """
    if transparency is None:
        return

    valid_transparency_values = ["opaque", "transparent"]
    if transparency in valid_transparency_values:
        event_body["transparency"] = transparency
        logger.info(f"[{function_name}] Set transparency to '{transparency}'")
    else:
        logger.warning(
            f"[{function_name}] Invalid transparency value '{transparency}', must be 'opaque' or 'transparent', skipping"
        )


def _apply_visibility_if_valid(
    event_body: dict[str, Any],
    visibility: str | None,
    function_name: str,
) -> None:
    """
    Apply visibility to the event body if the provided value is valid.

    Args:
        event_body: Event payload being constructed.
        visibility: Provided visibility value.
        function_name: Name of the calling function for logging context.
    """
    if visibility is None:
        return

    valid_visibility_values = ["default", "public", "private", "confidential"]
    if visibility in valid_visibility_values:
        event_body["visibility"] = visibility
        logger.info(f"[{function_name}] Set visibility to '{visibility}'")
    else:
        logger.warning(
            f"[{function_name}] Invalid visibility value '{visibility}', must be 'default', 'public', 'private', or 'confidential', skipping"
        )


def _preserve_existing_fields(
    event_body: dict[str, Any],
    existing_event: dict[str, Any],
    field_mappings: dict[str, Any],
) -> None:
    """
    Helper function to preserve existing event fields when not explicitly provided.

    Args:
        event_body: The event body being built for the API call
        existing_event: The existing event data from the API
        field_mappings: Dict mapping field names to their new values (None means preserve existing)
    """
    for field_name, new_value in field_mappings.items():
        if new_value is None and field_name in existing_event:
            event_body[field_name] = existing_event[field_name]
            logger.info(f"[modify_event] Preserving existing {field_name}")
        elif new_value is not None:
            event_body[field_name] = new_value


def _format_attendee_details(attendees: list[dict[str, Any]], indent: str = "  ") -> str:
    """
    Format attendee details including response status, organizer, and optional flags.

    Args:
        attendees: List of attendee dictionaries from Google Calendar API
        indent: Indentation to use for newline-separated attendees (default: "  ")

    Returns:
        Formatted string with attendee details, or "None" if no attendees
    """
    if not attendees:
        return "None"

    attendee_details_list = []
    for a in attendees:
        email = a.get("email", "unknown")
        response_status = a.get("responseStatus", "unknown")
        optional = a.get("optional", False)
        organizer = a.get("organizer", False)

        detail_parts = [f"{email}: {response_status}"]
        if organizer:
            detail_parts.append("(organizer)")
        if optional:
            detail_parts.append("(optional)")

        attendee_details_list.append(" ".join(detail_parts))

    return f"\n{indent}".join(attendee_details_list)


def _format_attachment_details(attachments: list[dict[str, Any]], indent: str = "  ") -> str:
    """
    Format attachment details including file information.

    Args:
        attachments: List of attachment dictionaries from Google Calendar API
        indent: Indentation to use for newline-separated attachments (default: "  ")

    Returns:
        Formatted string with attachment details, or "None" if no attachments
    """
    if not attachments:
        return "None"

    attachment_details_list = []
    for att in attachments:
        title = att.get("title", "Untitled")
        file_url = att.get("fileUrl", "No URL")
        file_id = att.get("fileId", "No ID")
        mime_type = att.get("mimeType", "Unknown")

        attachment_info = (
            f"{title}\n{indent}File URL: {file_url}\n{indent}File ID: {file_id}\n{indent}MIME Type: {mime_type}"
        )
        attachment_details_list.append(attachment_info)

    return f"\n{indent}".join(attachment_details_list)


def _correct_time_format_for_api(time_str: str | None, param_name: str) -> str | None:
    """
    Ensure time strings for API calls are correctly formatted.

    Args:
        time_str: Time string to format
        param_name: Parameter name for logging

    Returns:
        Formatted time string or None
    """
    if not time_str:
        return None

    logger.info(f"_correct_time_format_for_api: Processing {param_name} with value '{time_str}'")

    if len(time_str) == 10 and time_str.count("-") == 2:
        try:
            datetime.datetime.strptime(time_str, "%Y-%m-%d")
            formatted = f"{time_str}T00:00:00Z"
            logger.info(f"Formatting date-only {param_name} '{time_str}' to RFC3339: '{formatted}'")
            return formatted
        except ValueError:
            logger.warning(f"{param_name} '{time_str}' looks like a date but is not valid YYYY-MM-DD. Using as is.")
            return time_str

    if (
        len(time_str) == 19
        and time_str[10] == "T"
        and time_str.count(":") == 2
        and not (time_str.endswith("Z") or ("+" in time_str[10:]) or ("-" in time_str[10:]))
    ):
        try:
            datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
            logger.info(f"Formatting {param_name} '{time_str}' by appending 'Z' for UTC.")
            return time_str + "Z"
        except ValueError:
            logger.warning(
                f"{param_name} '{time_str}' looks like it needs 'Z' but is not valid YYYY-MM-DDTHH:MM:SS. Using as is."
            )
            return time_str

    logger.info(f"{param_name} '{time_str}' doesn't need formatting, using as is.")
    return time_str


def _normalize_attendees(
    attendees: str | None,
) -> list[dict[str, Any]] | None:
    """
    Normalize attendees input to list of attendee objects.

    Accepts a JSON string representing either:
    - List of email strings: '["user@example.com", "other@example.com"]'
    - List of attendee objects: '[{"email": "user@example.com", "responseStatus": "accepted"}]'
    - Mixed list of both formats

    Returns list of attendee dicts with at minimum 'email' key.
    """
    if attendees is None:
        return None

    try:
        parsed = json.loads(attendees)
    except json.JSONDecodeError as e:
        raise ValueError(f"attendees must be a valid JSON array: {e}") from e

    if not isinstance(parsed, list):
        raise ValueError(f"attendees must be a JSON array, got {type(parsed).__name__}")

    normalized = []
    for att in parsed:
        if isinstance(att, str):
            normalized.append({"email": att})
        elif isinstance(att, dict) and "email" in att:
            normalized.append(att)
        else:
            logger.warning(f"[_normalize_attendees] Invalid attendee format: {att}, skipping")
    return normalized if normalized else None
