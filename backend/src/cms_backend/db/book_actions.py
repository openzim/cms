from collections import deque
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.book import (
    book_has_flavour_mismatch,
    book_has_recipe_issue,
    get_book,
    get_book_or_none,
    get_book_unsupported_languages,
    get_differing_metadata_keys,
    get_zimcheck_errors,
    move_book_to_destination,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.flavour import (
    create_title_flavour,
    get_title_flavour,
    get_title_flavour_or_none,
)
from cms_backend.db.models import Book
from cms_backend.db.rules import title_is_missing_mandatory_metadata
from cms_backend.db.title import create_title, restore_title, update_title
from cms_backend.schemas.models import (
    BaseBookPromotionAction,
    BookPromotionAction,
    RestoreTitlesSchema,
    TitleCreateSchema,
    TitleUpdateSchema,
)
from cms_backend.schemas.orms import (
    ZimcheckSummarySchema,
)
from cms_backend.utils.zim import (
    get_missing_keys,
    get_missing_metadata_keys,
)


def construct_recipe_link(recipe_id: UUID | None) -> str | None:
    if recipe_id is None:
        return None
    return f"{Context.zimfarm_api_url}/recipes/{recipe_id}"


def get_book_promotion_actions(
    session: OrmSession, *, book_id: UUID
) -> list[BookPromotionAction]:
    """Get actions required to promote a book to 'prod'."""
    book = get_book_or_none(
        session,
        book_id=book_id,
        has_error=False,
        needs_file_operation=False,
        needs_processing=False,
        locations=["staging", "quarantine"],
    )
    if book is None:
        raise RecordDoesNotExistError(
            f"Book {book_id} does not meet criteria to be validated"
        )

    actions: list[BookPromotionAction] = []

    missing_metadata_keys = get_missing_metadata_keys(book.zim_metadata)
    if missing_metadata_keys:
        raise ValueError(
            "Book is missing mandatory metadata keys and cannot "
            "possibly be promoted through to 'prod'"
        )

    unknown_languages = get_book_unsupported_languages(book)
    if unknown_languages:
        actions.append(
            BookPromotionAction(
                kind="unknown_languages",
                requirement="information",
                data={},
                message=(
                    "Book has unknown language code(s): "
                    f"{','.join(unknown_languages)}. "
                    "Please contact a CMS admin if code(s) look legit to you."
                ),
            )
        )

    zimcheck_errors = get_zimcheck_errors(book, raise_exceptions=False)
    if zimcheck_errors and book.zimcheck_summary:
        zimcheck_summary = ZimcheckSummarySchema.model_validate(book.zimcheck_summary)
        actions.append(
            BookPromotionAction(
                kind="zimcheck_issues",
                requirement="information",
                data={},
                message=f"Book has {zimcheck_summary.error_count} zimcheck error(s). ",
            )
        )

    if book.title is None:
        actions.append(
            BookPromotionAction(
                kind="create_title",
                requirement="mandatory",
                data={
                    "name": book.name,
                    "maturity": "stable",
                    "title": book.zim_metadata["Title"],
                    "creator": book.zim_metadata["Creator"],
                    "publisher": book.zim_metadata["Publisher"],
                    "description": book.zim_metadata["Description"],
                    "language": book.zim_metadata["Language"],
                    "illustration_48x48_at_1": book.zim_metadata[
                        "Illustration_48x48@1"
                    ],
                    "flavours": [
                        {
                            "flavour": book.flavour,
                            "recipe_link": construct_recipe_link(book.recipe_id),
                        }
                    ],
                    "collection_titles": [],
                },
                message="Create new title. Please configure title collection(s).",
            )
        )
        return actions

    title = book.title

    if title.archived:
        actions.append(
            BookPromotionAction(
                kind="restore_title",
                requirement="mandatory",
                data={"title_names": [title.name]},
                message=f"Restore title '{title.name}' from archive",
            )
        )

    if title_is_missing_mandatory_metadata(title) or get_differing_metadata_keys(book):
        actions.append(
            BookPromotionAction(
                kind="update_title_metadata",
                requirement="optional",
                data={
                    "title": book.zim_metadata["Title"],
                    "creator": book.zim_metadata["Creator"],
                    "publisher": book.zim_metadata["Publisher"],
                    "description": book.zim_metadata["Description"],
                    "language": book.zim_metadata["Language"],
                    "illustration_48x48_at_1": book.zim_metadata[
                        "Illustration_48x48@1"
                    ],
                },
                message="Update title metadata",
            )
        )

    if title.maturity != "stable":
        actions.append(
            BookPromotionAction(
                kind="update_title_maturity",
                requirement="optional",
                data={
                    "maturity": "stable",
                },
                message=f"Mark title '{title.maturity}' as stable.",
            )
        )
    if len(title.collections) == 0:
        actions.append(
            BookPromotionAction(
                kind="set_title_collections",
                requirement="mandatory",
                data={
                    "collection_titles": [],
                },
                message="Configure title collection(s)",
            )
        )

    if book_has_flavour_mismatch(book):
        title_flavours = [tf.flavour for tf in title.flavours]
        actions.append(
            BookPromotionAction(
                kind="create_title_flavour",
                requirement="mandatory",
                data={
                    "flavour": book.flavour,
                    "recipe_link": construct_recipe_link(book.recipe_id),
                },
                message=(
                    f"Add '{book.flavour}' to title flavours: "
                    f"{','.join(title_flavours)}"
                ),
            )
        )

    if book_has_recipe_issue(book):
        matching_flavour = get_title_flavour(session, title.id, book.flavour)
        actions.append(
            BookPromotionAction(
                kind="update_flavour_recipe",
                requirement="mandatory",
                data={
                    "recipe_id": book.recipe_id,
                    "recipe_link": construct_recipe_link(book.recipe_id),
                },
                message=(
                    f"Update flavour recipe from "
                    f"{construct_recipe_link(matching_flavour.recipe_id)} to "
                    f"{construct_recipe_link(book.recipe_id)}"
                ),
            )
        )

    return actions


def _apply_update_flavour_recipe_action(
    session: OrmSession, action: BaseBookPromotionAction, book: Book
):
    if book.title is None:
        raise ValueError("Book does not have an associated title")

    if get_missing_keys(action.data, "recipe_id"):
        raise ValueError("Action to update title flavour recipe must provide recipe id")
    if str(action.data["recipe_id"]) != str(book.recipe_id):
        raise ValueError(
            f"Provided recipe {action.data['recipe_id']} differs from book recipe "
            f"{book.recipe_id} and cannot solve book recipe issue."
        )
    title_flavour = get_title_flavour(session, book.title.id, book.flavour)
    title_flavour.recipe_id = book.recipe_id
    session.add(title_flavour)


def apply_book_promotion_actions(
    session: OrmSession,
    *,
    book_id: UUID,
    actions: list[BaseBookPromotionAction],
    author_id: UUID,
) -> None:
    """Apply a list of actions to book so that it can be promoted to 'prod'"""
    action_kinds = {action.kind for action in actions}
    if len(action_kinds) != len(actions):
        raise ValueError("Provided actions contain duplicates")

    book = get_book(session, book_id=book_id)
    expected_actions = get_book_promotion_actions(session, book_id=book_id)

    expected_actions_set = {action.kind for action in expected_actions}
    provided_actions_set = {action.kind for action in actions}

    unknown_actions = provided_actions_set - expected_actions_set
    if unknown_actions:
        raise ValueError(
            "One or more provided actions are not in the list of expected actions "
            f"to promote the book. Unexpected actions: "
            f"{','.join(sorted(unknown_actions))}; "
            f"expected actions: {','.join(sorted(expected_actions_set))}"
        )
    expected_mandatory_actions = {
        action.kind for action in expected_actions if action.requirement == "mandatory"
    }
    provided_mandatory_actions = {
        action.kind for action in actions if action.requirement == "mandatory"
    }
    if expected_mandatory_actions != provided_mandatory_actions:
        raise ValueError(
            "The mandatory actions provided do not match the expected mandatory "
            "actions. Expected mandatory actions: "
            f"{','.join(sorted(expected_mandatory_actions))}; provided mandatory "
            f"actions: {','.join(sorted(provided_mandatory_actions))}"
        )
    actions_todo = deque(actions)
    # Batch the updates to a title in a common payload
    title_update_payload: dict[str, Any] = {}
    while actions_todo:
        action = actions_todo.popleft()
        match action.kind:
            case "create_title":
                payload = TitleCreateSchema.model_validate(action.data)
                if not payload.collection_titles:
                    raise ValueError(
                        "Title must have at least one collection configured."
                    )
                title = create_title(session, author_id=author_id, payload=payload)
                book.title = title
                if get_title_flavour_or_none(session, title.id, book.flavour) is None:
                    create_title_flavour(
                        session,
                        title,
                        book.recipe_id,
                        book.flavour,
                    )

            case "restore_title":
                if not book.title:
                    raise ValueError(
                        "Book does not have an associated title to restore"
                    )
                payload = RestoreTitlesSchema.model_validate(action.data)
                if (
                    len(payload.title_names) != 1
                    or payload.title_names[0] != book.title.name
                ):
                    raise ValueError(
                        "Only the book's title should be specified in "
                        "the restore payload"
                    )
                book.title = restore_title(
                    session,
                    title_identifier=payload.title_names[0],
                    author_id=author_id,
                )
            case "update_title_metadata":
                missing_keys = get_missing_keys(
                    action.data,
                    "title",
                    "creator",
                    "publisher",
                    "description",
                    "language",
                    "illustration_48x48_at_1",
                )
                if missing_keys:
                    raise ValueError("Title must be updated with mandatory metadata")
                title_update_payload.update(**action.data)
            case "update_title_maturity":
                if get_missing_keys(action.data, "maturity"):
                    raise ValueError(
                        "Action to update title maturity must set maturity value"
                    )
                title_update_payload.update(**action.data)
            case "create_title_flavour":
                if action.data.get("flavour") is None:
                    raise ValueError(
                        "Action to update title flavours must set flavour value"
                    )
                if not book.title:
                    raise ValueError("Book does not have an associated title")

                if (
                    get_title_flavour_or_none(
                        session, book.title.id, action.data["flavour"]
                    )
                    is None
                ):
                    create_title_flavour(
                        session,
                        title=book.title,
                        recipe_id=book.recipe_id,
                        flavour=action.data["flavour"],
                    )
            case "set_title_collections":
                if get_missing_keys(action.data, "collection_titles") or (
                    isinstance(action.data["collection_titles"], list)
                    and not (action.data["collection_titles"])
                ):
                    raise ValueError(
                        "Action to update title collections must provide "
                        "collection details"
                    )
                title_update_payload.update(**action.data)
            case "update_flavour_recipe":
                _apply_update_flavour_recipe_action(session, action, book)
            case "unknown_languages" | "zimcheck_issues":
                pass

    if book.title is None:
        raise ValueError("Book does not have an associated title")

    if title_update_payload:
        payload = TitleUpdateSchema.model_validate(title_update_payload)
        book.title = update_title(
            session,
            title_identifier=book.title.name,
            author_id=author_id,
            payload=payload,
            create_event=False,
        )

    move_book_to_destination(session, book=book, destination="prod")
