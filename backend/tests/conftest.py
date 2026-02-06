# ruff: noqa: E501
from collections.abc import Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import JWTClaims
from cms_backend.db import Session
from cms_backend.db.models import (
    Base,
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    User,
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
        zimcheck_result: dict[str, Any] | None = None,
        name: str | None = None,
        date: str | None = None,
        flavour: str | None = None,
        zimfarm_notification: ZimfarmNotification | None = None,
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
            zimcheck_result=zimcheck_result if zimcheck_result else {},
            name=name,
            date=date,
            flavour=flavour,
            zimfarm_notification=zimfarm_notification,
        )
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
    ) -> Title:
        title = Title(
            name=name,
        )
        dbsession.add(title)
        dbsession.flush()
        return title

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
    return create_warehouse()


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
        title_ids_with_paths: list[tuple[UUID, str]] | None = None,
    ) -> Collection:
        if warehouse is None:
            warehouse = create_warehouse()

        collection = Collection(
            name=name if name is not None else faker.slug(),
            warehouse_id=warehouse.id,
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
def create_user(
    dbsession: OrmSession,
    faker: Faker,
) -> Callable[..., User]:
    def _create_user(
        *,
        username: str | None = None,
        permission: RoleEnum = RoleEnum.EDITOR,
    ):
        user = User(
            username=username or faker.first_name(),
            role=permission,
            idp_sub=uuid4(),
        )
        dbsession.add(user)

        dbsession.flush()

        return user

    return _create_user


@pytest.fixture
def user(create_user: Callable[..., User]):
    return create_user()


@pytest.fixture
def mock_token_for_user(monkeypatch: pytest.MonkeyPatch) -> Callable[[User], None]:
    def _mock_for_user(user: User) -> None:
        def mock_decode(_: str) -> JWTClaims:
            return JWTClaims(
                iss="https://test.kiwix.org",
                subject=user.idp_sub,
                name=user.username,
                iat=getnow(),
                exp=getnow(),
            )

        monkeypatch.setattr(
            "cms_backend.api.routes.dependencies.token_decoder.decode", mock_decode
        )

    return _mock_for_user
