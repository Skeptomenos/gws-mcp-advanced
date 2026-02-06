"""
Google Calendar MCP Tools

This module provides MCP tools for interacting with Google Calendar API.
"""

import asyncio
import datetime
import logging
import re
import uuid
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.service_decorator import require_google_service
from core.errors import APIError, ValidationError
from core.server import server
from core.utils import handle_http_errors
from gcalendar.calendar_helpers import (
    _apply_transparency_if_valid,
    _apply_visibility_if_valid,
    _correct_time_format_for_api,
    _format_attachment_details,
    _format_attendee_details,
    _normalize_attendees,
    _parse_reminders_json,
    _preserve_existing_fields,
)

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("list_calendars", is_read_only=True, service_type="calendar")
@require_google_service("calendar", "calendar_read")
async def list_calendars(service, user_google_email: str) -> str:
    """
    Retrieves a list of calendars accessible to the authenticated user.

    Args:
        user_google_email (str): The user's Google email address. Required.

    Returns:
        str: A formatted list of the user's calendars (summary, ID, primary status).
    """
    logger.info(f"[list_calendars] Invoked. Email: '{user_google_email}'")

    calendar_list_response = await asyncio.to_thread(lambda: service.calendarList().list().execute())
    items = calendar_list_response.get("items", [])
    if not items:
        return f"No calendars found for {user_google_email}."

    calendars_summary_list = [
        f'- "{cal.get("summary", "No Summary")}"{" (Primary)" if cal.get("primary") else ""} (ID: {cal["id"]})'
        for cal in items
    ]
    text_output = f"Successfully listed {len(items)} calendars for {user_google_email}:\n" + "\n".join(
        calendars_summary_list
    )
    logger.info(f"Successfully listed {len(items)} calendars for {user_google_email}.")
    return text_output


@server.tool()
@handle_http_errors("get_events", is_read_only=True, service_type="calendar")
@require_google_service("calendar", "calendar_read")
async def get_events(
    service,
    user_google_email: str,
    calendar_id: str = "primary",
    event_id: str | None = None,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 25,
    query: str | None = None,
    detailed: bool = False,
    include_attachments: bool = False,
) -> str:
    """
    Retrieves events from a specified Google Calendar. Can retrieve a single event by ID or multiple events within a time range.
    You can also search for events by keyword by supplying the optional "query" param.

    Args:
        user_google_email (str): The user's Google email address. Required.
        calendar_id (str): The ID of the calendar to query. Use 'primary' for the user's primary calendar. Defaults to 'primary'. Calendar IDs can be obtained using `list_calendars`.
        event_id (Optional[str]): The ID of a specific event to retrieve. If provided, retrieves only this event and ignores time filtering parameters.
        time_min (Optional[str]): The start of the time range (inclusive) in RFC3339 format (e.g., '2024-05-12T10:00:00Z' or '2024-05-12'). If omitted, defaults to the current time. Ignored if event_id is provided.
        time_max (Optional[str]): The end of the time range (exclusive) in RFC3339 format. If omitted, events starting from `time_min` onwards are considered (up to `max_results`). Ignored if event_id is provided.
        max_results (int): The maximum number of events to return. Defaults to 25. Ignored if event_id is provided.
        query (Optional[str]): A keyword to search for within event fields (summary, description, location). Ignored if event_id is provided.
        detailed (bool): Whether to return detailed event information including description, location, attendees, and attendee details (response status, organizer, optional flags). Defaults to False.
        include_attachments (bool): Whether to include attachment information in detailed event output. When True, shows attachment details (fileId, fileUrl, mimeType, title) for events that have attachments. Only applies when detailed=True. Set this to True when you need to view or access files that have been attached to calendar events, such as meeting documents, presentations, or other shared files. Defaults to False.

    Returns:
        str: A formatted list of events (summary, start and end times, link) within the specified range, or detailed information for a single event if event_id is provided.
    """
    logger.info(
        f"[get_events] Raw parameters - event_id: '{event_id}', time_min: '{time_min}', time_max: '{time_max}', query: '{query}', detailed: {detailed}, include_attachments: {include_attachments}"
    )

    # Handle single event retrieval
    if event_id:
        logger.info(f"[get_events] Retrieving single event with ID: {event_id}")
        event = await asyncio.to_thread(
            lambda: service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        )
        items = [event]
    else:
        # Handle multiple events retrieval with time filtering
        # Ensure time_min and time_max are correctly formatted for the API
        formatted_time_min = _correct_time_format_for_api(time_min, "time_min")
        if formatted_time_min:
            effective_time_min = formatted_time_min
        else:
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            effective_time_min = utc_now.isoformat().replace("+00:00", "Z")
        if time_min is None:
            logger.info(f"time_min not provided, defaulting to current UTC time: {effective_time_min}")
        else:
            logger.info(
                f"time_min processing: original='{time_min}', formatted='{formatted_time_min}', effective='{effective_time_min}'"
            )

        effective_time_max = _correct_time_format_for_api(time_max, "time_max")
        if time_max:
            logger.info(f"time_max processing: original='{time_max}', formatted='{effective_time_max}'")

        logger.info(
            f"[get_events] Final API parameters - calendarId: '{calendar_id}', timeMin: '{effective_time_min}', timeMax: '{effective_time_max}', maxResults: {max_results}, query: '{query}'"
        )

        # Build the request parameters dynamically
        request_params = {
            "calendarId": calendar_id,
            "timeMin": effective_time_min,
            "timeMax": effective_time_max,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if query:
            request_params["q"] = query

        events_result = await asyncio.to_thread(lambda: service.events().list(**request_params).execute())
        items = events_result.get("items", [])
    if not items:
        if event_id:
            return f"Event with ID '{event_id}' not found in calendar '{calendar_id}' for {user_google_email}."
        else:
            return f"No events found in calendar '{calendar_id}' for {user_google_email} for the specified time range."

    # Handle returning detailed output for a single event when requested
    if event_id and detailed:
        item = items[0]
        summary = item.get("summary", "No Title")
        start = item["start"].get("dateTime", item["start"].get("date"))
        end = item["end"].get("dateTime", item["end"].get("date"))
        link = item.get("htmlLink", "No Link")
        description = item.get("description", "No Description")
        location = item.get("location", "No Location")
        color_id = item.get("colorId", "None")
        attendees = item.get("attendees", [])
        attendee_emails = ", ".join([a.get("email", "") for a in attendees]) if attendees else "None"
        attendee_details_str = _format_attendee_details(attendees, indent="  ")

        event_details = (
            f"Event Details:\n"
            f"- Title: {summary}\n"
            f"- Starts: {start}\n"
            f"- Ends: {end}\n"
            f"- Description: {description}\n"
            f"- Location: {location}\n"
            f"- Color ID: {color_id}\n"
            f"- Attendees: {attendee_emails}\n"
            f"- Attendee Details: {attendee_details_str}\n"
        )

        if include_attachments:
            attachments = item.get("attachments", [])
            attachment_details_str = _format_attachment_details(attachments, indent="  ")
            event_details += f"- Attachments: {attachment_details_str}\n"

        event_details += f"- Event ID: {event_id}\n- Link: {link}"
        logger.info(f"[get_events] Successfully retrieved detailed event {event_id} for {user_google_email}.")
        return event_details

    # Handle multiple events or single event with basic output
    event_details_list = []
    for item in items:
        summary = item.get("summary", "No Title")
        start_time = item["start"].get("dateTime", item["start"].get("date"))
        end_time = item["end"].get("dateTime", item["end"].get("date"))
        link = item.get("htmlLink", "No Link")
        item_event_id = item.get("id", "No ID")

        if detailed:
            # Add detailed information for multiple events
            description = item.get("description", "No Description")
            location = item.get("location", "No Location")
            attendees = item.get("attendees", [])
            attendee_emails = ", ".join([a.get("email", "") for a in attendees]) if attendees else "None"
            attendee_details_str = _format_attendee_details(attendees, indent="    ")

            event_detail_parts = (
                f'- "{summary}" (Starts: {start_time}, Ends: {end_time})\n'
                f"  Description: {description}\n"
                f"  Location: {location}\n"
                f"  Attendees: {attendee_emails}\n"
                f"  Attendee Details: {attendee_details_str}\n"
            )

            if include_attachments:
                attachments = item.get("attachments", [])
                attachment_details_str = _format_attachment_details(attachments, indent="    ")
                event_detail_parts += f"  Attachments: {attachment_details_str}\n"

            event_detail_parts += f"  ID: {item_event_id} | Link: {link}"
            event_details_list.append(event_detail_parts)
        else:
            # Basic output format
            event_details_list.append(
                f'- "{summary}" (Starts: {start_time}, Ends: {end_time}) ID: {item_event_id} | Link: {link}'
            )

    if event_id:
        # Single event basic output
        text_output = (
            f"Successfully retrieved event from calendar '{calendar_id}' for {user_google_email}:\n"
            + "\n".join(event_details_list)
        )
    else:
        # Multiple events output
        text_output = (
            f"Successfully retrieved {len(items)} events from calendar '{calendar_id}' for {user_google_email}:\n"
            + "\n".join(event_details_list)
        )

    logger.info(f"Successfully retrieved {len(items)} events for {user_google_email}.")
    return text_output


@server.tool()
@handle_http_errors("create_event", service_type="calendar")
@require_google_service("calendar", "calendar_events")
async def create_event(
    service,
    user_google_email: str,
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    timezone: str | None = None,
    attachments: list[str] | None = None,
    add_google_meet: bool = False,
    reminders: str | None = None,
    use_default_reminders: bool = True,
    transparency: str | None = None,
    visibility: str | None = None,
) -> str:
    """
    Creates a new event.

    Args:
        user_google_email (str): The user's Google email address. Required.
        summary (str): Event title.
        start_time (str): Start time (RFC3339, e.g., "2023-10-27T10:00:00-07:00" or "2023-10-27" for all-day).
        end_time (str): End time (RFC3339, e.g., "2023-10-27T11:00:00-07:00" or "2023-10-28" for all-day).
        calendar_id (str): Calendar ID (default: 'primary').
        description (Optional[str]): Event description.
        location (Optional[str]): Event location.
        attendees (Optional[List[str]]): Attendee email addresses.
        timezone (Optional[str]): Timezone (e.g., "America/New_York").
        attachments (Optional[List[str]]): List of Google Drive file URLs or IDs to attach to the event.
        add_google_meet (bool): Whether to add a Google Meet video conference to the event. Defaults to False.
        reminders (Optional[Union[str, List[Dict[str, Any]]]]): JSON string or list of reminder objects. Each should have 'method' ("popup" or "email") and 'minutes' (0-40320). Max 5 reminders. Example: '[{"method": "popup", "minutes": 15}]' or [{"method": "popup", "minutes": 15}]
        use_default_reminders (bool): Whether to use calendar's default reminders. If False, uses custom reminders. Defaults to True.
        transparency (Optional[str]): Event transparency for busy/free status. "opaque" shows as Busy (default), "transparent" shows as Available/Free. Defaults to None (uses Google Calendar default).
        visibility (Optional[str]): Event visibility. "default" uses calendar default, "public" is visible to all, "private" is visible only to attendees, "confidential" is same as private (legacy). Defaults to None (uses Google Calendar default).

    Returns:
        str: Confirmation message of the successful event creation with event link.
    """
    logger.info(f"[create_event] Invoked. Email: '{user_google_email}', Summary: {summary}")
    logger.info(f"[create_event] Incoming attachments param: {attachments}")
    # If attachments value is a string, split by comma and strip whitespace
    if attachments and isinstance(attachments, str):
        attachments = [a.strip() for a in attachments.split(",") if a.strip()]
        logger.info(f"[create_event] Parsed attachments list from string: {attachments}")
    event_body: dict[str, Any] = {
        "summary": summary,
        "start": ({"date": start_time} if "T" not in start_time else {"dateTime": start_time}),
        "end": ({"date": end_time} if "T" not in end_time else {"dateTime": end_time}),
    }
    if location:
        event_body["location"] = location
    if description:
        event_body["description"] = description
    if timezone:
        if "dateTime" in event_body["start"]:
            event_body["start"]["timeZone"] = timezone
        if "dateTime" in event_body["end"]:
            event_body["end"]["timeZone"] = timezone
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]

    # Handle reminders
    if reminders is not None or not use_default_reminders:
        # If custom reminders are provided, automatically disable default reminders
        effective_use_default = use_default_reminders and reminders is None

        reminder_data: dict[str, bool | list[dict[str, str | int]]] = {"useDefault": effective_use_default}
        if reminders is not None:
            validated_reminders = _parse_reminders_json(reminders, "create_event")
            if validated_reminders:
                reminder_data["overrides"] = validated_reminders
                logger.info(f"[create_event] Added {len(validated_reminders)} custom reminders")
                if use_default_reminders:
                    logger.info("[create_event] Custom reminders provided - disabling default reminders")

        event_body["reminders"] = reminder_data

    # Handle transparency validation
    _apply_transparency_if_valid(event_body, transparency, "create_event")

    # Handle visibility validation
    _apply_visibility_if_valid(event_body, visibility, "create_event")

    if add_google_meet:
        request_id = str(uuid.uuid4())
        event_body["conferenceData"] = {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
        logger.info(f"[create_event] Adding Google Meet conference with request ID: {request_id}")

    if attachments:
        # Accept both file URLs and file IDs. If a URL, extract the fileId.
        event_body["attachments"] = []
        drive_service = None
        try:
            drive_service = service._http and build("drive", "v3", http=service._http)
        except Exception as e:
            logger.warning(f"Could not build Drive service for MIME type lookup: {e}")
        for att in attachments:
            file_id = None
            if att.startswith("https://"):
                # Match /d/<id>, /file/d/<id>, ?id=<id>
                match = re.search(r"(?:/d/|/file/d/|id=)([\w-]+)", att)
                file_id = match.group(1) if match else None
                logger.info(f"[create_event] Extracted file_id '{file_id}' from attachment URL '{att}'")
            else:
                file_id = att
                logger.info(f"[create_event] Using direct file_id '{file_id}' for attachment")
            if file_id:
                file_url = f"https://drive.google.com/open?id={file_id}"
                mime_type = "application/vnd.google-apps.drive-sdk"
                title = "Drive Attachment"
                # Try to get the actual MIME type and filename from Drive
                if drive_service:
                    try:
                        file_metadata = await asyncio.to_thread(
                            lambda fid=file_id: drive_service.files()  # type: ignore[misc]
                            .get(
                                fileId=fid,
                                fields="mimeType,name",
                                supportsAllDrives=True,
                            )
                            .execute()
                        )
                        mime_type = file_metadata.get("mimeType", mime_type)
                        filename = file_metadata.get("name")
                        if filename:
                            title = filename
                            logger.info(f"[create_event] Using filename '{filename}' as attachment title")
                        else:
                            logger.info("[create_event] No filename found, using generic title")
                    except Exception as e:
                        logger.warning(f"Could not fetch metadata for file {file_id}: {e}")
                event_body["attachments"].append(
                    {
                        "fileUrl": file_url,
                        "title": title,
                        "mimeType": mime_type,
                    }
                )
        created_event = await asyncio.to_thread(
            lambda: service.events()
            .insert(
                calendarId=calendar_id,
                body=event_body,
                supportsAttachments=True,
                conferenceDataVersion=1 if add_google_meet else 0,
            )
            .execute()
        )
    else:
        created_event = await asyncio.to_thread(
            lambda: service.events()
            .insert(
                calendarId=calendar_id,
                body=event_body,
                conferenceDataVersion=1 if add_google_meet else 0,
            )
            .execute()
        )
    link = created_event.get("htmlLink", "No link available")
    confirmation_message = (
        f"Successfully created event '{created_event.get('summary', summary)}' for {user_google_email}. Link: {link}"
    )

    # Add Google Meet information if conference was created
    if add_google_meet and "conferenceData" in created_event:
        conference_data = created_event["conferenceData"]
        if "entryPoints" in conference_data:
            for entry_point in conference_data["entryPoints"]:
                if entry_point.get("entryPointType") == "video":
                    meet_link = entry_point.get("uri", "")
                    if meet_link:
                        confirmation_message += f" Google Meet: {meet_link}"
                        break

    logger.info(f"Event created successfully for {user_google_email}. ID: {created_event.get('id')}, Link: {link}")
    return confirmation_message


@server.tool()
@handle_http_errors("modify_event", service_type="calendar")
@require_google_service("calendar", "calendar_events")
async def modify_event(
    service,
    user_google_email: str,
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    location: str | None = None,
    attendees: str | None = None,
    timezone: str | None = None,
    add_google_meet: bool | None = None,
    reminders: str | None = None,
    use_default_reminders: bool | None = None,
    transparency: str | None = None,
    visibility: str | None = None,
    color_id: str | None = None,
) -> str:
    """
    Modifies an existing event.

    Args:
        user_google_email (str): The user's Google email address. Required.
        event_id (str): The ID of the event to modify.
        calendar_id (str): Calendar ID (default: 'primary').
        summary (Optional[str]): New event title.
        start_time (Optional[str]): New start time (RFC3339, e.g., "2023-10-27T10:00:00-07:00" or "2023-10-27" for all-day).
        end_time (Optional[str]): New end time (RFC3339, e.g., "2023-10-27T11:00:00-07:00" or "2023-10-28" for all-day).
        description (Optional[str]): New event description.
        location (Optional[str]): New event location.
        attendees (Optional[Union[List[str], List[Dict[str, Any]]]]): Attendees as email strings or objects with metadata. Supports: ["email@example.com"] or [{"email": "email@example.com", "responseStatus": "accepted", "organizer": true, "optional": true}]. When using objects, existing metadata (responseStatus, organizer, optional) is preserved. New attendees default to responseStatus="needsAction".
        timezone (Optional[str]): New timezone (e.g., "America/New_York").
        add_google_meet (Optional[bool]): Whether to add or remove Google Meet video conference. If True, adds Google Meet; if False, removes it; if None, leaves unchanged.
        reminders (Optional[Union[str, List[Dict[str, Any]]]]): JSON string or list of reminder objects to replace existing reminders. Each should have 'method' ("popup" or "email") and 'minutes' (0-40320). Max 5 reminders. Example: '[{"method": "popup", "minutes": 15}]' or [{"method": "popup", "minutes": 15}]
        use_default_reminders (Optional[bool]): Whether to use calendar's default reminders. If specified, overrides current reminder settings.
        transparency (Optional[str]): Event transparency for busy/free status. "opaque" shows as Busy, "transparent" shows as Available/Free. If None, preserves existing transparency setting.
        visibility (Optional[str]): Event visibility. "default" uses calendar default, "public" is visible to all, "private" is visible only to attendees, "confidential" is same as private (legacy). If None, preserves existing visibility setting.
        color_id (Optional[str]): Event color ID (1-11). If None, preserves existing color.

    Returns:
        str: Confirmation message of the successful event modification with event link.
    """
    logger.info(f"[modify_event] Invoked. Email: '{user_google_email}', Event ID: {event_id}")

    # Build the event body with only the fields that are provided
    event_body: dict[str, Any] = {}
    if summary is not None:
        event_body["summary"] = summary
    if start_time is not None:
        event_body["start"] = {"date": start_time} if "T" not in start_time else {"dateTime": start_time}
        if timezone is not None and "dateTime" in event_body["start"]:
            event_body["start"]["timeZone"] = timezone
    if end_time is not None:
        event_body["end"] = {"date": end_time} if "T" not in end_time else {"dateTime": end_time}
        if timezone is not None and "dateTime" in event_body["end"]:
            event_body["end"]["timeZone"] = timezone
    if description is not None:
        event_body["description"] = description
    if location is not None:
        event_body["location"] = location

    # Normalize attendees - accepts both email strings and full attendee objects
    normalized_attendees = _normalize_attendees(attendees)
    if normalized_attendees is not None:
        event_body["attendees"] = normalized_attendees

    if color_id is not None:
        event_body["colorId"] = color_id

    # Handle reminders
    if reminders is not None or use_default_reminders is not None:
        reminder_data: dict[str, bool | list[dict[str, str | int]]] = {}
        if use_default_reminders is not None:
            reminder_data["useDefault"] = use_default_reminders
        else:
            # Preserve existing event's useDefault value if not explicitly specified
            try:
                existing_event = await asyncio.to_thread(
                    lambda: service.events().get(calendarId=calendar_id, eventId=event_id).execute()
                )
                reminder_data["useDefault"] = existing_event.get("reminders", {}).get("useDefault", True)
            except Exception as e:
                logger.warning(f"[modify_event] Could not fetch existing event for reminders: {e}")
                reminder_data["useDefault"] = True

        # If custom reminders are provided, automatically disable default reminders
        if reminders is not None:
            if reminder_data.get("useDefault", False):
                reminder_data["useDefault"] = False
                logger.info("[modify_event] Custom reminders provided - disabling default reminders")

            validated_reminders = _parse_reminders_json(reminders, "modify_event")
            if reminders and not validated_reminders:
                logger.warning(
                    "[modify_event] Reminders provided but failed validation. No custom reminders will be set."
                )
            elif validated_reminders:
                reminder_data["overrides"] = validated_reminders
                logger.info(f"[modify_event] Updated reminders with {len(validated_reminders)} custom reminders")

        event_body["reminders"] = reminder_data

    # Handle transparency validation
    _apply_transparency_if_valid(event_body, transparency, "modify_event")

    # Handle visibility validation
    _apply_visibility_if_valid(event_body, visibility, "modify_event")

    if timezone is not None and "start" not in event_body and "end" not in event_body:
        # If timezone is provided but start/end times are not, we need to fetch the existing event
        # to apply the timezone correctly. This is a simplification; a full implementation
        # might handle this more robustly or require start/end with timezone.
        # For now, we'll log a warning and skip applying timezone if start/end are missing.
        logger.warning(
            "[modify_event] Timezone provided but start_time and end_time are missing. Timezone will not be applied unless start/end times are also provided."
        )

    if not event_body:
        message = "No fields provided to modify the event."
        logger.warning(f"[modify_event] {message}")
        raise ValidationError(message)

    # Log the event ID for debugging
    logger.info(f"[modify_event] Attempting to update event with ID: '{event_id}' in calendar '{calendar_id}'")

    # Get the existing event to preserve fields that aren't being updated
    try:
        existing_event = await asyncio.to_thread(
            lambda: service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        )
        logger.info("[modify_event] Successfully retrieved existing event before update")

        # Preserve existing fields if not provided in the update
        _preserve_existing_fields(
            event_body,
            existing_event,
            {
                "summary": summary,
                "description": description,
                "location": location,
                # Use the already-normalized attendee objects (if provided); otherwise preserve existing
                "attendees": event_body.get("attendees"),
                "colorId": event_body.get("colorId"),
            },
        )

        # Handle Google Meet conference data
        if add_google_meet is not None:
            if add_google_meet:
                # Add Google Meet
                request_id = str(uuid.uuid4())
                event_body["conferenceData"] = {
                    "createRequest": {
                        "requestId": request_id,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                }
                logger.info(f"[modify_event] Adding Google Meet conference with request ID: {request_id}")
            else:
                # Remove Google Meet by setting conferenceData to empty
                event_body["conferenceData"] = {}
                logger.info("[modify_event] Removing Google Meet conference")
        elif "conferenceData" in existing_event:
            # Preserve existing conference data if not specified
            event_body["conferenceData"] = existing_event["conferenceData"]
            logger.info("[modify_event] Preserving existing conference data")

    except HttpError as get_error:
        if get_error.resp.status == 404:
            logger.error(f"[modify_event] Event not found during pre-update verification: {get_error}")
            message = f"Event not found during verification. The event with ID '{event_id}' could not be found in calendar '{calendar_id}'. This may be due to incorrect ID format or the event no longer exists."
            raise APIError(message) from get_error
        else:
            logger.warning(
                f"[modify_event] Error during pre-update verification, but proceeding with update: {get_error}"
            )

    # Proceed with the update
    updated_event = await asyncio.to_thread(
        lambda: service.events()
        .update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_body,
            conferenceDataVersion=1,
        )
        .execute()
    )

    link = updated_event.get("htmlLink", "No link available")
    confirmation_message = f"Successfully modified event '{updated_event.get('summary', summary)}' (ID: {event_id}) for {user_google_email}. Link: {link}"

    # Add Google Meet information if conference was added
    if add_google_meet is True and "conferenceData" in updated_event:
        conference_data = updated_event["conferenceData"]
        if "entryPoints" in conference_data:
            for entry_point in conference_data["entryPoints"]:
                if entry_point.get("entryPointType") == "video":
                    meet_link = entry_point.get("uri", "")
                    if meet_link:
                        confirmation_message += f" Google Meet: {meet_link}"
                        break
    elif add_google_meet is False:
        confirmation_message += " (Google Meet removed)"

    logger.info(f"Event modified successfully for {user_google_email}. ID: {updated_event.get('id')}, Link: {link}")
    return confirmation_message


@server.tool()
@handle_http_errors("delete_event", service_type="calendar")
@require_google_service("calendar", "calendar_events")
async def delete_event(service, user_google_email: str, event_id: str, calendar_id: str = "primary") -> str:
    """
    Deletes an existing event.

    Args:
        user_google_email (str): The user's Google email address. Required.
        event_id (str): The ID of the event to delete.
        calendar_id (str): Calendar ID (default: 'primary').

    Returns:
        str: Confirmation message of the successful event deletion.
    """
    logger.info(f"[delete_event] Invoked. Email: '{user_google_email}', Event ID: {event_id}")

    # Log the event ID for debugging
    logger.info(f"[delete_event] Attempting to delete event with ID: '{event_id}' in calendar '{calendar_id}'")

    # Try to get the event first to verify it exists
    try:
        await asyncio.to_thread(lambda: service.events().get(calendarId=calendar_id, eventId=event_id).execute())
        logger.info("[delete_event] Successfully verified event exists before deletion")
    except HttpError as get_error:
        if get_error.resp.status == 404:
            logger.error(f"[delete_event] Event not found during pre-delete verification: {get_error}")
            message = f"Event not found during verification. The event with ID '{event_id}' could not be found in calendar '{calendar_id}'. This may be due to incorrect ID format or the event no longer exists."
            raise APIError(message) from get_error
        else:
            logger.warning(
                f"[delete_event] Error during pre-delete verification, but proceeding with deletion: {get_error}"
            )

    # Proceed with the deletion
    await asyncio.to_thread(lambda: service.events().delete(calendarId=calendar_id, eventId=event_id).execute())

    confirmation_message = (
        f"Successfully deleted event (ID: {event_id}) from calendar '{calendar_id}' for {user_google_email}."
    )
    logger.info(f"Event deleted successfully for {user_google_email}. ID: {event_id}")
    return confirmation_message
