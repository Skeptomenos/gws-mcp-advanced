#!/usr/bin/env python3
"""Cleanup utility for live MCP test artifacts.

This script removes artifacts created by live test lanes using strict ownership
signals:
1) name/title must start with the configured artifact prefix
2) resource timestamp must be older than the retention cutoff

Safety defaults:
1) dry-run by default
2) explicit --execute required for deletion
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from auth.credential_store import get_credential_store
from auth.oauth_clients import resolve_oauth_client_for_user

logger = logging.getLogger(__name__)

SUPPORTED_SERVICES = {"drive", "calendar", "tasks"}


@dataclass
class CleanupStats:
    """Aggregate cleanup statistics for one service."""

    scanned: int = 0
    matched: int = 0
    deleted: int = 0
    failed: int = 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup live MCP test artifacts by prefix and retention.")
    parser.add_argument(
        "--user-email",
        default=os.getenv("MCP_TEST_USER_EMAIL") or os.getenv("USER_GOOGLE_EMAIL"),
        help="Google account email used by live tests (default: MCP_TEST_USER_EMAIL or USER_GOOGLE_EMAIL).",
    )
    parser.add_argument(
        "--artifact-prefix",
        default=os.getenv("MCP_TEST_PREFIX", "codex-it-"),
        help="Artifact name prefix to match (default: MCP_TEST_PREFIX or 'codex-it-').",
    )
    parser.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="Only delete artifacts older than this many hours (default: 24).",
    )
    parser.add_argument(
        "--services",
        default="drive,calendar,tasks",
        help="Comma-separated cleanup targets: drive,calendar,tasks,all (default: drive,calendar,tasks).",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=500,
        help="Maximum number of matching artifacts per service to process (default: 500).",
    )
    parser.add_argument(
        "--oauth-client-key",
        default=None,
        help="Optional OAuth client key override for credential lookup.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply destructive deletes. Omit to run dry-run only.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def _parse_services(raw: str) -> set[str]:
    entries = {item.strip().lower() for item in raw.split(",") if item.strip()}
    if not entries:
        raise ValueError("services list cannot be empty")
    if "all" in entries:
        return set(SUPPORTED_SERVICES)
    invalid = sorted(entries - SUPPORTED_SERVICES)
    if invalid:
        raise ValueError(
            f"Unsupported services: {', '.join(invalid)}. Supported: {', '.join(sorted(SUPPORTED_SERVICES))}"
        )
    return entries


def _parse_rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_owned_and_old(name: str | None, updated_at: str | None, prefix: str, cutoff: datetime) -> bool:
    if not name or not name.startswith(prefix):
        return False
    parsed = _parse_rfc3339(updated_at)
    if parsed is None:
        return False
    return parsed <= cutoff


def _escape_drive_query_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _resolve_credentials(user_email: str, oauth_client_key: str | None) -> Credentials:
    store = get_credential_store()
    credentials: Credentials | None = None

    resolved_client_key = oauth_client_key
    if not resolved_client_key:
        try:
            selection = resolve_oauth_client_for_user(user_email)
            if selection.client_key != "legacy-env":
                resolved_client_key = selection.client_key
        except Exception as exc:
            logger.debug("OAuth client selection not available for cleanup: %s", exc)

    if resolved_client_key and hasattr(store, "get_credential_for_client"):
        credentials = store.get_credential_for_client(resolved_client_key, user_email)  # type: ignore[attr-defined]

    if credentials is None:
        credentials = store.get_credential(user_email)

    if credentials is None:
        raise RuntimeError(
            f"No credentials found for '{user_email}'. Authenticate first or provide a configured credential store."
        )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    return credentials


def _build_service(api: str, version: str, credentials: Credentials) -> Resource:
    return build(api, version, credentials=credentials, cache_discovery=False)


def cleanup_drive_files(
    drive_service: Resource,
    *,
    prefix: str,
    cutoff: datetime,
    execute: bool,
    max_items: int,
) -> CleanupStats:
    stats = CleanupStats()
    page_token: str | None = None
    query = (
        f"trashed=false and name contains '{_escape_drive_query_literal(prefix)}' "
        f"and modifiedTime < '{cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')}'"
    )

    while stats.matched < max_items:
        response = (
            drive_service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                corpora="allDrives",
                pageSize=min(100, max_items - stats.matched),
                pageToken=page_token,
            )
            .execute()
        )
        files = response.get("files", [])
        stats.scanned += len(files)
        for item in files:
            if stats.matched >= max_items:
                break
            name = item.get("name")
            modified = item.get("modifiedTime")
            if not _is_owned_and_old(name, modified, prefix, cutoff):
                continue
            stats.matched += 1
            file_id = item.get("id")
            if not execute:
                continue
            try:
                drive_service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
                stats.deleted += 1
            except HttpError as exc:
                logger.error("Drive delete failed for %s (%s): %s", name, file_id, exc)
                stats.failed += 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return stats


def cleanup_calendar_events(
    calendar_service: Resource,
    *,
    prefix: str,
    cutoff: datetime,
    execute: bool,
    max_items: int,
    calendar_id: str = "primary",
) -> CleanupStats:
    stats = CleanupStats()
    page_token: str | None = None

    while stats.matched < max_items:
        response = (
            calendar_service.events()
            .list(
                calendarId=calendar_id,
                q=prefix,
                timeMax=cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
                singleEvents=True,
                showDeleted=False,
                maxResults=min(250, max_items - stats.matched),
                pageToken=page_token,
            )
            .execute()
        )

        events = response.get("items", [])
        stats.scanned += len(events)
        for item in events:
            if stats.matched >= max_items:
                break
            summary = item.get("summary")
            updated = item.get("updated")
            if not _is_owned_and_old(summary, updated, prefix, cutoff):
                continue
            stats.matched += 1
            if not execute:
                continue
            event_id = item.get("id")
            try:
                calendar_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                stats.deleted += 1
            except HttpError as exc:
                logger.error("Calendar delete failed for %s (%s): %s", summary, event_id, exc)
                stats.failed += 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return stats


def cleanup_task_lists(
    tasks_service: Resource,
    *,
    prefix: str,
    cutoff: datetime,
    execute: bool,
    max_items: int,
) -> CleanupStats:
    stats = CleanupStats()
    page_token: str | None = None

    while stats.matched < max_items:
        response = (
            tasks_service.tasklists()
            .list(maxResults=min(100, max_items - stats.matched), pageToken=page_token)
            .execute()
        )
        task_lists = response.get("items", [])
        stats.scanned += len(task_lists)

        for item in task_lists:
            if stats.matched >= max_items:
                break
            title = item.get("title")
            updated = item.get("updated")
            if not _is_owned_and_old(title, updated, prefix, cutoff):
                continue
            stats.matched += 1
            if not execute:
                continue
            tasklist_id = item.get("id")
            try:
                tasks_service.tasklists().delete(tasklist=tasklist_id).execute()
                stats.deleted += 1
            except HttpError as exc:
                logger.error("Task list delete failed for %s (%s): %s", title, tasklist_id, exc)
                stats.failed += 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return stats


def _print_summary(service_name: str, stats: CleanupStats, execute: bool) -> None:
    mode = "EXECUTE" if execute else "DRY-RUN"
    print(
        f"[{service_name}] mode={mode} scanned={stats.scanned} matched={stats.matched} "
        f"deleted={stats.deleted} failed={stats.failed}"
    )


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not args.user_email:
        print("Error: --user-email is required (or set MCP_TEST_USER_EMAIL / USER_GOOGLE_EMAIL).", file=sys.stderr)
        return 1
    if args.older_than_hours < 0:
        print("Error: --older-than-hours must be >= 0.", file=sys.stderr)
        return 1
    if not args.artifact_prefix:
        print("Error: --artifact-prefix must be non-empty.", file=sys.stderr)
        return 1
    if args.max_items <= 0:
        print("Error: --max-items must be > 0.", file=sys.stderr)
        return 1

    try:
        services = _parse_services(args.services)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.older_than_hours)
    logger.info(
        "Starting live artifact cleanup: user=%s prefix=%s cutoff=%s mode=%s services=%s",
        args.user_email,
        args.artifact_prefix,
        cutoff.isoformat(),
        "execute" if args.execute else "dry-run",
        ",".join(sorted(services)),
    )

    try:
        credentials = _resolve_credentials(args.user_email, args.oauth_client_key)
    except Exception as exc:
        print(f"Error: failed to resolve credentials: {exc}", file=sys.stderr)
        return 1

    exit_code = 0

    if "drive" in services:
        try:
            drive_service = _build_service("drive", "v3", credentials)
            drive_stats = cleanup_drive_files(
                drive_service,
                prefix=args.artifact_prefix,
                cutoff=cutoff,
                execute=args.execute,
                max_items=args.max_items,
            )
            _print_summary("drive", drive_stats, args.execute)
            if drive_stats.failed:
                exit_code = 1
        except Exception as exc:
            logger.error("Drive cleanup failed: %s", exc)
            exit_code = 1

    if "calendar" in services:
        try:
            calendar_service = _build_service("calendar", "v3", credentials)
            calendar_stats = cleanup_calendar_events(
                calendar_service,
                prefix=args.artifact_prefix,
                cutoff=cutoff,
                execute=args.execute,
                max_items=args.max_items,
            )
            _print_summary("calendar", calendar_stats, args.execute)
            if calendar_stats.failed:
                exit_code = 1
        except Exception as exc:
            logger.error("Calendar cleanup failed: %s", exc)
            exit_code = 1

    if "tasks" in services:
        try:
            tasks_service = _build_service("tasks", "v1", credentials)
            tasks_stats = cleanup_task_lists(
                tasks_service,
                prefix=args.artifact_prefix,
                cutoff=cutoff,
                execute=args.execute,
                max_items=args.max_items,
            )
            _print_summary("tasks", tasks_stats, args.execute)
            if tasks_stats.failed:
                exit_code = 1
        except Exception as exc:
            logger.error("Tasks cleanup failed: %s", exc)
            exit_code = 1

    if not args.execute:
        print("Dry-run complete. Re-run with --execute to delete matched artifacts.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
