from typing import Any, Callable, Generator
from unittest.mock import Mock

import pytest
from discord import Message
from pytest_mock import MockerFixture
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from hyacinth import plugin
from hyacinth.db.models import Base
from hyacinth.models import Location
from hyacinth.plugin import register_plugin
from hyacinth.settings import get_settings
from hyacinth.util import geo

sqlite_engine = create_engine(
    "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
)


@pytest.fixture
def test_db_session(mocker: MockerFixture) -> Generator[sessionmaker[Session], None, None]:
    """
    Test fixture for replacing the postgres session with a clean SQLite session.
    DB is cleared after use.
    """
    sm = sessionmaker(sqlite_engine)
    mocker.patch("hyacinth.db.session.Session", sm)

    Base.metadata.create_all(sqlite_engine)
    yield sm
    Base.metadata.drop_all(sqlite_engine)


def make_message(content: str = "") -> Mock:
    message_mock = Mock(spec=Message)
    message_mock.content = content
    message_mock.channel.id = 0
    return message_mock


@pytest.fixture(params=["google", "local"])
def reverse_geocode_function(request: Any) -> Callable[[tuple[float, float]], Location]:
    if request.param == "google":
        return geo._reverse_geotag_google
    return geo._reverse_geotag_local


@pytest.fixture()
def load_plugins() -> Generator[None, None, None]:
    settings = get_settings()
    # load plugins
    for plugin_path in settings.plugins:
        register_plugin(plugin_path)

    yield

    # unload plugins
    plugin._plugins.clear()
    plugin._plugin_path_dict.clear()


@pytest.fixture()
def mock_schedulers(mocker: MockerFixture) -> None:
    """
    Mocks the schedulers so that they don't run.
    """
    mocker.patch("hyacinth.scheduler.get_async_scheduler")
    mocker.patch("hyacinth.scheduler.get_threadpool_scheduler")
