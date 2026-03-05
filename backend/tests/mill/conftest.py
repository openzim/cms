from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_redis_consumer():
    """Mock RedisConsumer for testing without Redis connection."""
    mock = MagicMock()
    mock.read_events = MagicMock(return_value=[])
    mock.acknowledge_event = MagicMock()
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing without Redis connection."""
    mock = MagicMock()
    mock.ping = MagicMock(return_value=True)
    mock.xadd = MagicMock(return_value="1234-0")
    mock.xreadgroup = MagicMock(return_value=[])
    mock.xack = MagicMock(return_value=1)
    mock.xgroup_create = MagicMock()
    mock.close = MagicMock()
    return mock
