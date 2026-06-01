from collections.abc import Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession
from werkzeug.security import generate_password_hash

from cms_backend.api.token import generate_access_token
from cms_backend.context import Context
from cms_backend.db import Session
from cms_backend.db.models import (
    Account,
    Base,
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Event,
    Title,
    Warehouse,
    ZimfarmNotification,
)
from cms_backend.roles import RoleEnum
from cms_backend.utils.datetime import getnow


@pytest.fixture
def dbsession() -> Generator[OrmSession]:
    session = Session()
    # Ensure we are starting with an empty database
    engine = session.get_bind()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def faker(faker: Faker) -> Faker:
    """Sets up faker to generate random data for testing."""
    # Setting a fixed seed ensures that Faker generates the same fake data
    # on every test run. This makes tests deterministic and reproducible,
    # so failures are easier to debug and tests are more reliable.
    # Other test submodules can choose a new seed value.
    faker.seed_instance("cms_tests_init")

    return faker


@pytest.fixture
def create_zimfarm_notification(
    dbsession: OrmSession,
) -> Callable[..., ZimfarmNotification]:
    def _create_zimfarm_notification(
        _id: UUID | None = None,
        received_at: datetime | None = None,
        content: dict[str, Any] | None = None,
        events: list[str] | None = None,
    ) -> ZimfarmNotification:
        zimfarm_notification = ZimfarmNotification(
            id=_id if _id is not None else uuid4(),
            received_at=received_at if received_at is not None else getnow(),
            content=content if content is not None else {"key": "value"},
        )
        zimfarm_notification.events = events if events is not None else []
        dbsession.add(zimfarm_notification)
        dbsession.flush()
        return zimfarm_notification

    return _create_zimfarm_notification


@pytest.fixture
def zimfarm_notification(
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
) -> ZimfarmNotification:
    return create_zimfarm_notification()


@pytest.fixture
def create_book(
    dbsession: OrmSession,
    faker: Faker,
) -> Callable[..., Book]:
    def _create_book(
        _id: UUID | None = None,
        created_at: datetime | None = None,
        article_count: int | None = None,
        media_count: int | None = None,
        size: int | None = None,
        zim_metadata: dict[str, Any] | None = None,
        zimcheck_result_url: str | None = None,
        name: str | None = None,
        date: str | None = None,
        flavour: str | None = None,
        zimfarm_notification: ZimfarmNotification | None = None,
        location_kind: str = "quarantine",
        updated_at: datetime | None = None,
    ) -> Book:
        if zim_metadata is None:
            zim_metadata = {}

        # Extract name from zim_metadata if not explicitly provided
        if name is None:
            name = zim_metadata.get("Name")

        # Extract date from zim_metadata if not explicitly provided
        if date is None:
            date = zim_metadata.get("Date")

        # Extract flavour from zim_metadata if not explicitly provided
        if flavour is None:
            flavour = zim_metadata.get("Flavour")

        book = Book(
            id=_id if _id is not None else uuid4(),
            created_at=created_at if created_at is not None else getnow(),
            article_count=(
                article_count if article_count is not None else faker.random_int()
            ),
            media_count=media_count if media_count is not None else faker.random_int(),
            size=size if size is not None else faker.random_int(),
            zim_metadata=zim_metadata,
            zimcheck_result_url=zimcheck_result_url,
            name=name,
            date=date,
            flavour=flavour,
            zimfarm_notification=zimfarm_notification,
        )
        book.location_kind = location_kind
        if updated_at:
            book.updated_at = updated_at
        dbsession.add(book)
        dbsession.flush()
        return book

    return _create_book


@pytest.fixture
def book(
    create_book: Callable[..., Book],
) -> Book:
    return create_book()


@pytest.fixture
def create_title(
    dbsession: OrmSession,
) -> Callable[..., Title]:
    def _create_title(
        *,
        name: str = "test_en_all",
        archived: bool = False,
        title: str | None = None,
        creator: str | None = None,
        publisher: str | None = None,
        description: str | None = None,
        language: str | None = None,
        illustration_48x48_at_1: str | None = None,
        long_description: str | None = None,
        license: str | None = None,  # noqa: A002
        relation: str | None = None,
        source: str | None = None,
        flavours: list[str] | None = None,
    ) -> Title:
        db_title = Title(
            name=name,
            title=title,
            archived=archived,
            creator=creator,
            publisher=publisher,
            description=description,
            language=language,
            illustration_48x48_at_1=illustration_48x48_at_1,
            long_description=long_description,
            license=license,
            relation=relation,
            source=source,
            flavours=flavours if flavours is not None else [],
        )
        dbsession.add(db_title)
        dbsession.flush()
        return db_title

    return _create_title


@pytest.fixture()
def title(
    create_title: Callable[..., Title],
) -> Title:
    return create_title()


@pytest.fixture
def create_warehouse(
    dbsession: OrmSession,
    faker: Faker,
) -> Callable[..., Warehouse]:
    def _create_warehouse(
        name: str | None = None,
        warehouse_id: UUID | None = None,
    ) -> Warehouse:
        warehouse = Warehouse(
            name=name if name is not None else faker.company(),
        )
        if warehouse_id:
            warehouse.id = warehouse_id
        dbsession.add(warehouse)
        dbsession.flush()
        return warehouse

    return _create_warehouse


@pytest.fixture
def warehouse(
    create_warehouse: Callable[..., Warehouse],
) -> Warehouse:
    return create_warehouse(warehouse_id=Context.staging_warehouse_id)


@pytest.fixture
def create_book_location(
    dbsession: OrmSession,
    faker: Faker,
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
) -> Callable[..., BookLocation]:
    def _create_book_location(
        book: Book | None = None,
        warehouse_id: UUID | None = None,
        path: str | Path | None = None,
        filename: str | None = None,
        status: str = "current",
    ) -> BookLocation:
        if book is None:
            book = create_book()

        if warehouse_id is None:
            warehouse = create_warehouse()
            warehouse_id = warehouse.id

        if path is None:
            path = Path(faker.file_path())
        else:
            # Convert string paths to Path objects
            path = Path(path) if isinstance(path, str) else path

        if filename is None:
            filename = "test_file.zim"

        location = BookLocation(
            book_id=book.id,
            warehouse_id=warehouse_id,
            path=path,
            status=status,
            filename=filename,
        )
        dbsession.add(location)
        dbsession.flush()
        return location

    return _create_book_location


@pytest.fixture
def book_location(
    create_book_location: Callable[..., BookLocation],
) -> BookLocation:
    return create_book_location()


@pytest.fixture
def create_collection(
    dbsession: OrmSession,
    faker: Faker,
    create_warehouse: Callable[..., Warehouse],
) -> Callable[..., Collection]:
    def _create_collection(
        name: str | None = None,
        warehouse: Warehouse | None = None,
        download_base_url: str = "https://download.kiwix.org/zim/",
        view_base_url: str = "https://browse.library.kiwix.org/viewer#",
        title_ids_with_paths: list[tuple[UUID, str]] | None = None,
    ) -> Collection:
        if warehouse is None:
            warehouse = create_warehouse()

        collection = Collection(
            name=name if name is not None else faker.slug(),
            warehouse_id=warehouse.id,
            download_base_url=download_base_url,
            view_base_url=view_base_url,
        )

        # Add title associations if provided
        if title_ids_with_paths:
            for title_id, path in title_ids_with_paths:
                ct = CollectionTitle(path=Path(path))
                ct.title_id = title_id
                collection.titles.append(ct)

        dbsession.add(collection)
        dbsession.flush()
        return collection

    return _create_collection


@pytest.fixture
def collection(
    create_collection: Callable[..., Collection],
) -> Collection:
    return create_collection()


@pytest.fixture
def create_collection_title(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
) -> Callable[..., CollectionTitle]:
    def _create_collection_title(
        title: Title | None = None,
        collection: Collection | None = None,
        path: str | Path = "/test/path",
    ) -> CollectionTitle:
        if title is None:
            title = create_title()

        if collection is None:
            collection = create_collection()

        collection_title = CollectionTitle(
            path=Path(path) if isinstance(path, str) else path
        )
        collection_title.title_id = title.id
        collection_title.collection_id = collection.id

        dbsession.add(collection_title)
        dbsession.flush()
        return collection_title

    return _create_collection_title


@pytest.fixture
def create_account(
    dbsession: OrmSession,
    faker: Faker,
) -> Callable[..., Account]:
    def _create_account(
        *,
        username: str | None = None,
        permission: RoleEnum = RoleEnum.EDITOR,
        password: str | None = None,
    ):
        username = username or faker.first_name()
        account = Account(
            role=permission,
            username=username,
            display_name=username,
            idp_sub=uuid4(),
            password_hash=(
                None if password is None else generate_password_hash(password)
            ),
        )
        dbsession.add(account)
        dbsession.flush()

        return account

    return _create_account


@pytest.fixture
def account(create_account: Callable[..., Account]):
    return create_account()


@pytest.fixture
def access_token(account: Account) -> str:
    return generate_access_token(
        issue_time=getnow(),
        account_id=str(account.id),
    )


@pytest.fixture
def create_event(
    dbsession: OrmSession,
    faker: Faker,
) -> Callable[..., Event]:
    def _create_event(
        *,
        topic: str | None = None,
        created_at: datetime | None = None,
    ):
        event = Event(
            topic=topic or faker.slug(),
            payload={},
            created_at=created_at or faker.date_time(),
        )
        dbsession.add(event)
        dbsession.flush()

        return event

    return _create_event


@pytest.fixture()
def illustration_48x48_at_1():
    return """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"""  # noqa: E501
