# ruff: noqa: E501
from collections.abc import Callable, Generator
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import Session
from cms_backend.db.models import (
    Base,
    Book,
    Title,
    TitleWarehousePath,
    Warehouse,
    WarehousePath,
    ZimfarmNotification,
)
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
        producer_display_name: str | None = None,
        producer_display_url: str | None = None,
        producer_unique_id: str | None = None,
    ) -> Book:
        book = Book(
            id=_id if _id is not None else uuid4(),
            created_at=created_at if created_at is not None else getnow(),
            article_count=(
                article_count if article_count is not None else faker.random_int()
            ),
            media_count=media_count if media_count is not None else faker.random_int(),
            size=size if size is not None else faker.random_int(),
            zim_metadata=zim_metadata if zim_metadata else {},
            zimcheck_result=zimcheck_result if zimcheck_result else {},
            name=name,
            date=date,
            flavour=flavour,
            zimfarm_notification=zimfarm_notification,
            producer_display_name=(
                producer_display_name
                if producer_display_name is not None
                else faker.company()
            ),
            producer_display_url=(
                producer_display_url
                if producer_display_url is not None
                else faker.url()
            ),
            producer_unique_id=(
                producer_unique_id
                if producer_unique_id is not None
                else str(faker.uuid4())
            ),
        )
        # book.events = []
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
    faker: Faker,
    create_warehouse_path: Callable[..., WarehousePath],
) -> Callable[..., Title]:
    def _create_title(
        name: str = "test_en_all",
        producer_unique_id: str | None = None,
        producer_display_name: str | None = None,
        producer_display_url: str | None = None,
        dev_warehouse_path_ids: list[UUID] | None = None,
        prod_warehouse_path_ids: list[UUID] | None = None,
    ) -> Title:
        title = Title(
            name=name,
            producer_unique_id=(
                producer_unique_id
                if producer_unique_id is not None
                else str(faker.uuid4())
            ),
        )
        title.producer_display_name = producer_display_name
        title.producer_display_url = producer_display_url

        # Create default warehouse paths if not provided
        if dev_warehouse_path_ids is None:
            dev_warehouse_path = create_warehouse_path()
            dev_warehouse_path_ids = [dev_warehouse_path.id]
        if prod_warehouse_path_ids is None:
            prod_warehouse_path = create_warehouse_path()
            prod_warehouse_path_ids = [prod_warehouse_path.id]

        # Add warehouse path associations
        for path_id in dev_warehouse_path_ids:
            twp = TitleWarehousePath(path_type="dev")
            twp.warehouse_path_id = path_id
            title.warehouse_paths.append(twp)
        for path_id in prod_warehouse_path_ids:
            twp = TitleWarehousePath(path_type="prod")
            twp.warehouse_path_id = path_id
            title.warehouse_paths.append(twp)

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
        configuration: dict[str, Any] | None = None,
    ) -> Warehouse:
        warehouse = Warehouse(
            name=name if name is not None else faker.company(),
            configuration=configuration if configuration is not None else {},
        )
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
def create_warehouse_path(
    dbsession: OrmSession,
    faker: Faker,
    create_warehouse: Callable[..., Warehouse],
) -> Callable[..., WarehousePath]:
    def _create_warehouse_path(
        folder_name: str | None = None,
        warehouse: Warehouse | None = None,
    ) -> WarehousePath:
        warehouse_path = WarehousePath(
            folder_name=folder_name if folder_name is not None else faker.file_path(),
        )
        warehouse_path.warehouse = (
            warehouse if warehouse is not None else create_warehouse()
        )
        dbsession.add(warehouse_path)
        dbsession.flush()
        return warehouse_path

    return _create_warehouse_path


@pytest.fixture
def warehouse_path(
    create_warehouse_path: Callable[..., WarehousePath],
    warehouse: Warehouse,
) -> WarehousePath:
    return create_warehouse_path(warehouse=warehouse)
