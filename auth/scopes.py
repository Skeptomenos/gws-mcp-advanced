"""
Google Workspace OAuth Scopes

This module centralizes OAuth scope definitions for Google Workspace integration.
Separated from service_decorator.py to avoid circular imports.
"""

import logging

logger = logging.getLogger(__name__)

# Global variable to store enabled tools (set by main.py)
_ENABLED_TOOLS = None

# Individual OAuth Scope Constants
USERINFO_EMAIL_SCOPE = "https://www.googleapis.com/auth/userinfo.email"
USERINFO_PROFILE_SCOPE = "https://www.googleapis.com/auth/userinfo.profile"
OPENID_SCOPE = "openid"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"

# Google Drive scopes
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"

# Google Docs scopes
DOCS_READONLY_SCOPE = "https://www.googleapis.com/auth/documents.readonly"
DOCS_WRITE_SCOPE = "https://www.googleapis.com/auth/documents"

# Gmail API scopes
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
GMAIL_LABELS_SCOPE = "https://www.googleapis.com/auth/gmail.labels"
GMAIL_SETTINGS_BASIC_SCOPE = "https://www.googleapis.com/auth/gmail.settings.basic"

# Google Chat API scopes
CHAT_READONLY_SCOPE = "https://www.googleapis.com/auth/chat.messages.readonly"
CHAT_WRITE_SCOPE = "https://www.googleapis.com/auth/chat.messages"
CHAT_SPACES_SCOPE = "https://www.googleapis.com/auth/chat.spaces"

# Google Sheets API scopes
SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
SHEETS_WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"

# Google Forms API scopes
FORMS_BODY_SCOPE = "https://www.googleapis.com/auth/forms.body"
FORMS_BODY_READONLY_SCOPE = "https://www.googleapis.com/auth/forms.body.readonly"
FORMS_RESPONSES_READONLY_SCOPE = "https://www.googleapis.com/auth/forms.responses.readonly"

# Google Slides API scopes
SLIDES_SCOPE = "https://www.googleapis.com/auth/presentations"
SLIDES_READONLY_SCOPE = "https://www.googleapis.com/auth/presentations.readonly"

# Google Tasks API scopes
TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"
TASKS_READONLY_SCOPE = "https://www.googleapis.com/auth/tasks.readonly"

# Google Custom Search API scope
CUSTOM_SEARCH_SCOPE = "https://www.googleapis.com/auth/cse"

# Base OAuth scopes required for user identification
BASE_SCOPES = [USERINFO_EMAIL_SCOPE, USERINFO_PROFILE_SCOPE, OPENID_SCOPE]

# Service-specific scope groups
DOCS_SCOPES = [DOCS_READONLY_SCOPE, DOCS_WRITE_SCOPE]

CALENDAR_SCOPES = [CALENDAR_SCOPE, CALENDAR_READONLY_SCOPE, CALENDAR_EVENTS_SCOPE]

DRIVE_SCOPES = [DRIVE_SCOPE, DRIVE_READONLY_SCOPE, DRIVE_FILE_SCOPE]

GMAIL_SCOPES = [
    GMAIL_READONLY_SCOPE,
    GMAIL_SEND_SCOPE,
    GMAIL_COMPOSE_SCOPE,
    GMAIL_MODIFY_SCOPE,
    GMAIL_LABELS_SCOPE,
    GMAIL_SETTINGS_BASIC_SCOPE,
]

CHAT_SCOPES = [CHAT_READONLY_SCOPE, CHAT_WRITE_SCOPE, CHAT_SPACES_SCOPE]

SHEETS_SCOPES = [SHEETS_READONLY_SCOPE, SHEETS_WRITE_SCOPE]

FORMS_SCOPES = [
    FORMS_BODY_SCOPE,
    FORMS_BODY_READONLY_SCOPE,
    FORMS_RESPONSES_READONLY_SCOPE,
]

SLIDES_SCOPES = [SLIDES_SCOPE, SLIDES_READONLY_SCOPE]

TASKS_SCOPES = [TASKS_SCOPE, TASKS_READONLY_SCOPE]

CUSTOM_SEARCH_SCOPES = [CUSTOM_SEARCH_SCOPE]

# Tool-to-scopes mapping
TOOL_SCOPES_MAP = {
    "gmail": GMAIL_SCOPES,
    "drive": DRIVE_SCOPES,
    "calendar": CALENDAR_SCOPES,
    "docs": DOCS_SCOPES,
    "sheets": SHEETS_SCOPES,
    "chat": CHAT_SCOPES,
    "forms": FORMS_SCOPES,
    "slides": SLIDES_SCOPES,
    "tasks": TASKS_SCOPES,
    "search": CUSTOM_SEARCH_SCOPES,
}


def set_enabled_tools(enabled_tools: list[str] | None) -> None:
    """
    Set the globally enabled tools list.

    Args:
        enabled_tools: List of enabled tool names.
    """
    global _ENABLED_TOOLS
    _ENABLED_TOOLS = enabled_tools
    logger.info(f"Enabled tools set for scope management: {enabled_tools}")


def get_scopes_for_tools(enabled_tools: list[str] | None = None) -> list[str]:
    """
    Returns OAuth scopes for the specified or enabled tools.

    Args:
        enabled_tools: List of tool names to get scopes for.
                      If None, uses globally set tools via set_enabled_tools().
                      If no global tools set, returns scopes for all tools.

    Returns:
        List of unique OAuth scopes including base scopes.
    """
    # Use provided tools, or fall back to global, or fall back to all
    if enabled_tools is None:
        enabled_tools = _ENABLED_TOOLS
    if enabled_tools is None:
        enabled_tools = list(TOOL_SCOPES_MAP.keys())

    # Start with base scopes (always required)
    scopes = BASE_SCOPES.copy()

    # Add scopes for each enabled tool
    for tool in enabled_tools:
        if tool in TOOL_SCOPES_MAP:
            scopes.extend(TOOL_SCOPES_MAP[tool])

    logger.debug(f"Generated scopes for tools {list(enabled_tools)}: {len(set(scopes))} unique scopes")
    return list(set(scopes))


def get_current_scopes() -> list[str]:
    """
    Returns scopes for currently enabled tools.

    Deprecated: Use get_scopes_for_tools() instead.
    """
    return get_scopes_for_tools()


# Combined scopes for all supported Google Workspace operations (backwards compatibility)
SCOPES = get_scopes_for_tools()
