"""Tests for the move_files module."""

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from cms_backend.shuttle.context import Context
from cms_backend.shuttle.move_files import move_book_files, move_files


class TestMoveFilesEndToEnd:
    """End-to-end tests for the move_files function."""

    def test_move_files_processes_multiple_books_in_order(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that move_files processes multiple books in created_at order."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1",
            folder_name="zims",
        )
        warehouse_2, warehouse_path_2 = create_warehouse_with_path(
            name="warehouse_2",
            folder_name="zims",
        )
        dbsession.flush()

        # Create test files
        source_file_1 = temp_warehouse_dirs["warehouse_1"] / "zims" / "book1.zim"
        source_file_2 = temp_warehouse_dirs["warehouse_1"] / "zims" / "book2.zim"
        source_file_3 = temp_warehouse_dirs["warehouse_1"] / "zims" / "book3.zim"
        for src_file in [source_file_1, source_file_2, source_file_3]:
            src_file.parent.mkdir(parents=True, exist_ok=True)
        source_file_1.write_text("book1 content")
        source_file_2.write_text("book2 content")
        source_file_3.write_text("book3 content")

        # Create books with locations
        book_1 = create_book()
        create_book_location(
            book=book_1,
            warehouse_path=warehouse_path_1,
            filename="book1.zim",
            status="current",
        )
        create_book_location(
            book=book_1,
            warehouse_path=warehouse_path_2,
            filename="book1.zim",
            status="target",
        )
        book_1.status = "pending_move"

        book_2 = create_book()
        create_book_location(
            book=book_2,
            warehouse_path=warehouse_path_1,
            filename="book2.zim",
            status="current",
        )
        create_book_location(
            book=book_2,
            warehouse_path=warehouse_path_2,
            filename="book2.zim",
            status="target",
        )
        book_2.status = "pending_move"

        book_3 = create_book()
        create_book_location(
            book=book_3,
            warehouse_path=warehouse_path_1,
            filename="book3.zim",
            status="current",
        )
        create_book_location(
            book=book_3,
            warehouse_path=warehouse_path_2,
            filename="book3.zim",
            status="target",
        )
        book_3.status = "pending_move"

        dbsession.flush()

        warehouse_paths = {
            warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_2.id: str(temp_warehouse_dirs["warehouse_2"]),
        }

        Context.local_warehouse_paths = warehouse_paths
        move_files(dbsession)
        dbsession.flush()

        # Verify all books processed
        assert book_1.status == "published"
        assert book_2.status == "published"
        assert book_3.status == "published"

        # Verify files moved
        target_file_1 = temp_warehouse_dirs["warehouse_2"] / "zims" / "book1.zim"
        target_file_2 = temp_warehouse_dirs["warehouse_2"] / "zims" / "book2.zim"
        target_file_3 = temp_warehouse_dirs["warehouse_2"] / "zims" / "book3.zim"

        assert target_file_1.read_text() == "book1 content"
        assert target_file_2.read_text() == "book2 content"
        assert target_file_3.read_text() == "book3 content"

        assert not source_file_1.exists()
        assert not source_file_2.exists()
        assert not source_file_3.exists()


class TestMoveBookFilesSuccess:
    """Tests for successful move_book_files scenarios."""

    def test_move_book_files_simple_move(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test simple move with 1 current and 1 target location."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1",
            folder_name="zims",
        )
        dbsession.flush()

        source_dir = temp_warehouse_dirs["warehouse_1"] / "zims"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "old_book.zim"
        source_file.write_text("test content")

        book = create_book()
        current_loc = create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="old_book.zim",
            status="current",
        )
        target_loc = create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="new_book.zim",
            status="target",
        )
        dbsession.flush()

        warehouse_paths = {warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"])}
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        target_file = source_dir / "new_book.zim"
        assert target_file.exists()
        assert target_file.read_text() == "test content"
        assert not source_file.exists()
        assert book.status == "published"
        assert target_loc.status == "current"
        assert current_loc not in book.locations

    def test_move_book_files_copy_then_move(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test copying to first target, then moving to second (1→2)."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="source"
        )
        warehouse_2_a, warehouse_path_2_a = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_a"
        )
        warehouse_2_b, warehouse_path_2_b = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_b"
        )
        dbsession.flush()

        source_dir = temp_warehouse_dirs["warehouse_1"] / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "source.zim"
        source_file.write_text("book content")

        book = create_book()
        # current_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="source.zim",
            status="current",
        )
        # target_loc_1
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_a,
            filename="target1.zim",
            status="target",
        )
        # target_loc_2
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_b,
            filename="target2.zim",
            status="target",
        )
        dbsession.flush()

        for subfolder in ["target_a", "target_b"]:
            (temp_warehouse_dirs["warehouse_2"] / subfolder).mkdir(
                parents=True, exist_ok=True
            )

        warehouse_paths = {
            warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_2_a.id: str(temp_warehouse_dirs["warehouse_2"]),
            warehouse_2_b.id: str(temp_warehouse_dirs["warehouse_2"]),
        }
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        target_file_1 = temp_warehouse_dirs["warehouse_2"] / "target_a" / "target1.zim"
        target_file_2 = temp_warehouse_dirs["warehouse_2"] / "target_b" / "target2.zim"
        assert target_file_1.exists()
        assert target_file_1.read_text() == "book content"
        assert target_file_2.exists()
        assert target_file_2.read_text() == "book content"
        assert not source_file.exists()
        assert book.status == "published"

    def test_move_book_files_multiple_copies_one_move(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test 1→3: 2 copies then 1 move."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="source"
        )
        warehouse_2_a, warehouse_path_2_a = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_a"
        )
        warehouse_2_b, warehouse_path_2_b = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_b"
        )
        warehouse_2_c, warehouse_path_2_c = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_c"
        )
        dbsession.flush()

        source_dir = temp_warehouse_dirs["warehouse_1"] / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "source.zim"
        source_file.write_text("book content")

        book = create_book()
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="source.zim",
            status="current",
        )
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_a,
            filename="target1.zim",
            status="target",
        )
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_b,
            filename="target2.zim",
            status="target",
        )
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_c,
            filename="target3.zim",
            status="target",
        )
        dbsession.flush()

        for subfolder in ["target_a", "target_b", "target_c"]:
            (temp_warehouse_dirs["warehouse_2"] / subfolder).mkdir(
                parents=True, exist_ok=True
            )

        warehouse_paths = {
            warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_2_a.id: str(temp_warehouse_dirs["warehouse_2"]),
            warehouse_2_b.id: str(temp_warehouse_dirs["warehouse_2"]),
            warehouse_2_c.id: str(temp_warehouse_dirs["warehouse_2"]),
        }
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        for i, subfolder in enumerate(["target_a", "target_b", "target_c"], 1):
            target_file = (
                temp_warehouse_dirs["warehouse_2"] / subfolder / f"target{i}.zim"
            )
            assert target_file.exists()
            assert target_file.read_text() == "book content"

        assert not source_file.exists()
        current_locs = [loc for loc in book.locations if loc.status == "current"]
        assert len(current_locs) == 3


class TestMoveBookFilesErrors:
    """Tests for error handling in move_book_files."""

    def test_move_book_files_no_current_locations(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that book with no current locations is marked as errored."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="zims"
        )
        dbsession.flush()

        book = create_book()
        target_loc = create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="target.zim",
            status="target",
        )
        dbsession.flush()

        warehouse_paths = {warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"])}
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        assert book.status == "errored"
        assert any("no current location" in event for event in book.events)
        assert target_loc.status == "target"

    def test_move_book_files_no_target_locations(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that book with no target locations is marked as published."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="zims"
        )
        dbsession.flush()

        source_dir = temp_warehouse_dirs["warehouse_1"] / "zims"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "book.zim"
        source_file.write_text("content")

        book = create_book()
        # current_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="book.zim",
            status="current",
        )
        dbsession.flush()

        warehouse_paths = {warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"])}
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        assert book.status == "published"
        assert any("no target location" in event for event in book.events)
        assert source_file.exists()

    def test_move_book_files_inaccessible_warehouse(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that book with inaccessible warehouse is skipped."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="zims"
        )
        _, warehouse_path_2 = create_warehouse_with_path(
            name="warehouse_2", folder_name="zims"
        )
        dbsession.flush()

        book = create_book()
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="book.zim",
            status="current",
        )
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2,
            filename="book_target.zim",
            status="target",
        )
        dbsession.flush()

        # Only warehouse_1 accessible (warehouse_2 is inaccessible)
        warehouse_paths = {warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"])}
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        # Book should not be processed (status unchanged)
        assert book.status == "pending_processing"


class TestMoveBookFilesEdgeCases:
    """Tests for edge cases in move_book_files."""

    def test_move_book_files_same_location(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test when current location matches target."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="zims"
        )
        dbsession.flush()

        source_dir = temp_warehouse_dirs["warehouse_1"] / "zims"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "book.zim"
        source_file.write_text("content")

        book = create_book()
        # current_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="book.zim",
            status="current",
        )
        # target_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="book.zim",
            status="target",
        )
        dbsession.flush()

        warehouse_paths = {warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"])}
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        assert book.status == "published"
        assert source_file.exists()
        assert source_file.read_text() == "content"

    def test_move_book_files_events_contain_warehouse_info(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that events contain warehouse and folder info."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="primary_warehouse", folder_name="main_zims"
        )
        warehouse_2, warehouse_path_2 = create_warehouse_with_path(
            name="backup_warehouse", folder_name="backup_zims"
        )
        dbsession.flush()

        source_dir = temp_warehouse_dirs["warehouse_1"] / "main_zims"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "test_book.zim"
        source_file.write_text("content")

        book = create_book()
        # current_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="test_book.zim",
            status="current",
        )
        # target_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2,
            filename="test_book_v2.zim",
            status="target",
        )
        dbsession.flush()

        (temp_warehouse_dirs["warehouse_2"] / "backup_zims").mkdir(
            parents=True, exist_ok=True
        )

        warehouse_paths = {
            warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_2.id: str(temp_warehouse_dirs["warehouse_2"]),
        }
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        move_events = [e for e in book.events if "moved book from" in e]
        assert len(move_events) == 1
        event = move_events[0]
        assert "primary_warehouse" in event
        assert "main_zims" in event
        assert "backup_warehouse" in event
        assert "backup_zims" in event

    def test_move_book_files_file_content_preserved(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that file content is preserved during copy and move."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="source"
        )
        warehouse_2_a, warehouse_path_2_a = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_a"
        )
        warehouse_2_b, warehouse_path_2_b = create_warehouse_with_path(
            name="warehouse_2", folder_name="target_b"
        )
        dbsession.flush()

        test_content = "This is a test ZIM file content with special chars: éàù\n" * 100
        source_dir = temp_warehouse_dirs["warehouse_1"] / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "source.zim"
        source_file.write_text(test_content)

        book = create_book()
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="source.zim",
            status="current",
        )
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_a,
            filename="target1.zim",
            status="target",
        )
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2_b,
            filename="target2.zim",
            status="target",
        )
        dbsession.flush()

        for subfolder in ["target_a", "target_b"]:
            (temp_warehouse_dirs["warehouse_2"] / subfolder).mkdir(
                parents=True, exist_ok=True
            )

        warehouse_paths = {
            warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_2_a.id: str(temp_warehouse_dirs["warehouse_2"]),
            warehouse_2_b.id: str(temp_warehouse_dirs["warehouse_2"]),
        }
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        target_file_1 = temp_warehouse_dirs["warehouse_2"] / "target_a" / "target1.zim"
        target_file_2 = temp_warehouse_dirs["warehouse_2"] / "target_b" / "target2.zim"

        assert target_file_1.read_text() == test_content
        assert target_file_2.read_text() == test_content

    def test_move_book_files_three_current_one_target(
        self,
        dbsession: OrmSession,
        create_book: Any,
        create_book_location: Any,
        create_warehouse_with_path: Any,
        temp_warehouse_dirs: dict[str, Path],
    ):
        """Test that when there are 3 current and 1 target, one moves and two get
        deleted."""
        warehouse_1, warehouse_path_1 = create_warehouse_with_path(
            name="warehouse_1", folder_name="zims"
        )
        warehouse_2, warehouse_path_2 = create_warehouse_with_path(
            name="warehouse_2", folder_name="zims"
        )
        warehouse_3, warehouse_path_3 = create_warehouse_with_path(
            name="warehouse_3", folder_name="zims"
        )
        warehouse_4, warehouse_path_4 = create_warehouse_with_path(
            name="warehouse_4", folder_name="zims"
        )
        dbsession.flush()

        # Create three current locations with actual files
        source_dir_1 = temp_warehouse_dirs["warehouse_1"] / "zims"
        source_dir_1.mkdir(parents=True, exist_ok=True)
        source_file_1 = source_dir_1 / "book1.zim"
        source_file_1.write_text("content 1")

        source_dir_2 = temp_warehouse_dirs["warehouse_2"] / "zims"
        source_dir_2.mkdir(parents=True, exist_ok=True)
        source_file_2 = source_dir_2 / "book2.zim"
        source_file_2.write_text("content 2")

        source_dir_3 = temp_warehouse_dirs["warehouse_1"] / "zims"
        source_file_3 = source_dir_3 / "book3.zim"
        source_file_3.write_text("content 3")

        book = create_book()
        # current_loc_1
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_1,
            filename="book1.zim",
            status="current",
        )
        # current_loc_2
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_2,
            filename="book2.zim",
            status="current",
        )
        # current_loc_3
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_3,
            filename="book3.zim",
            status="current",
        )
        # target_loc
        create_book_location(
            book=book,
            warehouse_path=warehouse_path_4,
            filename="book_final.zim",
            status="target",
        )
        dbsession.flush()

        (temp_warehouse_dirs["warehouse_2"] / "zims").mkdir(parents=True, exist_ok=True)

        warehouse_paths = {
            warehouse_1.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_2.id: str(temp_warehouse_dirs["warehouse_2"]),
            warehouse_3.id: str(temp_warehouse_dirs["warehouse_1"]),
            warehouse_4.id: str(temp_warehouse_dirs["warehouse_2"]),
        }
        Context.local_warehouse_paths = warehouse_paths
        move_book_files(dbsession, book)
        dbsession.flush()

        # Verify one file moved to target
        target_file = temp_warehouse_dirs["warehouse_2"] / "zims" / "book_final.zim"
        assert target_file.exists()
        assert target_file.read_text() == "content 1"  # First current moved

        # Verify other files deleted
        assert not source_file_1.exists()  # Moved
        assert not source_file_2.exists()  # Deleted
        assert not source_file_3.exists()  # Deleted

        # Verify events
        move_events = [e for e in book.events if "moved book from" in e]
        delete_events = [e for e in book.events if "deleted old location" in e]
        assert len(move_events) == 1
        assert len(delete_events) == 2

        # Verify only one current location remains
        current_locations = [loc for loc in book.locations if loc.status == "current"]
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_path_id == warehouse_path_4.id

        assert book.status == "published"
