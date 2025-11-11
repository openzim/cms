"""Tests for filename utilities."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import BookLocation
from cms_backend.utils.filename import compute_target_filename, get_next_suffix


class TestGetNextSuffix:
    """Test the get_next_suffix function."""

    def test_empty_suffix_returns_a(self):
        """Empty suffix should return 'a'."""
        assert get_next_suffix("") == "a"

    def test_single_letter_progression(self):
        """Single letters should progress through alphabet."""
        assert get_next_suffix("a") == "b"
        assert get_next_suffix("b") == "c"
        assert get_next_suffix("m") == "n"
        assert get_next_suffix("y") == "z"

    def test_z_wraps_to_aa(self):
        """'z' should wrap to 'aa'."""
        assert get_next_suffix("z") == "aa"

    def test_double_letter_progression(self):
        """Double letters should progress correctly."""
        assert get_next_suffix("aa") == "ab"
        assert get_next_suffix("ab") == "ac"
        assert get_next_suffix("az") == "ba"
        assert get_next_suffix("ba") == "bb"
        assert get_next_suffix("zz") == "aaa"

    def test_triple_letter_progression(self):
        """Triple letters should progress correctly."""
        assert get_next_suffix("aaa") == "aab"
        assert get_next_suffix("aaz") == "aba"
        assert get_next_suffix("zzz") == "aaaa"


class TestComputeTargetFilename:
    """Test the compute_target_filename function."""

    def test_missing_date_raises_error(self, dbsession: OrmSession):
        """Missing date should raise ValueError."""
        with pytest.raises(ValueError, match="Book date is required"):
            compute_target_filename(dbsession, name="test", flavour=None, date="")

    def test_invalid_date_format_raises_error(self, dbsession: OrmSession):
        """Invalid date format should raise ValueError."""
        with pytest.raises(ValueError, match="at least YYYY-MM"):
            compute_target_filename(dbsession, name="test", flavour=None, date="2024")

    def test_basic_filename_without_flavour(self, dbsession: OrmSession):
        """Should generate basic filename without flavour."""
        result = compute_target_filename(
            dbsession,
            name="wikipedia_en_all",
            flavour=None,
            date="2024-01-15",
        )
        assert result == "wikipedia_en_all_2024-01.zim"

    def test_basic_filename_with_flavour(self, dbsession: OrmSession):
        """Should generate filename with flavour."""
        result = compute_target_filename(
            dbsession,
            name="wikipedia_en_all",
            flavour="maxi",
            date="2024-01-15",
        )
        assert result == "wikipedia_en_all_maxi_2024-01.zim"

    def test_no_existing_locations_uses_base(self, dbsession: OrmSession):
        """When no existing locations, should use base pattern."""
        # Fresh database has no locations
        result = compute_target_filename(
            dbsession,
            name="new_book",
            flavour=None,
            date="2024-02-20",
        )
        assert result == "new_book_2024-02.zim"

    def test_collision_handling_single_letter(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Should handle collision with single letter suffix."""
        # Create first location (base pattern)
        create_book_location(
            filename="test_book_2024-03.zim",
            status="target",
        )

        # Compute filename for same name/flavour/period
        result = compute_target_filename(
            dbsession,
            name="test_book",
            flavour=None,
            date="2024-03-10",
        )
        assert result == "test_book_2024-03a.zim"

    def test_multiple_collisions_progression(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Should handle multiple collisions in progression."""
        # Create locations with existing suffixes
        create_book_location(filename="foo_2024-04.zim", status="target")
        create_book_location(filename="foo_2024-04a.zim", status="target")
        create_book_location(filename="foo_2024-04b.zim", status="target")

        # Should get next suffix
        result = compute_target_filename(
            dbsession,
            name="foo",
            flavour=None,
            date="2024-04-10",
        )
        assert result == "foo_2024-04c.zim"

    def test_gap_in_suffixes_uses_last(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Should use last suffix even if gaps exist."""
        # Create locations with a gap (a, c exist, b is missing)
        create_book_location(filename="bar_2024-05.zim", status="target")
        create_book_location(filename="bar_2024-05a.zim", status="target")
        # Note: bar_2024-05b.zim is missing
        create_book_location(filename="bar_2024-05c.zim", status="target")

        # Should get suffix after 'c', not reuse 'b'
        result = compute_target_filename(
            dbsession,
            name="bar",
            flavour=None,
            date="2024-05-10",
        )
        assert result == "bar_2024-05d.zim"

    def test_double_letter_suffix_progression(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Should progress to double letter suffixes when needed."""
        # Create locations through z
        create_book_location(filename="baz_2024-06.zim", status="target")
        for letter in "abcdefghijklmnopqrstuvwxyz":
            create_book_location(filename=f"baz_2024-06{letter}.zim", status="target")

        # Should wrap to aa
        result = compute_target_filename(
            dbsession,
            name="baz",
            flavour=None,
            date="2024-06-10",
        )
        assert result == "baz_2024-06aa.zim"

    def test_flavour_prevents_collision(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Different flavours should not collide."""
        # Create location for name without flavour
        create_book_location(filename="wiki_2024-07.zim", status="target")

        # Same name with flavour should not collide
        result = compute_target_filename(
            dbsession,
            name="wiki",
            flavour="maxi",
            date="2024-07-10",
        )
        assert result == "wiki_maxi_2024-07.zim"

    def test_mixed_status_locations_included(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Should consider both current and target locations."""
        # Create both current and target locations
        create_book_location(filename="mixed_2024-08.zim", status="current")
        create_book_location(filename="mixed_2024-08a.zim", status="target")

        # Should get suffix after 'a'
        result = compute_target_filename(
            dbsession,
            name="mixed",
            flavour=None,
            date="2024-08-10",
        )
        assert result == "mixed_2024-08b.zim"

    def test_different_period_no_collision(
        self, dbsession: OrmSession, create_book_location: Callable[..., BookLocation]
    ):
        """Different periods should not collide."""
        # Create location for different period
        create_book_location(filename="period_2024-08.zim", status="target")

        # Different period should not collide
        result = compute_target_filename(
            dbsession,
            name="period",
            flavour=None,
            date="2024-09-10",
        )
        assert result == "period_2024-09.zim"
