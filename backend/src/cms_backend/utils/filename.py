"""Utilities for computing and managing book target filenames."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import BookLocation

PERIOD_LENGTH = 7


def get_next_suffix(current_suffix: str) -> str:
    """
    Get the next suffix in sequence.

    Suffixes progress: "" -> "a" -> "b" -> ... -> "z" -> "aa" -> "ab" -> ...
    This is essentially a base-26 number system using lowercase letters.

    Args:
        current_suffix: The current suffix (e.g., "a", "z", "aa", "ab")

    Returns:
        The next suffix in sequence

    Examples:
        - "" -> "a"
        - "a" -> "b"
        - "z" -> "aa"
        - "ab" -> "ac"
        - "az" -> "ba"
        - "zz" -> "aaa"
    """
    if not current_suffix:
        return "a"

    # Convert suffix to list of chars for easier manipulation
    chars = list(current_suffix)

    # Increment from right to left (like a base-26 number)
    carry = True
    for i in range(len(chars) - 1, -1, -1):
        if carry:
            if chars[i] == "z":
                chars[i] = "a"
                # carry continues
            else:
                chars[i] = chr(ord(chars[i]) + 1)
                carry = False
                break

    # If we still have carry, we need an additional character
    if carry:
        chars.insert(0, "a")

    return "".join(chars)


def compute_target_filename(
    session: OrmSession,
    *,
    name: str,
    flavour: str | None,
    date: str,
    book_id: UUID | None = None,
) -> str:
    """
    Compute target filename: {name}[_{flavour}]_{period}[suffix]

    Period is YYYY-MM from book.date (format: YYYY-MM-DD), with suffix for multiple
    books in the same month:
    - YYYY-MM (no suffix, if available)
    - YYYY-MMa, YYYY-MMb, ..., YYYY-MMz (single letter)
    - YYYY-MMaa, YYYY-MMab, ... (multiple letters)

    Finds the last suffix already in use and generates the next one.
    Queries ALL book locations (any status) with filenames starting with base pattern,
    excluding locations from the current book to avoid self-collision.

    Important edge cases:
    - Books with same name but different flavours (including no flavour) never collide
    - If YYYY-MM and YYYY-MMa exist but YYYY-MMb was deleted, next is YYYY-MMc
      (finds last suffix, not collision)

    Args:
        session: SQLAlchemy session
        name: Book name
        flavour: Book flavour (optional)
        date: Book date (format: YYYY-MM-DD)
        book_id: ID of the book being processed (to exclude its own locations)

    Returns:
        Target filename including .zim extension

    Raises:
        ValueError: If date is missing or has invalid format
    """
    if not date:
        raise ValueError("Book date is required to compute target filename")

    # Extract YYYY-MM from book.date (format: YYYY-MM-DD)
    if len(date) < PERIOD_LENGTH:
        raise ValueError(f"Book date must have at least YYYY-MM format, got: {date}")

    base_period = date[:PERIOD_LENGTH]  # "2024-01-15" -> "2024-01"

    # Build base filename pattern
    # IMPORTANT: name with no flavour vs name with flavour never collide
    if flavour:
        base_name = f"{name}_{flavour}"
    else:
        base_name = name

    # Base pattern for this book (without .zim extension)
    base_pattern = f"{base_name}_{base_period}"

    # Query all locations where filename starts with this pattern
    # Check ALL locations regardless of status (current or target)
    # Exclude the current book's own locations to avoid self-collision
    stmt = select(BookLocation.filename).where(
        BookLocation.filename.like(f"{base_pattern}%")
    )
    if book_id is not None:
        stmt = stmt.where(BookLocation.book_id != book_id)

    existing_filenames = list(session.scalars(stmt).all())

    # If no existing files, use base pattern (no suffix)
    if not existing_filenames:
        return f"{base_pattern}.zim"

    # Parse existing filenames to find the highest suffix
    # Examples:
    #   - "foo_2024-01.zim" -> no suffix (empty string)
    #   - "foo_2024-01a.zim" -> "a"
    #   - "foo_2024-01ab.zim" -> "ab"

    suffixes: list[str] = []
    for filename in existing_filenames:
        # Remove .zim extension
        name_part = filename.rsplit(".zim", 1)[0]

        # Extract suffix after base_pattern
        if name_part == base_pattern:
            # No suffix
            suffixes.append("")
        elif name_part.startswith(base_pattern):
            suffix = name_part[len(base_pattern) :]
            # Validate it's only lowercase letters
            if suffix.isalpha() and suffix.islower():
                suffixes.append(suffix)

    # If no valid suffixes found, use base pattern
    if not suffixes:
        return f"{base_pattern}.zim"

    # Sort suffixes: "", "a", "b", ..., "z", "aa", "ab", ..., "zz", "aaa", ...
    suffixes.sort(key=lambda s: (len(s), s))

    # Get the last suffix and compute the next one
    last_suffix = suffixes[-1]
    next_suffix = get_next_suffix(last_suffix)

    return f"{base_pattern}{next_suffix}.zim"
