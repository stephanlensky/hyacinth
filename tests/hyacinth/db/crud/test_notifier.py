from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from hyacinth.db.crud.notifier import get_channel_notifiers
from hyacinth.db.models import ChannelNotifierState
from tests.sample_data import make_channel_notifier_state

SOME_CHANNEL_ID = 123
SOME_OTHER_CHANNEL_ID = 456


def test_get_channel_notifiers__some_channels_do_not_exist__deletes_notifiers_with_stale_channels(
    test_db_session: sessionmaker[Session], mock_notifier_scheduler: None, mocker: MockerFixture
) -> None:
    mock_client = mocker.Mock(
        get_channel=lambda channel_id: mocker.Mock(id=SOME_CHANNEL_ID)
        if channel_id == SOME_CHANNEL_ID
        else None
    )
    some_saved_states = [
        make_channel_notifier_state(channel_id=SOME_CHANNEL_ID),
        make_channel_notifier_state(channel_id=SOME_OTHER_CHANNEL_ID),
    ]

    with test_db_session() as session:
        session.add_all(some_saved_states)
        session.commit()

        notifiers = get_channel_notifiers(session, mock_client, mocker.Mock())

        assert len(notifiers) == 1
        assert notifiers[0].channel.id == SOME_CHANNEL_ID

        assert session.execute(select(ChannelNotifierState)).scalars().one().channel_id == str(
            SOME_CHANNEL_ID
        )
