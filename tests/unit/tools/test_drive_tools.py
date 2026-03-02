"""
Unit tests for Google Drive helper functions and tool registration.

Tests cover:
- Permission validation and formatting
- URL building and query construction
- Expiration time validation
- Alias resolution
- Tool registration verification
"""

from unittest.mock import MagicMock, patch

import pytest


def _get_innermost_tool_function(tool_name: str):
    from gdrive import files as drive_files

    function = getattr(drive_files, tool_name).fn
    while hasattr(function, "__wrapped__"):
        function = function.__wrapped__
    return function


def _get_innermost_permission_tool_function(tool_name: str):
    from gdrive import permissions as drive_permissions

    function = getattr(drive_permissions, tool_name).fn
    while hasattr(function, "__wrapped__"):
        function = function.__wrapped__
    return function


def _get_innermost_sync_tool_function(tool_name: str):
    from gdrive import sync_tools as drive_sync_tools

    function = getattr(drive_sync_tools, tool_name).fn
    while hasattr(function, "__wrapped__"):
        function = function.__wrapped__
    return function


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


class TestDriveMutatorDryRunBehavior:
    """Tests for dry-run defaults on Drive mutating tools."""

    @pytest.mark.asyncio
    async def test_create_drive_file_dry_run_skips_resolution_and_mutation(self, monkeypatch):
        """Default dry-run should return preview without resolving folder or mutating."""
        create_impl = _get_innermost_tool_function("create_drive_file")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_folder_id(_service, _folder_id):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-folder"

        monkeypatch.setattr("gdrive.files.resolve_folder_id", fake_resolve_folder_id)

        result = await create_impl(
            service=service,
            user_google_email="user@example.com",
            file_name="demo.txt",
            content="hello world",
        )

        assert result.startswith("DRY RUN:")
        assert "Would create Drive file 'demo.txt'" in result
        assert resolve_called is False
        assert service.files.call_count == 0

    @pytest.mark.asyncio
    async def test_create_drive_file_dry_run_false_calls_drive_create(self, monkeypatch):
        """Explicit dry_run=False should execute Drive create mutation."""
        create_impl = _get_innermost_tool_function("create_drive_file")
        service = MagicMock()
        service.files.return_value.create.return_value.execute.return_value = {
            "id": "file-123",
            "name": "demo.txt",
            "webViewLink": "https://drive.google.com/file/d/file-123/view",
        }

        async def fake_resolve_folder_id(_service, _folder_id):
            return "resolved-folder"

        monkeypatch.setattr("gdrive.files.resolve_folder_id", fake_resolve_folder_id)

        result = await create_impl(
            service=service,
            user_google_email="user@example.com",
            file_name="demo.txt",
            content="hello world",
            dry_run=False,
        )

        assert "Successfully created file" in result
        assert service.files.return_value.create.call_count == 1

    @pytest.mark.asyncio
    async def test_update_drive_file_dry_run_skips_resolution_and_mutation(self, monkeypatch):
        """Default dry-run should skip file resolution and update mutation."""
        update_impl = _get_innermost_tool_function("update_drive_file")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-file", {"name": "Old Name"}

        monkeypatch.setattr("gdrive.files.resolve_drive_item", fake_resolve_drive_item)

        result = await update_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            name="New Name",
        )

        assert result.startswith("DRY RUN:")
        assert "Would update Drive file 'file-123'" in result
        assert "name" in result
        assert resolve_called is False
        assert service.files.call_count == 0

    @pytest.mark.asyncio
    async def test_update_drive_file_dry_run_false_calls_drive_update(self, monkeypatch):
        """Explicit dry_run=False should execute Drive update mutation."""
        update_impl = _get_innermost_tool_function("update_drive_file")
        service = MagicMock()
        service.files.return_value.update.return_value.execute.return_value = {
            "id": "file-123",
            "name": "New Name",
            "webViewLink": "https://drive.google.com/file/d/file-123/view",
        }

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            return "resolved-file", {
                "name": "Old Name",
                "description": "old",
                "starred": False,
                "trashed": False,
                "writersCanShare": True,
                "copyRequiresWriterPermission": False,
            }

        monkeypatch.setattr("gdrive.files.resolve_drive_item", fake_resolve_drive_item)

        result = await update_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            name="New Name",
            dry_run=False,
        )

        assert "Successfully updated file" in result
        assert service.files.return_value.update.call_count == 1


class TestDrivePermissionMutatorDryRunBehavior:
    """Tests for dry-run defaults on Drive permission mutating tools."""

    @pytest.mark.asyncio
    async def test_share_drive_file_dry_run_skips_resolution_and_mutation(self, monkeypatch):
        """Default dry-run should not resolve file metadata or create permission."""
        share_impl = _get_innermost_permission_tool_function("share_drive_file")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-file", {"name": "Demo"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await share_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            share_with="friend@example.com",
        )

        assert result.startswith("DRY RUN:")
        assert "Would share file 'file-123'" in result
        assert resolve_called is False
        assert service.permissions.call_count == 0

    @pytest.mark.asyncio
    async def test_share_drive_file_dry_run_false_calls_create(self, monkeypatch):
        """Explicit dry_run=False should execute permission create mutation."""
        share_impl = _get_innermost_permission_tool_function("share_drive_file")
        service = MagicMock()
        service.permissions.return_value.create.return_value.execute.return_value = {
            "id": "perm-1",
            "type": "user",
            "role": "reader",
            "emailAddress": "friend@example.com",
        }

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            return "resolved-file", {"name": "Demo", "webViewLink": "https://drive.google.com/file/d/file-123/view"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await share_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            share_with="friend@example.com",
            dry_run=False,
        )

        assert "Successfully shared" in result
        assert service.permissions.return_value.create.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_share_drive_file_dry_run_skips_resolution_and_mutation(self, monkeypatch):
        """Default dry-run should return preview without creating permissions."""
        from gdrive.permissions import ShareRecipient

        batch_impl = _get_innermost_permission_tool_function("batch_share_drive_file")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-file", {"name": "Demo", "webViewLink": "https://example.com"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        recipients = [ShareRecipient(email="friend@example.com", role="reader", share_type="user")]
        result = await batch_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            recipients=recipients,
        )

        assert result.startswith("DRY RUN:")
        assert "Would batch share file 'file-123'" in result
        assert "1 valid recipient" in result
        assert resolve_called is False
        assert service.permissions.call_count == 0

    @pytest.mark.asyncio
    async def test_batch_share_drive_file_dry_run_false_calls_create(self, monkeypatch):
        """Explicit dry_run=False should execute permission create mutations."""
        from gdrive.permissions import ShareRecipient

        batch_impl = _get_innermost_permission_tool_function("batch_share_drive_file")
        service = MagicMock()
        service.permissions.return_value.create.return_value.execute.return_value = {
            "id": "perm-1",
            "type": "user",
            "role": "reader",
            "emailAddress": "friend@example.com",
        }

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            return "resolved-file", {"name": "Demo", "webViewLink": "https://drive.google.com/file/d/file-123/view"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        recipients = [ShareRecipient(email="friend@example.com", role="reader", share_type="user")]
        result = await batch_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            recipients=recipients,
            dry_run=False,
        )

        assert "Batch share results" in result
        assert service.permissions.return_value.create.call_count == 1

    @pytest.mark.asyncio
    async def test_update_drive_permission_dry_run_skips_resolution_and_mutation(self, monkeypatch):
        """Default dry-run should skip permission update mutation."""
        update_impl = _get_innermost_permission_tool_function("update_drive_permission")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-file", {"name": "Demo"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await update_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            permission_id="perm-1",
            role="writer",
        )

        assert result.startswith("DRY RUN:")
        assert "Would update permission 'perm-1'" in result
        assert resolve_called is False
        assert service.permissions.call_count == 0

    @pytest.mark.asyncio
    async def test_update_drive_permission_dry_run_false_calls_update(self, monkeypatch):
        """Explicit dry_run=False should execute permission update mutation."""
        update_impl = _get_innermost_permission_tool_function("update_drive_permission")
        service = MagicMock()
        service.permissions.return_value.update.return_value.execute.return_value = {
            "id": "perm-1",
            "type": "user",
            "role": "writer",
            "emailAddress": "friend@example.com",
        }

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            return "resolved-file", {"name": "Demo"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await update_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            permission_id="perm-1",
            role="writer",
            dry_run=False,
        )

        assert "Successfully updated permission" in result
        assert service.permissions.return_value.update.call_count == 1

    @pytest.mark.asyncio
    async def test_remove_drive_permission_dry_run_skips_resolution_and_delete(self, monkeypatch):
        """Default dry-run should skip permission delete mutation."""
        remove_impl = _get_innermost_permission_tool_function("remove_drive_permission")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-file", {"name": "Demo"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await remove_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            permission_id="perm-1",
        )

        assert result.startswith("DRY RUN:")
        assert "Would remove permission 'perm-1'" in result
        assert resolve_called is False
        assert service.permissions.call_count == 0

    @pytest.mark.asyncio
    async def test_remove_drive_permission_dry_run_false_calls_delete(self, monkeypatch):
        """Explicit dry_run=False should execute permission delete mutation."""
        remove_impl = _get_innermost_permission_tool_function("remove_drive_permission")
        service = MagicMock()
        service.permissions.return_value.delete.return_value.execute.return_value = None

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            return "resolved-file", {"name": "Demo"}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await remove_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            permission_id="perm-1",
            dry_run=False,
        )

        assert "Successfully removed permission" in result
        assert service.permissions.return_value.delete.call_count == 1

    @pytest.mark.asyncio
    async def test_transfer_drive_ownership_dry_run_skips_resolution_and_create(self, monkeypatch):
        """Default dry-run should skip ownership transfer mutation."""
        transfer_impl = _get_innermost_permission_tool_function("transfer_drive_ownership")
        service = MagicMock()
        resolve_called = False

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-file", {"name": "Demo", "owners": [{"emailAddress": "old@example.com"}]}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await transfer_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            new_owner_email="new-owner@example.com",
        )

        assert result.startswith("DRY RUN:")
        assert "Would transfer ownership of file 'file-123'" in result
        assert resolve_called is False
        assert service.permissions.call_count == 0

    @pytest.mark.asyncio
    async def test_transfer_drive_ownership_dry_run_false_calls_create(self, monkeypatch):
        """Explicit dry_run=False should execute ownership transfer mutation."""
        transfer_impl = _get_innermost_permission_tool_function("transfer_drive_ownership")
        service = MagicMock()
        service.permissions.return_value.create.return_value.execute.return_value = {
            "id": "perm-owner",
            "type": "user",
            "role": "owner",
            "emailAddress": "new-owner@example.com",
        }

        async def fake_resolve_drive_item(_service, _file_id, extra_fields=None):
            return "resolved-file", {"name": "Demo", "owners": [{"emailAddress": "old@example.com"}]}

        monkeypatch.setattr("gdrive.permissions.resolve_drive_item", fake_resolve_drive_item)

        result = await transfer_impl(
            service=service,
            user_google_email="user@example.com",
            file_id="file-123",
            new_owner_email="new-owner@example.com",
            dry_run=False,
        )

        assert "Successfully transferred ownership" in result
        assert service.permissions.return_value.create.call_count == 1


class TestDriveSyncMutatorDryRunBehavior:
    """Tests for dry-run defaults on Drive sync mutating tools."""

    @pytest.mark.asyncio
    async def test_link_local_file_dry_run_skips_resolution_and_link(self, monkeypatch):
        """Default dry-run should not resolve aliases or mutate sync map."""
        link_impl = _get_innermost_sync_tool_function("link_local_file")
        service = MagicMock()
        resolve_called = False
        link_mock = MagicMock()

        def fake_resolve_file_id_or_alias(_file_id):
            nonlocal resolve_called
            resolve_called = True
            return "resolved-id"

        monkeypatch.setattr("gdrive.sync_tools.resolve_file_id_or_alias", fake_resolve_file_id_or_alias)
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.link_file", link_mock)

        result = await link_impl(
            service=service,
            user_google_email="user@example.com",
            local_path="docs/notes.md",
            file_id="A",
        )

        assert result.startswith("DRY RUN:")
        assert "Would link local path 'docs/notes.md'" in result
        assert resolve_called is False
        assert link_mock.call_count == 0
        assert service.files.call_count == 0

    @pytest.mark.asyncio
    async def test_link_local_file_dry_run_false_executes_link(self, monkeypatch):
        """Explicit dry_run=False should resolve file and update sync map."""
        link_impl = _get_innermost_sync_tool_function("link_local_file")
        service = MagicMock()
        link_mock = MagicMock()

        async def fake_get_file_version(_service, _file_id):
            return 7

        monkeypatch.setattr("gdrive.sync_tools.resolve_file_id_or_alias", lambda _file_id: "resolved-id")
        monkeypatch.setattr("gdrive.sync_tools.get_file_version", fake_get_file_version)
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.link_file", link_mock)

        result = await link_impl(
            service=service,
            user_google_email="user@example.com",
            local_path="docs/notes.md",
            file_id="A",
            dry_run=False,
        )

        assert "Linked docs/notes.md to resolved-id (Version 7)" in result
        link_mock.assert_called_once_with("docs/notes.md", "resolved-id", 7)

    @pytest.mark.asyncio
    async def test_upload_folder_dry_run_skips_mutation(self, tmp_path):
        """Default dry-run should preview upload without touching Drive/sync links."""
        upload_impl = _get_innermost_sync_tool_function("upload_folder")
        service = MagicMock()
        local_dir = tmp_path / "upload"
        local_dir.mkdir()
        (local_dir / "demo.txt").write_text("hello", encoding="utf-8")

        result = await upload_impl(
            service=service,
            user_google_email="user@example.com",
            local_path=str(local_dir),
        )

        assert result.startswith("DRY RUN:")
        assert "Would upload folder" in result
        assert service.files.call_count == 0

    @pytest.mark.asyncio
    async def test_upload_folder_dry_run_false_executes_mutation(self, tmp_path, monkeypatch):
        """Explicit dry_run=False should create Drive folders/files and link uploads."""
        upload_impl = _get_innermost_sync_tool_function("upload_folder")
        service = MagicMock()
        link_mock = MagicMock()
        local_dir = tmp_path / "upload"
        local_dir.mkdir()
        (local_dir / "demo.txt").write_text("hello", encoding="utf-8")

        service.files.return_value.create.return_value.execute.side_effect = [
            {"id": "root-folder"},
            {"id": "file-123"},
        ]
        service.files.return_value.get.return_value.execute.return_value = {"version": "5"}
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.link_file", link_mock)

        result = await upload_impl(
            service=service,
            user_google_email="user@example.com",
            local_path=str(local_dir),
            dry_run=False,
        )

        assert "Created 1 folders and uploaded 1 files." in result
        assert service.files.return_value.create.return_value.execute.call_count == 2
        link_mock.assert_called_once_with(str(local_dir / "demo.txt"), "file-123", 5)

    @pytest.mark.asyncio
    async def test_mirror_drive_folder_dry_run_skips_mutation(self):
        """Default dry-run should preview mirror operation without API/local writes."""
        mirror_impl = _get_innermost_sync_tool_function("mirror_drive_folder")
        service = MagicMock()

        result = await mirror_impl(
            service=service,
            user_google_email="user@example.com",
            local_parent_dir="downloads",
            folder_query="A",
        )

        assert result.startswith("DRY RUN:")
        assert "Would mirror Drive folder 'A'" in result
        assert service.files.call_count == 0

    @pytest.mark.asyncio
    async def test_mirror_drive_folder_dry_run_false_executes_download(self, tmp_path, monkeypatch):
        """Explicit dry_run=False should run folder metadata/list flow."""
        mirror_impl = _get_innermost_sync_tool_function("mirror_drive_folder")
        service = MagicMock()
        link_mock = MagicMock()
        monkeypatch.setattr("gdrive.sync_tools.resolve_file_id_or_alias", lambda _query: "folder-123")
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.link_file", link_mock)

        service.files.return_value.get.return_value.execute.return_value = {"id": "folder-123", "name": "RootFolder"}
        service.files.return_value.list.return_value.execute.return_value = {"files": []}

        result = await mirror_impl(
            service=service,
            user_google_email="user@example.com",
            local_parent_dir=str(tmp_path),
            folder_query="A",
            dry_run=False,
        )

        assert "Downloaded 0 files into 1 folders" in result
        assert service.files.return_value.get.call_count == 1
        assert service.files.return_value.list.call_count == 1
        assert link_mock.call_count == 0

    @pytest.mark.asyncio
    async def test_download_doc_tabs_dry_run_skips_mutation(self):
        """Default dry-run should preview tab download without writes."""
        tabs_impl = _get_innermost_sync_tool_function("download_doc_tabs")
        drive_service = MagicMock()
        docs_service = MagicMock()

        result = await tabs_impl(
            drive_service=drive_service,
            docs_service=docs_service,
            user_google_email="user@example.com",
            local_dir="downloads/tabs",
            file_id="A",
        )

        assert result.startswith("DRY RUN:")
        assert "Would download document tabs for 'A'" in result
        assert drive_service.files.call_count == 0
        assert docs_service.documents.call_count == 0

    @pytest.mark.asyncio
    async def test_download_doc_tabs_dry_run_false_executes_flow(self, tmp_path, monkeypatch):
        """Explicit dry_run=False should execute export/docs fetch and write output files."""
        tabs_impl = _get_innermost_sync_tool_function("download_doc_tabs")
        drive_service = MagicMock()
        docs_service = MagicMock()
        link_mock = MagicMock()
        local_dir = tmp_path / "tabs"

        monkeypatch.setattr("gdrive.sync_tools.resolve_file_id_or_alias", lambda _file_id: "doc-123")
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.link_file", link_mock)

        drive_service.files.return_value.export.return_value.execute.return_value = "full export"
        drive_service.files.return_value.get.return_value.execute.return_value = {"version": "9"}
        docs_service.documents.return_value.get.return_value.execute.return_value = {"tabs": []}

        result = await tabs_impl(
            drive_service=drive_service,
            docs_service=docs_service,
            user_google_email="user@example.com",
            local_dir=str(local_dir),
            file_id="A",
            dry_run=False,
        )

        assert "Hybrid Sync Complete" in result
        assert (local_dir / "_Full_Export.md").exists()
        assert link_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_update_google_doc_dry_run_skips_mutation(self, tmp_path, monkeypatch):
        """Default dry-run should produce a diff without calling Drive update."""
        update_impl = _get_innermost_sync_tool_function("update_google_doc")
        service = MagicMock()
        update_version_mock = MagicMock()
        local_file = tmp_path / "sync.md"
        local_file.write_text("local text\n", encoding="utf-8")

        async def fake_get_file_version(_service, _file_id):
            return 3

        async def fake_download_doc_as_text(_service, _file_id, _mime):
            return "remote text\n"

        monkeypatch.setattr(
            "gdrive.sync_tools.sync_manager.get_link",
            lambda _path: {"id": "doc-123", "last_synced_version": 3},
        )
        monkeypatch.setattr("gdrive.sync_tools.get_file_version", fake_get_file_version)
        monkeypatch.setattr("gdrive.sync_tools.download_doc_as_text", fake_download_doc_as_text)
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.update_version", update_version_mock)

        result = await update_impl(
            service=service,
            user_google_email="user@example.com",
            local_path=str(local_file),
        )

        assert result.startswith("DRY RUN")
        assert "Remote (v3)" in result
        assert "Local (Proposed)" in result
        assert service.files.return_value.update.call_count == 0
        assert update_version_mock.call_count == 0

    @pytest.mark.asyncio
    async def test_update_google_doc_dry_run_false_executes_mutation(self, tmp_path, monkeypatch):
        """Explicit dry_run=False should call Drive update and sync version update."""
        update_impl = _get_innermost_sync_tool_function("update_google_doc")
        service = MagicMock()
        update_version_mock = MagicMock()
        local_file = tmp_path / "sync.md"
        local_file.write_text("local text\n", encoding="utf-8")

        versions = iter([3, 4])

        async def fake_get_file_version(_service, _file_id):
            return next(versions)

        monkeypatch.setattr(
            "gdrive.sync_tools.sync_manager.get_link",
            lambda _path: {"id": "doc-123", "last_synced_version": 3},
        )
        monkeypatch.setattr("gdrive.sync_tools.get_file_version", fake_get_file_version)
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.update_version", update_version_mock)
        service.files.return_value.update.return_value.execute.return_value = {}

        result = await update_impl(
            service=service,
            user_google_email="user@example.com",
            local_path=str(local_file),
            dry_run=False,
        )

        assert "Successfully updated Google Doc (new version: 4)" in result
        assert service.files.return_value.update.call_count == 1
        update_version_mock.assert_called_once_with(str(local_file), 4)

    @pytest.mark.asyncio
    async def test_download_google_doc_dry_run_skips_file_write(self, tmp_path, monkeypatch):
        """Default dry-run should preview content without writing local file."""
        download_impl = _get_innermost_sync_tool_function("download_google_doc")
        service = MagicMock()
        target_file = tmp_path / "download.md"

        async def fake_download_doc_as_text(_service, _file_id, _mime):
            return "remote content\n"

        monkeypatch.setattr(
            "gdrive.sync_tools.sync_manager.get_link",
            lambda _path: {"id": "doc-123", "last_synced_version": 1},
        )
        monkeypatch.setattr("gdrive.sync_tools.download_doc_as_text", fake_download_doc_as_text)

        result = await download_impl(
            service=service,
            user_google_email="user@example.com",
            local_path=str(target_file),
        )

        assert result.startswith("DRY RUN:")
        assert "Would create new file with content" in result
        assert not target_file.exists()

    @pytest.mark.asyncio
    async def test_download_google_doc_dry_run_false_writes_file_and_updates_version(self, tmp_path, monkeypatch):
        """Explicit dry_run=False should persist file content and update sync version."""
        download_impl = _get_innermost_sync_tool_function("download_google_doc")
        service = MagicMock()
        target_file = tmp_path / "download.md"
        update_version_mock = MagicMock()

        async def fake_download_doc_as_text(_service, _file_id, _mime):
            return "remote content\n"

        async def fake_get_file_version(_service, _file_id):
            return 9

        monkeypatch.setattr(
            "gdrive.sync_tools.sync_manager.get_link",
            lambda _path: {"id": "doc-123", "last_synced_version": 1},
        )
        monkeypatch.setattr("gdrive.sync_tools.download_doc_as_text", fake_download_doc_as_text)
        monkeypatch.setattr("gdrive.sync_tools.get_file_version", fake_get_file_version)
        monkeypatch.setattr("gdrive.sync_tools.sync_manager.update_version", update_version_mock)

        result = await download_impl(
            service=service,
            user_google_email="user@example.com",
            local_path=str(target_file),
            dry_run=False,
        )

        assert result == f"Successfully downloaded to {target_file} (synced at version 9)"
        assert target_file.read_text(encoding="utf-8") == "remote content\n"
        update_version_mock.assert_called_once_with(str(target_file), 9)


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
