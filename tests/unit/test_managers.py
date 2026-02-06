"""Unit tests for SearchManager and SyncManager."""

import os
import tempfile

from core.managers import SearchManager, SyncManager


class TestSearchManager:
    """Tests for SearchManager alias and caching logic."""

    def setup_method(self):
        """Create fresh SearchManager for each test."""
        self.manager = SearchManager()

    def test_cache_results_assigns_aliases(self):
        """Test that A-Z aliases are assigned to search results."""
        files = [
            {"id": "id1", "name": "File 1"},
            {"id": "id2", "name": "File 2"},
        ]
        results = self.manager.cache_results(files)

        assert len(results) == 2
        assert results[0]["alias"] == "A"
        assert results[1]["alias"] == "B"
        assert self.manager.resolve_alias("A") == "id1"
        assert self.manager.resolve_alias("B") == "id2"

    def test_cache_results_limit(self):
        """Test that aliases are limited to A-Z (26 max results)."""
        files = [{"id": f"id{i}", "name": f"File {i}"} for i in range(30)]
        results = self.manager.cache_results(files)

        # Only 26 results are cached (A-Z)
        assert len(results) == 26
        assert results[0]["alias"] == "A"
        assert results[25]["alias"] == "Z"

    def test_resolve_alias_passthrough(self):
        """Test that non-aliases are returned unchanged."""
        assert self.manager.resolve_alias("some-long-id") == "some-long-id"
        assert self.manager.resolve_alias("123") == "123"

    def test_recache_clears_previous(self):
        """Test that caching new results clears previous aliases."""
        self.manager.cache_results([{"id": "id1", "name": "File 1"}])
        assert self.manager.resolve_alias("A") == "id1"

        self.manager.cache_results([{"id": "id2", "name": "File 2"}])
        assert self.manager.resolve_alias("A") == "id2"


class TestSyncManager:
    """Tests for SyncManager file linking and persistence."""

    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sync_map_path = os.path.join(self.temp_dir.name, "sync_map.json")
        self.manager = SyncManager(sync_map_path=self.sync_map_path)

    def teardown_method(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_link_file(self):
        """Test creating a link between a local file and Drive ID."""
        local_path = "test.md"

        msg = self.manager.link_file(local_path, "drive_id_123", version=10)
        assert "Linked" in msg

        link = self.manager.get_link(local_path)
        assert link["id"] == "drive_id_123"
        assert link["last_synced_version"] == 10

    def test_persistence(self):
        """Test that links survive manager restarts."""
        local_path = "persistent.md"
        self.manager.link_file(local_path, "drive_id_999", version=5)

        new_manager = SyncManager(sync_map_path=self.sync_map_path)
        link = new_manager.get_link(local_path)

        assert link is not None
        assert link["id"] == "drive_id_999"
        assert link["last_synced_version"] == 5

    def test_update_version(self):
        """Test updating the synced version of a file."""
        local_path = "version.md"
        self.manager.link_file(local_path, "id1", version=1)
        self.manager.update_version(local_path, 2)

        link = self.manager.get_link(local_path)
        assert link["last_synced_version"] == 2

    def test_unlink_file(self):
        """Test removing a link."""
        local_path = "remove.md"
        self.manager.link_file(local_path, "id1")
        assert self.manager.get_link(local_path) is not None

        removed = self.manager.unlink_file(local_path)
        assert removed is True
        assert self.manager.get_link(local_path) is None

    def test_get_sync_link_typed(self):
        """Test getting typed SyncLink object."""
        local_path = "typed.md"
        self.manager.link_file(local_path, "drive_id_typed", version=42)

        sync_link = self.manager.get_sync_link(local_path)
        assert sync_link is not None
        assert sync_link.file_id == "drive_id_typed"
        assert sync_link.last_synced_version == 42
