from typing import Any, Callable
from unittest.mock import Mock

import pytest
from discord import Message

from notifier_bot.models import Location
from notifier_bot.util import geo


def make_message(content: str = "") -> Mock:
    message_mock = Mock(spec=Message)
    message_mock.content = content
    message_mock.channel.id = 0
    return message_mock


@pytest.fixture(params=["google", "local"])
def reverse_geocode_function(request: Any) -> Callable[[tuple[float, float]], Location]:
    if request.param == "google":
        return geo._reverse_geotag_google  # pylint: disable=protected-access
    return geo._reverse_geotag_local  # pylint: disable=protected-access
