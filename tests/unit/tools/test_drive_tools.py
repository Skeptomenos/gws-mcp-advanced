"""
Unit tests for Google Drive helper functions and tool registration.

Tests cover:
- Permission validation and formatting
- URL building and query construction
- Expiration time validation
- Alias resolution
- Tool registration verification
"""

from unittest.mock import patch

import pytest


class TestValidateShareRole:
    """Tests for share role validation."""

    def test_valid_roles_pass(self):
        """Valid roles should not raise."""
        from gdrive.drive_helpers import validate_share_role

        validate_share_role("reader")
        validate_share_role("commenter")
        validate_share_role("writer")

    def test_invalid_role_raises(self):
        """Invalid role should raise ValueError."""
        from gdrive.drive_helpers import validate_share_role

        with pytest.raises(ValueError, match="Invalid role"):
            validate_share_role("admin")

    def test_empty_role_raises(self):
        """Empty role should raise ValueError."""
        from gdrive.drive_helpers import validate_share_role

        with pytest.raises(ValueError, match="Invalid role"):
            validate_share_role("")


class TestValidateShareType:
    """Tests for share type validation."""

    def test_valid_types_pass(self):
        """Valid share types should not raise."""
        from gdrive.drive_helpers import validate_share_type

        validate_share_type("user")
        validate_share_type("group")
        validate_share_type("domain")
        validate_share_type("anyone")

    def test_invalid_type_raises(self):
        """Invalid share type should raise ValueError."""
        from gdrive.drive_helpers import validate_share_type

        with pytest.raises(ValueError, match="Invalid share_type"):
            validate_share_type("public")


class TestValidateExpirationTime:
    """Tests for RFC 3339 expiration time validation."""

    def test_valid_utc_format(self):
        """UTC format with Z suffix should pass."""
        from gdrive.drive_helpers import validate_expiration_time

        validate_expiration_time("2025-01-15T00:00:00Z")

    def test_valid_with_offset(self):
        """Format with timezone offset should pass."""
        from gdrive.drive_helpers import validate_expiration_time

        validate_expiration_time("2025-01-15T12:30:00+05:30")
        validate_expiration_time("2025-01-15T12:30:00-08:00")

    def test_valid_with_milliseconds(self):
        """Format with milliseconds should pass."""
        from gdrive.drive_helpers import validate_expiration_time

        validate_expiration_time("2025-01-15T00:00:00.123Z")

    def test_invalid_format_raises(self):
        """Invalid format should raise ValueError."""
        from gdrive.drive_helpers import validate_expiration_time

        with pytest.raises(ValueError, match="RFC 3339"):
            validate_expiration_time("2025-01-15")

    def test_invalid_no_timezone_raises(self):
        """Missing timezone should raise ValueError."""
        from gdrive.drive_helpers import validate_expiration_time

        with pytest.raises(ValueError, match="RFC 3339"):
            validate_expiration_time("2025-01-15T00:00:00")


class TestCheckPublicLinkPermission:
    """Tests for public link permission checking."""

    def test_anyone_reader_is_public(self):
        """Anyone with reader role is public."""
        from gdrive.drive_helpers import check_public_link_permission

        permissions = [{"type": "anyone", "role": "reader"}]
        assert check_public_link_permission(permissions) is True

    def test_anyone_writer_is_public(self):
        """Anyone with writer role is public."""
        from gdrive.drive_helpers import check_public_link_permission

        permissions = [{"type": "anyone", "role": "writer"}]
        assert check_public_link_permission(permissions) is True

    def test_anyone_commenter_is_public(self):
        """Anyone with commenter role is public."""
        from gdrive.drive_helpers import check_public_link_permission

        permissions = [{"type": "anyone", "role": "commenter"}]
        assert check_public_link_permission(permissions) is True

    def test_user_only_not_public(self):
        """User-only permissions are not public."""
        from gdrive.drive_helpers import check_public_link_permission

        permissions = [{"type": "user", "role": "reader", "emailAddress": "user@example.com"}]
        assert check_public_link_permission(permissions) is False

    def test_empty_permissions_not_public(self):
        """Empty permissions list is not public."""
        from gdrive.drive_helpers import check_public_link_permission

        assert check_public_link_permission([]) is False

    def test_mixed_permissions_with_anyone(self):
        """Mixed permissions with anyone is public."""
        from gdrive.drive_helpers import check_public_link_permission

        permissions = [
            {"type": "user", "role": "writer", "emailAddress": "owner@example.com"},
            {"type": "anyone", "role": "reader"},
        ]
        assert check_public_link_permission(permissions) is True


class TestFormatPermissionInfo:
    """Tests for permission info formatting."""

    def test_format_anyone_permission(self):
        """Format anyone permission."""
        from gdrive.drive_helpers import format_permission_info

        perm = {"type": "anyone", "role": "reader", "id": "anyoneWithLink"}
        result = format_permission_info(perm)
        assert "Anyone with the link" in result
        assert "reader" in result
        assert "anyoneWithLink" in result

    def test_format_user_permission(self):
        """Format user permission."""
        from gdrive.drive_helpers import format_permission_info

        perm = {"type": "user", "role": "writer", "id": "123", "emailAddress": "user@example.com"}
        result = format_permission_info(perm)
        assert "User:" in result
        assert "user@example.com" in result
        assert "writer" in result

    def test_format_group_permission(self):
        """Format group permission."""
        from gdrive.drive_helpers import format_permission_info

        perm = {"type": "group", "role": "reader", "id": "456", "emailAddress": "group@example.com"}
        result = format_permission_info(perm)
        assert "Group:" in result
        assert "group@example.com" in result

    def test_format_domain_permission(self):
        """Format domain permission."""
        from gdrive.drive_helpers import format_permission_info

        perm = {"type": "domain", "role": "reader", "id": "789", "domain": "example.com"}
        result = format_permission_info(perm)
        assert "Domain:" in result
        assert "example.com" in result

    def test_format_with_expiration(self):
        """Format permission with expiration time."""
        from gdrive.drive_helpers import format_permission_info

        perm = {
            "type": "user",
            "role": "reader",
            "id": "123",
            "emailAddress": "user@example.com",
            "expirationTime": "2025-12-31T00:00:00Z",
        }
        result = format_permission_info(perm)
        assert "expires:" in result
        assert "2025-12-31" in result


class TestGetDriveImageUrl:
    """Tests for Drive image URL generation."""

    def test_generates_correct_url(self):
        """Generate correct embed URL."""
        from gdrive.drive_helpers import get_drive_image_url

        result = get_drive_image_url("abc123")
        assert result == "https://drive.google.com/uc?export=view&id=abc123"


class TestFormatPublicSharingError:
    """Tests for public sharing error message formatting."""

    def test_includes_file_name(self):
        """Error message includes file name."""
        from gdrive.drive_helpers import format_public_sharing_error

        result = format_public_sharing_error("My Document", "abc123")
        assert "My Document" in result

    def test_includes_file_link(self):
        """Error message includes file link."""
        from gdrive.drive_helpers import format_public_sharing_error

        result = format_public_sharing_error("My Document", "abc123")
        assert "abc123" in result
        assert "drive.google.com" in result


class TestBuildDriveListParams:
    """Tests for Drive API list parameter building."""

    def test_basic_params(self):
        """Build basic list params."""
        from gdrive.drive_helpers import build_drive_list_params

        result = build_drive_list_params("name contains 'test'", 10)
        assert result["q"] == "name contains 'test'"
        assert result["pageSize"] == 10
        assert result["supportsAllDrives"] is True
        assert result["includeItemsFromAllDrives"] is True

    def test_with_drive_id(self):
        """Build params with drive_id."""
        from gdrive.drive_helpers import build_drive_list_params

        result = build_drive_list_params("name contains 'test'", 10, drive_id="drive123")
        assert result["driveId"] == "drive123"
        assert result["corpora"] == "drive"

    def test_with_drive_id_and_corpora(self):
        """Build params with drive_id and explicit corpora."""
        from gdrive.drive_helpers import build_drive_list_params

        result = build_drive_list_params("name contains 'test'", 10, drive_id="drive123", corpora="allDrives")
        assert result["driveId"] == "drive123"
        assert result["corpora"] == "allDrives"

    def test_with_corpora_only(self):
        """Build params with corpora but no drive_id."""
        from gdrive.drive_helpers import build_drive_list_params

        result = build_drive_list_params("name contains 'test'", 10, corpora="user")
        assert "driveId" not in result
        assert result["corpora"] == "user"

    def test_include_items_from_all_drives_false(self):
        """Build params with includeItemsFromAllDrives=False."""
        from gdrive.drive_helpers import build_drive_list_params

        result = build_drive_list_params("name contains 'test'", 10, include_items_from_all_drives=False)
        assert result["includeItemsFromAllDrives"] is False


class TestResolveFileIdOrAlias:
    """Tests for file ID/alias resolution."""

    def test_single_letter_alias_resolved(self):
        """Single letter alias is resolved via search_manager."""
        from gdrive.drive_helpers import resolve_file_id_or_alias

        with patch("gdrive.drive_helpers.search_manager") as mock_manager:
            mock_manager.resolve_alias.return_value = "resolved_id_123"
            result = resolve_file_id_or_alias("A")
            mock_manager.resolve_alias.assert_called_once_with("A")
            assert result == "resolved_id_123"

    def test_file_id_passed_through(self):
        """Non-alias file ID is passed through."""
        from gdrive.drive_helpers import resolve_file_id_or_alias

        with patch("gdrive.drive_helpers.search_manager") as mock_manager:
            mock_manager.resolve_alias.return_value = "abc123xyz"
            result = resolve_file_id_or_alias("abc123xyz")
            assert result == "abc123xyz"


class TestToolRegistration:
    """Tests for MCP tool registration."""

    def test_search_tools_are_registered(self):
        """Verify search tools have correct names."""
        from gdrive import check_drive_file_public_access, list_drive_items, search_drive_files

        assert hasattr(search_drive_files, "name")
        assert search_drive_files.name == "search_drive_files"

        assert hasattr(list_drive_items, "name")
        assert list_drive_items.name == "list_drive_items"

        assert hasattr(check_drive_file_public_access, "name")
        assert check_drive_file_public_access.name == "check_drive_file_public_access"

    def test_file_tools_are_registered(self):
        """Verify file tools have correct names."""
        from gdrive import create_drive_file, get_drive_file_content, get_drive_file_download_url, update_drive_file

        assert hasattr(get_drive_file_content, "name")
        assert get_drive_file_content.name == "get_drive_file_content"

        assert hasattr(get_drive_file_download_url, "name")
        assert get_drive_file_download_url.name == "get_drive_file_download_url"

        assert hasattr(create_drive_file, "name")
        assert create_drive_file.name == "create_drive_file"

        assert hasattr(update_drive_file, "name")
        assert update_drive_file.name == "update_drive_file"

    def test_permission_tools_are_registered(self):
        """Verify permission tools have correct names."""
        from gdrive import (
            batch_share_drive_file,
            get_drive_file_permissions,
            get_drive_shareable_link,
            remove_drive_permission,
            share_drive_file,
            transfer_drive_ownership,
            update_drive_permission,
        )

        assert hasattr(get_drive_file_permissions, "name")
        assert get_drive_file_permissions.name == "get_drive_file_permissions"

        assert hasattr(get_drive_shareable_link, "name")
        assert get_drive_shareable_link.name == "get_drive_shareable_link"

        assert hasattr(share_drive_file, "name")
        assert share_drive_file.name == "share_drive_file"

        assert hasattr(batch_share_drive_file, "name")
        assert batch_share_drive_file.name == "batch_share_drive_file"

        assert hasattr(update_drive_permission, "name")
        assert update_drive_permission.name == "update_drive_permission"

        assert hasattr(remove_drive_permission, "name")
        assert remove_drive_permission.name == "remove_drive_permission"

        assert hasattr(transfer_drive_ownership, "name")
        assert transfer_drive_ownership.name == "transfer_drive_ownership"

    def test_sync_tools_are_registered(self):
        """Verify sync tools have correct names."""
        from gdrive import (
            download_doc_tabs,
            download_google_doc,
            link_local_file,
            mirror_drive_folder,
            update_google_doc,
            upload_folder,
        )

        assert hasattr(link_local_file, "name")
        assert link_local_file.name == "link_local_file"

        assert hasattr(update_google_doc, "name")
        assert update_google_doc.name == "update_google_doc"

        assert hasattr(download_google_doc, "name")
        assert download_google_doc.name == "download_google_doc"

        assert hasattr(upload_folder, "name")
        assert upload_folder.name == "upload_folder"

        assert hasattr(mirror_drive_folder, "name")
        assert mirror_drive_folder.name == "mirror_drive_folder"

        assert hasattr(download_doc_tabs, "name")
        assert download_doc_tabs.name == "download_doc_tabs"
