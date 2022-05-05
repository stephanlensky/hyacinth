from unittest.mock import Mock

from discord import Message


def make_message(content: str = "") -> Mock:
    message_mock = Mock(spec=Message)
    message_mock.content = content
    message_mock.channel.id = 0
    return message_mock
