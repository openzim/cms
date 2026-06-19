from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import (
    book_has_recipe_issue,
    process_book,
)
from cms_backend.db.models import Book, Title
from cms_backend.db.rules import (
    apply_retention_rules,
    title_is_missing_mandatory_metadata,
)
from cms_backend.db.zimfarm_recipe import (
    create_zimfarm_recipe,
    get_zimfarm_recipe_by_id_or_none,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import compute_target_filename
from cms_backend.utils.zim import get_missing_keys


def add_book_to_title(session: OrmSession, book: Book, title: Title):
    """
    Associate a book with a given title, create target locations for move operations.

    When a book is to be added to a book title newly:
    - if recipe exists and its configuration matches book name and flavour, proceed
        to add it to the title
    - if recipe exists and its configuration is NOT matching book name and flavour,
        block the book in staging without an associated title and set issue to
        'recipe issue'
    - if recipe does not exist, create the recipe (without associated title), block the
        book in staging without an associated title and set issue to 'recipe issue'
    """
    try:
        # Retrieve name from book.name directly
        if not book.name:
            raise ValueError("book name is missing or invalid")

        # Validate book.date is also present and valid
        if not book.date:
            raise ValueError("book date is missing or invalid")

        if not book.zimfarm_notification:
            raise ValueError("book is missing zimfarm notification")

        missing_recipe_keys = get_missing_keys(
            book.zimfarm_notification.content, "recipe_id", "recipe_name"
        )
        if missing_recipe_keys:
            raise ValueError(
                "book notification is missing recipe details: "
                f"{','.join(missing_recipe_keys)}"
            )

        content = book.zimfarm_notification.content
        recipe = get_zimfarm_recipe_by_id_or_none(session, content["recipe_id"])
        if recipe is None:
            recipe = create_zimfarm_recipe(
                session,
                recipe_id=content["recipe_id"],
                recipe_name=content["recipe_name"],
            )
        recipe.name = content["recipe_name"]

        if book_has_recipe_issue(book.flavour, title, recipe):
            book.issues = ["recipe issue"]
            book.events.append(
                f"{getnow()}: cannot add book to title {title.id} "
                "because of recipe issue"
            )
        else:
            title.books.append(book)
            book.events.append(f"{getnow()}: book added to title {title.id}")
            title.events.append(f"{getnow()}: book {book.id} added to title")
            # Update title name should it have changed (e.g. stackexchange domain
            # updated
            # leading to ZIM name automatically updated as well)
            if title.name != book.name:
                title.events.append(f"{getnow()}: updating title name to {book.name}")
                title.name = book.name

            if title_is_missing_mandatory_metadata(title):
                title.title = book.zim_metadata["Title"]
                title.creator = book.zim_metadata["Creator"]
                title.publisher = book.zim_metadata["Publisher"]
                title.description = book.zim_metadata["Description"]
                title.language = book.zim_metadata["Language"]
                title.illustration_48x48_at_1 = book.zim_metadata[
                    "Illustration_48x48@1"
                ]
                title.long_description = book.zim_metadata.get("LongDescription")
                title.license = book.zim_metadata.get("License")
                title.relation = book.zim_metadata.get("Relation")
                title.source = book.zim_metadata.get("Source")

        # Compute target filename once for this book
        book.filename = compute_target_filename(
            session,
            name=book.name,
            flavour=book.flavour,
            date=book.date,
            book_id=book.id,
        )
        process_book(session, book, update_events=True)
        apply_retention_rules(session, title)

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        book.has_error = True
        logger.exception(f"Failed to add book {book.id} to title {title.id}")
