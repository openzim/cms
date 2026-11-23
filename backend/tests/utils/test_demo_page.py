from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from cms_backend.db.collection import LibraryBookData
from cms_backend.db.models import Book, Collection, Title
from cms_backend.utils import demo_page
from cms_backend.utils.demo_page import build_collection_demo_html


def _make_entry(
    *,
    title: str = "Test Title",
    description: str = "A test book",
    language: str = "eng",
    date: str = "2025-01-01",
    size: int = 1024,
    flavour: str = "full",
    transition_status: str | None = None,
    illustration: str | None = None,
    zim_metadata: dict[str, Any] | None = None,
    download_base_url: str | None = "https://download.kiwix.org/zim/",
    filename: str = "test_en_all.zim",
) -> LibraryBookData:
    book = SimpleNamespace(
        zim_metadata=zim_metadata or {},
        size=size,
        date=date,
        flavour=flavour,
        transition_status=transition_status,
    )
    zim_title = SimpleNamespace(
        title=title,
        description=description,
        language=language,
        illustration_48x48_at_1=illustration,
    )
    return LibraryBookData(
        book=cast(Book, book),
        title=cast(Title, zim_title),
        download_base_url=download_base_url,
        path=Path("wikipedia"),
        filename=filename,
    )


def test_format_size() -> None:
    assert demo_page._format_size(0) == ""  # pyright: ignore[reportPrivateUsage]
    assert demo_page._format_size(-1) == ""  # pyright: ignore[reportPrivateUsage]
    assert demo_page._format_size(1) == "1 B"  # pyright: ignore[reportPrivateUsage]
    assert (
        demo_page._format_size(1536) == "1.5 KB"  # pyright: ignore[reportPrivateUsage]
    )
    assert (
        demo_page._format_size(1024 * 1024)  # pyright: ignore[reportPrivateUsage]
        == "1.0 MB"
    )
    assert (
        demo_page._format_size(1024**4) == "1.0 TB"  # pyright: ignore[reportPrivateUsage]
    )
    assert (
        demo_page._format_size(1024**5)  # pyright: ignore[reportPrivateUsage]
        == "1024.0 TB"
    )


def test_build_collection_demo_html_empty() -> None:
    collection = SimpleNamespace(name="demo", view_base_url=None)
    html = build_collection_demo_html(cast(Collection, collection), [])
    assert "demo" in html
    assert "No books are currently available" in html


def test_build_collection_demo_html_with_links() -> None:
    collection = SimpleNamespace(
        name="demo",
        view_base_url="https://library.kiwix.org/content/",
    )
    entry = _make_entry()
    html = build_collection_demo_html(cast(Collection, collection), [entry])
    assert "Test Title" in html
    assert "A test book" in html
    assert "https://download.kiwix.org/zim/wikipedia/test_en_all.zim" in html
    assert "https://library.kiwix.org/content/test_en_all" in html
    assert ">Browse<" in html
    assert ">Download<" in html


def test_build_collection_demo_html_no_links() -> None:
    collection = SimpleNamespace(name="demo", view_base_url=None)
    entry = _make_entry(download_base_url=None)
    html = build_collection_demo_html(cast(Collection, collection), [entry])
    assert ">Download<" not in html
    assert ">Browse<" not in html
    assert "—" in html


def test_build_collection_demo_html_browse_blocked_by_transition() -> None:
    collection = SimpleNamespace(
        name="demo",
        view_base_url="https://library.kiwix.org/content/",
    )
    entry = _make_entry(transition_status="checking_library")
    html = build_collection_demo_html(cast(Collection, collection), [entry])
    assert ">Browse<" not in html
    assert ">Download<" in html


def test_build_collection_demo_html_with_illustration() -> None:
    collection = SimpleNamespace(name="demo", view_base_url=None)
    entry = _make_entry(illustration="abc123")
    html = build_collection_demo_html(cast(Collection, collection), [entry])
    assert 'src="data:image/png;base64,abc123"' in html


def test_build_collection_demo_html_view_url_without_zim_suffix() -> None:
    collection = SimpleNamespace(
        name="demo",
        view_base_url="https://library.kiwix.org/content/",
    )
    entry = _make_entry(filename="test_en_all")
    html = build_collection_demo_html(cast(Collection, collection), [entry])
    assert "https://library.kiwix.org/content/test_en_all" in html
    assert ">Browse<" in html


def test_build_collection_demo_html_with_none_zim_metadata() -> None:
    collection = SimpleNamespace(name="demo", view_base_url=None)
    entry = _make_entry(zim_metadata=None, title="", description="")
    html = build_collection_demo_html(cast(Collection, collection), [entry])
    assert "test_en_all.zim" in html
