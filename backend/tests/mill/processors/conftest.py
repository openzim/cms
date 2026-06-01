from collections.abc import Callable

import pytest

from cms_backend.db.models import Account


@pytest.fixture(autouse=True)
def maint_scripts_account(create_account: Callable[..., Account]):
    create_account(username="maint-scripts")
