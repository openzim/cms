from collections.abc import Callable

import pytest

from cms_backend.context import Context
from cms_backend.db.models import Account


@pytest.fixture(autouse=True)
def zimfarm_account(create_account: Callable[..., Account]):
    create_account(username=Context.mill_account_username)
