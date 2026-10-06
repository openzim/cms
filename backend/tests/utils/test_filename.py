"""Tests for filename utilities."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book
from cms_backend.utils.filename import (
    compute_target_filename,
    get_next_suffix,
    normalize_download_location,
)


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


class TestNormalizeDownloadLocation:
    """Test the normalize_download_location function."""

    def test_zim_location_is_returned(self):
        assert normalize_download_location(
            "https://lb.download.kiwix.org/zim/foo_en_all_2026-01.zim"
        ) == ("lb.download.kiwix.org", "/zim/foo_en_all_2026-01.zim")

    def test_torrent_is_folded_to_zim(self):
        assert normalize_download_location(
            "https://lb.download.kiwix.org/zim/foo_en_all_2026-01.zim.torrent"
        ) == ("lb.download.kiwix.org", "/zim/foo_en_all_2026-01.zim")

    def test_meta4_is_folded_to_zim(self):
        assert normalize_download_location(
            "https://lb.download.kiwix.org/zim/foo_en_all_2026-01.zim.meta4"
        ) == ("lb.download.kiwix.org", "/zim/foo_en_all_2026-01.zim")

    def test_query_string_is_ignored(self):
        assert normalize_download_location(
            "https://lb.download.kiwix.org/foo.zim?foo=bar"
        ) == ("lb.download.kiwix.org", "/foo.zim")

    def test_url_encoded_path_is_decoded(self):
        assert normalize_download_location(
            "https://lb.download.kiwix.org/zim/foo%20bar.zim"
        ) == ("lb.download.kiwix.org", "/zim/foo bar.zim")

    def test_host_case_is_normalized(self):
        assert normalize_download_location("https://LB.Download.Kiwix.org/foo.zim") == (
            "lb.download.kiwix.org",
            "/foo.zim",
        )

    def test_scheme_less_host_path_is_supported(self):
        assert normalize_download_location("lb.download.kiwix.org/zim/foo.zim") == (
            "lb.download.kiwix.org",
            "/zim/foo.zim",
        )

    @pytest.mark.parametrize(
        "url",
        [
            "https://lb.download.kiwix.org/index.html",
            "https://lb.download.kiwix.org/",
            "https://lb.download.kiwix.org/zim/",
        ],
    )
    def test_non_zim_urls_return_none(self, url: str):
        assert normalize_download_location(url) is None


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
        """When no existing books, should use base pattern."""
        # Fresh database has no books
        result = compute_target_filename(
            dbsession,
            name="new_book",
            flavour=None,
            date="2024-02-20",
        )
        assert result == "new_book_2024-02.zim"

    def test_collision_handling_single_letter(
        self, dbsession: OrmSession, create_book: Callable[..., Book]
    ):
        """Should handle collision with single letter suffix."""
        # Create first book (base pattern)
        create_book(
            filename="test_book_2024-03.zim",
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
        self, dbsession: OrmSession, create_book: Callable[..., Book]
    ):
        """Should handle multiple collisions in progression."""
        # Create books with existing suffixes
        create_book(filename="foo_2024-04.zim")
        create_book(filename="foo_2024-04a.zim")
        create_book(filename="foo_2024-04b.zim")

        # Should get next suffix
        result = compute_target_filename(
            dbsession,
            name="foo",
            flavour=None,
            date="2024-04-10",
        )
        assert result == "foo_2024-04c.zim"

    def test_gap_in_suffixes_uses_last(
        self, dbsession: OrmSession, create_book: Callable[..., Book]
    ):
        """Should use last suffix even if gaps exist."""
        # Create books with a gap (a, c exist, b is missing)
        create_book(filename="bar_2024-05.zim")
        create_book(filename="bar_2024-05a.zim")
        # Note: bar_2024-05b.zim is missing
        create_book(filename="bar_2024-05c.zim")

        # Should get suffix after 'c', not reuse 'b'
        result = compute_target_filename(
            dbsession,
            name="bar",
            flavour=None,
            date="2024-05-10",
        )
        assert result == "bar_2024-05d.zim"

    def test_double_letter_suffix_progression(
        self, dbsession: OrmSession, create_book: Callable[..., Book]
    ):
        """Should progress to double letter suffixes when needed."""
        # Create books through z
        create_book(filename="baz_2024-06.zim")
        for letter in "abcdefghijklmnopqrstuvwxyz":
            create_book(filename=f"baz_2024-06{letter}.zim")

        # Should wrap to aa
        result = compute_target_filename(
            dbsession,
            name="baz",
            flavour=None,
            date="2024-06-10",
        )
        assert result == "baz_2024-06aa.zim"

    def test_flavour_prevents_collision(
        self, dbsession: OrmSession, create_book: Callable[..., Book]
    ):
        """Different flavours should not collide."""
        # Create book for name without flavour
        create_book(filename="wiki_2024-07.zim")

        # Same name with flavour should not collide
        result = compute_target_filename(
            dbsession,
            name="wiki",
            flavour="maxi",
            date="2024-07-10",
        )
        assert result == "wiki_maxi_2024-07.zim"

    def test_different_period_no_collision(
        self, dbsession: OrmSession, create_book: Callable[..., Book]
    ):
        """Different periods should not collide."""
        # Create book for different period
        create_book(filename="period_2024-08.zim")

        # Different period should not collide
        result = compute_target_filename(
            dbsession,
            name="period",
            flavour=None,
            date="2024-09-10",
        )
        assert result == "period_2024-09.zim"
