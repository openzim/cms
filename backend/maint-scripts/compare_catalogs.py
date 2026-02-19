#!/usr/bin/env python3
"""Maintenance script to compare two XML catalog files.

This script:
- Downloads XML files from two sources and caches them locally
- Compares the catalogs ignoring tag and attribute ordering
- Uses book.id as the unique identifier for comparison
- Reports differences in structure, attributes, and content
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import requests

from cms_backend import logger

CACHE_DIR = Path(__file__).parent / ".cache"

REPORT_FIRSTS_LIST_DIFFS = 10
REPORT_FIRSTS_CONTENT_DIFFS = 3
REPORT_FIRSTS_BOOKS_DIFFS = 5


def get_cache_path(url: str) -> Path:
    """Get the cache path for a URL based on its hash."""
    url_hash = hashlib.md5(url.encode()).hexdigest()  # noqa: S324
    return CACHE_DIR / f"{url_hash}.xml"


def download_file(url: str, *, force: bool = False) -> Path:
    """Download a file and cache it locally.

    Args:
        url: URL to download
        force: If True, re-download even if cached

    Returns:
        Path to the cached file
    """
    cache_path = get_cache_path(url)

    if cache_path.exists() and not force:
        logger.info(f"✓ Using cached file: {cache_path}")
        return cache_path

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"⬇ Downloading from: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    cache_path.write_bytes(response.content)
    logger.info(f"✓ Saved to cache: {cache_path}")
    return cache_path


def normalize_element(elem: ET.Element) -> dict[str, Any]:
    """Convert an XML element to a normalized dictionary form.

    This makes comparison order-independent.
    """
    return {
        "tag": elem.tag,
        "text": (elem.text or "").strip(),
        "tail": (elem.tail or "").strip(),
        "attrib": dict(elem.attrib),
        "children": sorted(
            [normalize_element(child) for child in elem],
            key=lambda x: (x["tag"], str(x["attrib"])),
        ),
    }


def compare_elements(
    elem1: dict[str, Any], elem2: dict[str, Any], path: str = ""
) -> list[str]:
    """Compare two normalized elements and return differences."""
    diffs: list[str] = []
    current_path = f"{path}/{elem1['tag']}" if path else elem1["tag"]

    # Compare tags
    if elem1["tag"] != elem2["tag"]:
        diffs.append(f"{current_path}: Tag mismatch - {elem1['tag']} vs {elem2['tag']}")
        return diffs

    # Compare text content
    if elem1["text"] != elem2["text"]:
        diffs.append(
            f"{current_path}: Text content differs\n"
            f"  File 1: {elem1['text'][:100]}\n"
            f"  File 2: {elem2['text'][:100]}"
        )

    # Compare attributes
    attrs1 = elem1["attrib"]
    attrs2 = elem2["attrib"]

    for key in set(list(attrs1.keys()) + list(attrs2.keys())):
        if attrs1.get(key) != attrs2.get(key):
            # Special case: ignore size attribute difference of exactly 1 byte
            if key == "size":
                try:
                    size1 = int(attrs1.get(key, 0))
                    size2 = int(attrs2.get(key, 0))
                    if abs(size1 - size2) == 1:
                        continue
                except (ValueError, TypeError):
                    pass

            diffs.append(
                f"{current_path}: Attribute '{key}' differs\n"
                f"  File 1: {attrs1.get(key)}\n"
                f"  File 2: {attrs2.get(key)}"
            )

    # Compare children
    children1 = elem1["children"]
    children2 = elem2["children"]

    if len(children1) != len(children2):
        diffs.append(
            f"{current_path}: Different number of children "
            f"({len(children1)} vs {len(children2)})"
        )

    # Match children by tag for comparison
    for child1, child2 in zip(children1, children2, strict=False):
        diffs.extend(compare_elements(child1, child2, current_path))

    return diffs


def compare_by_book_id(root1: ET.Element, root2: ET.Element) -> dict[str, Any]:
    """Compare catalogs by book.id as unique key."""
    # Extract books indexed by id
    books1: dict[str, Any] = {}
    books2: dict[str, Any] = {}

    for book in root1.findall(".//book"):
        book_id = book.get("id")
        if book_id:
            books1[book_id] = normalize_element(book)

    for book in root2.findall(".//book"):
        book_id = book.get("id")
        if book_id:
            books2[book_id] = normalize_element(book)

    all_ids: set[str] = set(list(books1.keys()) + list(books2.keys()))

    result: dict[str, list[str | dict[str, Any]]] = {
        "only_in_file1": [],
        "only_in_file2": [],
        "different": [],
    }

    for book_id in sorted(all_ids):
        if book_id not in books1:
            result["only_in_file2"].append(book_id)
        elif book_id not in books2:
            result["only_in_file1"].append(book_id)
        else:
            diffs = compare_elements(books1[book_id], books2[book_id])
            if diffs:
                result["different"].append({"book_id": book_id, "diffs": diffs})

    return result


def main(
    url1: str | None = None, url2: str | None = None, *, force: bool = False
) -> int:
    """Compare two catalog XML files."""
    # Default URLs
    if url1 is None:
        url1 = "https://api.cms.openzim.org/v1/collections/Kiwix/catalog.xml"
    if url2 is None:
        url2 = "https://download.kiwix.org/library/library_zim.xml"

    try:
        # Download files
        logger.info("=" * 70)
        logger.info("File 1:")
        file1 = download_file(url1, force=force)

        logger.info("\nFile 2:")
        file2 = download_file(url2, force=force)
        logger.info("=" * 70)

        # Parse XML
        logger.info("\n📄 Parsing XML files...")
        root1 = ET.parse(file1).getroot()  # noqa: S314
        root2 = ET.parse(file2).getroot()  # noqa: S314

        # Compare
        logger.info("🔍 Comparing catalogs by book.id...\n")
        comparison = compare_by_book_id(root1, root2)

        # Report results
        total_books = len(
            set(
                list(comparison["only_in_file1"])
                + list(comparison["only_in_file2"])
                + [item["book_id"] for item in comparison["different"]]
            )
        )

        logger.info(f"📊 Summary: {total_books} total unique books found\n")

        if comparison["only_in_file1"]:
            logger.warning(
                f"⚠️  Only in File 1 ({len(comparison['only_in_file1'])} books):"
            )
            for book_id in comparison["only_in_file1"][:REPORT_FIRSTS_LIST_DIFFS]:
                logger.warning(f"   - {book_id}")
            if len(comparison["only_in_file1"]) > REPORT_FIRSTS_LIST_DIFFS:
                logger.warning(
                    "   ... and "
                    f"{len(comparison['only_in_file1']) - REPORT_FIRSTS_LIST_DIFFS}"
                    " more"
                )
            logger.warning("")

        if comparison["only_in_file2"]:
            logger.warning(
                f"⚠️  Only in File 2 ({len(comparison['only_in_file2'])} books):"
            )
            for book_id in comparison["only_in_file2"][:REPORT_FIRSTS_LIST_DIFFS]:
                logger.warning(f"   - {book_id}")
            if len(comparison["only_in_file2"]) > REPORT_FIRSTS_LIST_DIFFS:
                logger.warning(
                    "   ... and "
                    f"{len(comparison['only_in_file2']) - REPORT_FIRSTS_LIST_DIFFS}"
                    " more"
                )
            logger.warning("")

        if comparison["different"]:
            logger.warning(
                f"❌ Different content ({len(comparison['different'])} books):"
            )
            for item in comparison["different"][:REPORT_FIRSTS_BOOKS_DIFFS]:
                logger.info(f"\n   Book: {item['book_id']}")
                for diff in item["diffs"][:REPORT_FIRSTS_CONTENT_DIFFS]:
                    # Indent the diff
                    for line in diff.split("\n"):
                        logger.info(f"      {line}")
                if len(item["diffs"]) > REPORT_FIRSTS_CONTENT_DIFFS:
                    diff_count = len(item["diffs"]) - REPORT_FIRSTS_CONTENT_DIFFS
                    logger.info(f"      ... and {diff_count} more differences")
            if len(comparison["different"]) > REPORT_FIRSTS_BOOKS_DIFFS:
                diff_count = len(comparison["different"]) - REPORT_FIRSTS_BOOKS_DIFFS
                logger.info(f"\n   ... and {diff_count} more books with differences")
            logger.info("")

        if not any(comparison.values()):
            logger.info("✅ Catalogs are identical!")
            return 0
        else:
            logger.warning("⚠️  Catalogs have differences")
            return 1

    except requests.RequestException as e:
        logger.error(f"❌ Network error: {e}")
        return 1
    except ET.ParseError as e:
        logger.error(f"❌ XML parse error: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare two XML catalog files")
    parser.add_argument(
        "--url1", help="URL of first catalog (default: api.cms.openzim.org)"
    )
    parser.add_argument(
        "--url2", help="URL of second catalog (default: download.kiwix.org)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-download files, ignore cache"
    )

    args = parser.parse_args()

    sys.exit(main(url1=args.url1, url2=args.url2, force=args.force))
