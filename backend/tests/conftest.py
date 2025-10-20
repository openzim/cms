# ruff: noqa: E501
from collections.abc import Callable, Generator
from uuid import uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import Session
from cms_backend.db.models import Base, ZimfarmNotification
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
    def _create_zimfarm_notification() -> ZimfarmNotification:
        zimfarm_notification = ZimfarmNotification(
            id=uuid4(), received_at=getnow(), content=""
        )
        dbsession.add(zimfarm_notification)
        dbsession.flush()
        return zimfarm_notification

    return _create_zimfarm_notification


@pytest.fixture
def zimfarm_notification(
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
) -> ZimfarmNotification:
    return create_zimfarm_notification()
