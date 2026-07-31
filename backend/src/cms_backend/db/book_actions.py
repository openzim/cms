from collections import deque
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import construct_recipe_link
from cms_backend.db.book import (
    add_book_to_title,
    book_has_flavour_mismatch,
    book_has_recipe_issue,
    get_book,
    get_book_article_count_issues,
    get_book_media_count_issues,
    get_book_or_none,
    get_book_unsupported_languages,
    get_differing_metadata_keys,
    get_latest_prod_book,
    get_zimcheck_errors,
    move_book_to_destination,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.flavour import (
    create_title_flavour,
    get_title_flavour,
    get_title_flavour_or_none,
)
from cms_backend.db.models import Account, Book
from cms_backend.db.title import create_title, restore_title, update_title
from cms_backend.roles import RoleEnum
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
from cms_backend.utils.datetime import getnow
from cms_backend.utils.zim import (
    get_missing_keys,
    get_missing_metadata_keys,
)


def _get_update_title_metadata_action(
    book: Book, account: Account
) -> BookPromotionAction | None:
    differing_metadata_keys = get_differing_metadata_keys(book)
    # Mapping of metadata fields to identifiers in TitleUpdatePayload
    metadata_to_identifier_map = {
        "Name": "name",
        "Title": "title",
        "Creator": "creator",
        "Publisher": "publisher",
        "Description": "description",
        "Language": "language",
        "Illustration_48x48@1": "illustration_48x48_at_1",
        "LongDescription": "long_description",
        "License": "license",
        "Relation": "relation",
        "Source": "source",
    }

    # Only accounts with sufficient permissions can update the Name metadata
    if (
        account.role not in [RoleEnum.GLOBAL_EDITOR, RoleEnum.ADMIN]
        and "Name" in differing_metadata_keys
    ):
        differing_metadata_keys.remove("Name")

    if differing_metadata_keys:
        return BookPromotionAction(
            kind="update_title_metadata",
            requirement="optional",
            data={
                metadata_to_identifier_map[key]: book.zim_metadata.get(key)
                for key in differing_metadata_keys
            },
            message="Update title metadata from book",
        )


def _get_unknown_languages_action(book: Book) -> BookPromotionAction | None:
    unknown_languages = get_book_unsupported_languages(book)
    if unknown_languages:
        return BookPromotionAction(
            kind="unknown_languages",
            requirement="information",
            data={},
            message=(
                "Book has unknown language code(s): "
                f"{','.join(unknown_languages)}. "
                "Please contact a CMS admin if code(s) look legit to you."
            ),
        )


def _get_zimcheck_issues_action(book: Book) -> BookPromotionAction | None:
    zimcheck_errors = get_zimcheck_errors(book, raise_exceptions=False)
    if zimcheck_errors:
        if book.zimcheck_summary:
            zimcheck_summary = ZimcheckSummarySchema.model_validate(
                book.zimcheck_summary
            )
            return BookPromotionAction(
                kind="zimcheck_issues",
                requirement="information",
                data={},
                message=f"Book has {zimcheck_summary.error_count} zimcheck error(s). ",
            )
        return BookPromotionAction(
            kind="zimcheck_issues",
            requirement="information",
            data={},
            message=";".join(zimcheck_errors),
        )


def _get_media_count_issues_action(book: Book, latest_book: Book):
    media_count_issues = get_book_media_count_issues(book=book, latest_book=latest_book)
    if media_count_issues:
        return BookPromotionAction(
            kind="media_count",
            requirement="information",
            data={},
            message=";".join(media_count_issues),
        )


def _get_article_count_issues_action(book: Book, latest_book: Book):
    article_count_issues = get_book_article_count_issues(
        book=book, latest_book=latest_book
    )
    if article_count_issues:
        return BookPromotionAction(
            kind="article_count",
            requirement="information",
            data={},
            message=";".join(article_count_issues),
        )


def _get_create_title_action(book: Book) -> BookPromotionAction | None:
    if book.title is None:
        return BookPromotionAction(
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
                "illustration_48x48_at_1": book.zim_metadata["Illustration_48x48@1"],
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


def _get_restore_title_action(book: Book) -> BookPromotionAction | None:
    if book.title is None:
        raise ValueError("Book must be associated with a title")

    if book.title.archived:
        return BookPromotionAction(
            kind="restore_title",
            requirement="mandatory",
            data={"title_names": [book.title.name]},
            message=f"Restore title '{book.title.name}' from archive",
        )


def _get_update_title_maturity_action(book: Book) -> BookPromotionAction | None:
    if book.title is None:
        raise ValueError("Book must be associated with a title")

    if book.title.maturity != "stable":
        return BookPromotionAction(
            kind="update_title_maturity",
            requirement="optional",
            data={
                "maturity": "stable",
            },
            message=f"Mark title '{book.title.maturity}' as stable.",
        )


def _get_set_title_collections_action(book: Book) -> BookPromotionAction | None:
    if book.title is None:
        raise ValueError("Book must be associated with a title")

    if len(book.title.collections) == 0:
        return BookPromotionAction(
            kind="set_title_collections",
            requirement="mandatory",
            data={
                "collection_titles": [],
            },
            message="Configure title collection(s)",
        )


def _get_create_title_flavour_action(book: Book) -> BookPromotionAction | None:
    if book.title is None:
        raise ValueError("Book must be associated with a title")

    if book_has_flavour_mismatch(book):
        title_flavours = [tf.flavour for tf in book.title.flavours]
        return BookPromotionAction(
            kind="create_title_flavour",
            requirement="mandatory",
            data={
                "flavour": book.flavour,
                "recipe_link": construct_recipe_link(book.recipe_id),
            },
            message=(
                f"Add '{book.flavour}' to title flavours: {','.join(title_flavours)}"
            ),
        )


def _get_update_flavour_recipe_action(
    session: OrmSession, book: Book
) -> BookPromotionAction | None:
    if book.title is None:
        raise ValueError("Book must be associated with a title")

    if book_has_recipe_issue(book):
        matching_flavour = get_title_flavour(session, book.title.id, book.flavour)
        return BookPromotionAction(
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


def get_book_promotion_actions(
    session: OrmSession,
    *,
    book_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
    account: Account,
) -> list[BookPromotionAction]:
    """Get actions required to promote a book to 'prod'."""
    book = get_book_or_none(
        session,
        book_id=book_id,
        accessible_collection_ids=accessible_collection_ids,
        has_error=False,
        needs_file_operation=False,
        needs_processing=False,
        locations=["staging", "quarantine"],
    )
    if book is None:
        raise RecordDoesNotExistError(
            f"Book {book_id} does not meet criteria to be validated or is not "
            "accessible to you"
        )

    actions: list[BookPromotionAction] = []

    missing_metadata_keys = get_missing_metadata_keys(book.zim_metadata)
    if missing_metadata_keys:
        raise ValueError(
            "Book is missing mandatory metadata keys and cannot "
            "possibly be promoted through to 'prod'"
        )

    if action := _get_unknown_languages_action(book):
        actions.append(action)

    if action := _get_zimcheck_issues_action(book):
        actions.append(action)

    latest_book = get_latest_prod_book(session, book)
    if action := _get_media_count_issues_action(book, latest_book):
        actions.append(action)

    if action := _get_article_count_issues_action(book, latest_book):
        actions.append(action)

    if action := _get_create_title_action(book):
        actions.append(action)
        return actions

    if action := _get_restore_title_action(book):
        actions.append(action)

    if action := _get_update_title_metadata_action(book, account):
        actions.append(action)

    if action := _get_update_title_maturity_action(book):
        actions.append(action)

    if action := _get_set_title_collections_action(book):
        actions.append(action)

    if action := _get_create_title_flavour_action(book):
        actions.append(action)

    if action := _get_update_flavour_recipe_action(session, book):
        actions.append(action)

    return actions


def _apply_restore_title_action(
    session: OrmSession,
    action: BaseBookPromotionAction,
    book: Book,
    author_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
):

    if not book.title:
        raise ValueError("Book does not have an associated title to restore")
    payload = RestoreTitlesSchema.model_validate(action.data)
    if len(payload.title_names) != 1 or payload.title_names[0] != book.title.name:
        raise ValueError(
            "Only the book's title should be specified in the restore payload"
        )
    book.title = restore_title(
        session,
        title_identifier=payload.title_names[0],
        author_id=author_id,
        accessible_collection_ids=accessible_collection_ids,
    )


def _apply_create_title_flavour_action(
    session: OrmSession, action: BaseBookPromotionAction, book: Book
):

    if action.data.get("flavour") is None:
        raise ValueError("Action to update title flavours must set flavour value")
    if not book.title:
        raise ValueError("Book does not have an associated title")

    tf = get_title_flavour_or_none(session, book.title.id, action.data["flavour"])
    if tf is None:
        tf = create_title_flavour(
            session,
            title=book.title,
            recipe_id=book.recipe_id,
            flavour=action.data["flavour"],
        )
    tf.last_book_added_at = getnow()


def _validate_create_title_action(
    expected_action: BaseBookPromotionAction, provided_action: BaseBookPromotionAction
):
    expected_payload = TitleCreateSchema.model_validate(expected_action.data)
    provided_payload = TitleCreateSchema.model_validate(provided_action.data)
    if expected_payload.collection_titles:
        if not provided_payload.collection_titles:
            raise ValueError(
                "Expected collection titles for action differ from "
                "provided collection titles."
            )
        expected_collection_titles: set[str] = {
            f"{entry.collection_name}:{entry.path}"
            for entry in expected_payload.collection_titles
        }
        provided_collection_titles: set[str] = {
            f"{entry.collection_name}:{entry.path}"
            for entry in provided_payload.collection_titles
        }
        if expected_collection_titles != provided_collection_titles:
            raise ValueError(
                "Expected collection titles for action differ from "
                "provided collection titles."
            )


def _apply_create_title_action(
    session: OrmSession,
    action: BaseBookPromotionAction,
    book: Book,
    author_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
):
    payload = TitleCreateSchema.model_validate(action.data)
    if not payload.collection_titles:
        raise ValueError("Title must have at least one collection configured.")
    title = create_title(
        session,
        author_id=author_id,
        payload=payload,
        accessible_collection_ids=accessible_collection_ids,
    )
    tf = get_title_flavour_or_none(session, title.id, book.flavour)
    if tf is None:
        tf = create_title_flavour(
            session,
            title,
            book.recipe_id,
            book.flavour,
        )
    tf.last_book_added_at = getnow()
    # Set book location kind to prod so that when we re-process, it moves
    # to prod location despite any issues that may be computed
    book.location_kind = "prod"
    add_book_to_title(session, book, title)


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
    account: Account,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> None:
    """Apply a list of actions to book so that it can be promoted to 'prod'"""
    action_kinds = {action.kind for action in actions}
    if len(action_kinds) != len(actions):
        raise ValueError("Provided actions contain duplicates")

    book = get_book(
        session, book_id=book_id, accessible_collection_ids=accessible_collection_ids
    )
    expected_actions = get_book_promotion_actions(
        session,
        book_id=book_id,
        accessible_collection_ids=accessible_collection_ids,
        account=account,
    )

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
                _validate_create_title_action(
                    next(
                        expected_action
                        for expected_action in expected_actions
                        if expected_action.kind == action.kind
                    ),
                    action,
                )
                _apply_create_title_action(
                    session,
                    action,
                    book,
                    account.id,
                    accessible_collection_ids=accessible_collection_ids,
                )
                return
            case "restore_title":
                _apply_restore_title_action(
                    session,
                    action,
                    book,
                    account.id,
                    accessible_collection_ids=accessible_collection_ids,
                )
            case "update_title_metadata":
                expected_action = next(
                    action
                    for action in expected_actions
                    if action.kind == "update_title_metadata"
                )
                missing_keys = set(expected_action.data.keys()) - set(
                    action.data.keys()
                )
                if missing_keys:
                    raise ValueError(
                        "Title must be updated with all metadata keys: "
                        f"{' '.join(missing_keys)}"
                    )
                title_update_payload.update(**action.data)
            case "update_title_maturity":
                if get_missing_keys(action.data, "maturity"):
                    raise ValueError(
                        "Action to update title maturity must set maturity value"
                    )
                title_update_payload.update(**action.data)
            case "create_title_flavour":
                _apply_create_title_flavour_action(session, action, book)
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
            case (
                "unknown_languages"
                | "zimcheck_issues"
                | "media_count"
                | "article_count"
            ):
                pass

    if book.title is None:
        raise ValueError("Book does not have an associated title")

    if title_update_payload:
        payload = TitleUpdateSchema.model_validate(title_update_payload)
        book.title = update_title(
            session,
            title_identifier=book.title.name,
            author_id=account.id,
            payload=payload,
            accessible_collection_ids=accessible_collection_ids,
            create_event=False,
        )

    move_book_to_destination(session, book=book, destination="prod")
