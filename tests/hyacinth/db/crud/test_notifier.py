from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from hyacinth.db.crud.notifier import get_channel_notifiers, save_notifier_state
from hyacinth.db.models import ChannelNotifierState
from hyacinth.notifier import ChannelNotifier
from tests.sample_data import make_channel_notifier_state

SOME_CHANNEL_ID = 123
SOME_OTHER_CHANNEL_ID = 456


def test_save_notifier_state__state_exists__deletes_old_state_and_saves_new(
    test_db_session: sessionmaker[Session], mock_schedulers: None, mocker: MockerFixture
) -> None:
    some_config = ChannelNotifier.Config(
        notification_frequency_seconds=123, paused=False, active_searches=[]
    )
    some_channel_notifier = ChannelNotifier(
        mocker.Mock(id=SOME_CHANNEL_ID), mocker.Mock(), some_config
    )

    some_existing_channel_notifier_state = make_channel_notifier_state(
        channel_id=SOME_CHANNEL_ID, notification_frequency_seconds=456
    )
    some_other_channel_notifier_state = make_channel_notifier_state(
        channel_id=SOME_OTHER_CHANNEL_ID,
    )

    with test_db_session() as session:
        session.add_all([some_existing_channel_notifier_state, some_other_channel_notifier_state])
        session.commit()

        save_notifier_state(session, some_channel_notifier)

        saved_states = session.execute(select(ChannelNotifierState)).scalars().all()
        assert len(saved_states) == 2
        assert saved_states[0].channel_id == str(SOME_OTHER_CHANNEL_ID)
        assert saved_states[1].channel_id == str(SOME_CHANNEL_ID)
        assert saved_states[1].notification_frequency_seconds == 123


def test_save_notifier_state__state_does_not_exist__saves_new_state(
    test_db_session: sessionmaker[Session], mock_schedulers: None, mocker: MockerFixture
) -> None:
    some_config = ChannelNotifier.Config(
        notification_frequency_seconds=123, paused=False, active_searches=[]
    )
    some_channel_notifier = ChannelNotifier(
        mocker.Mock(id=SOME_CHANNEL_ID), mocker.Mock(), some_config
    )

    with test_db_session() as session:
        save_notifier_state(session, some_channel_notifier)

        assert session.execute(select(ChannelNotifierState)).scalars().one().channel_id == str(
            SOME_CHANNEL_ID
        )


def test_get_channel_notifiers__some_channels_do_not_exist__deletes_notifiers_with_stale_channels(
    test_db_session: sessionmaker[Session], mock_schedulers: None, mocker: MockerFixture
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
