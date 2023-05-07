from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from pydantic import parse_raw_as
from sqlalchemy import delete
from sqlalchemy.orm import Session

from hyacinth.db.models import ChannelNotifierState, NotifierSearch
from hyacinth.filters import Filter

if TYPE_CHECKING:
    from hyacinth.monitor import MarketplaceMonitor
    from hyacinth.notifier import ChannelNotifier, ListingNotifier

_logger = logging.getLogger(__name__)


def save_notifier_state(session: Session, notifier: ListingNotifier) -> None:
    from hyacinth.notifier import ChannelNotifier

    if isinstance(notifier, ChannelNotifier):
        stmt = delete(ChannelNotifierState).where(
            ChannelNotifierState.channel_id == str(notifier.channel.id)
        )
        session.execute(stmt)
        session.add(
            ChannelNotifierState(
                channel_id=str(notifier.channel.id),
                notification_frequency_seconds=notifier.config.notification_frequency_seconds,
                paused=notifier.config.paused,
                active_searches=[
                    NotifierSearch(
                        last_notified=search.last_notified, search_spec_id=search.search_spec.id
                    )
                    for search in notifier.config.active_searches
                ],
            )
        )

    else:
        raise NotImplementedError(f"{type(notifier)} not implemented")


def get_channel_notifiers(
    session: Session, client: discord.Client, monitor: MarketplaceMonitor
) -> list[ChannelNotifier]:
    """
    Get all saved ChannelNotifiers from the database.

    If a stale notifier is encountered (for a channel that no longer exists), it is automatically
    deleted from the database.
    """
    from hyacinth.notifier import ActiveSearch, ChannelNotifier

    saved_states: list[ChannelNotifierState] = session.query(ChannelNotifierState).all()

    notifiers: list[ChannelNotifier] = []
    stale_notifier_channel_ids: list[str] = []
    for notifier_state in saved_states:
        notifier_channel = client.get_channel(int(notifier_state.channel_id))

        # If the channel no longer exists, delete the notifier from the database.
        if notifier_channel is None:
            _logger.info(f"Found stale notifier for channel {notifier_state.channel_id}! Deleting.")
            stale_notifier_channel_ids.append(notifier_state.channel_id)
            continue

        # Otherwise, create a new ChannelNotifier from the saved state.
        notifier = ChannelNotifier(
            # assume saved channel type is messageable
            notifier_channel,  # type: ignore[arg-type]
            monitor,
            ChannelNotifier.Config(
                notification_frequency_seconds=notifier_state.notification_frequency_seconds,
                paused=notifier_state.paused,
                active_searches=[
                    ActiveSearch(
                        search_spec=search.search_spec,
                        last_notified=search.last_notified,
                    )
                    for search in notifier_state.active_searches
                ],
                filters=parse_raw_as(dict[str, Filter], notifier_state.filters_json),
            ),
        )
        notifiers.append(notifier)

    if stale_notifier_channel_ids:
        _logger.info(
            f"Deleting {len(stale_notifier_channel_ids)} stale notifiers from the database."
        )
        stmt = delete(ChannelNotifierState).where(
            ChannelNotifierState.channel_id.in_(stale_notifier_channel_ids)
        )
        session.execute(stmt)
        session.commit()

    return notifiers


def delete_channel_notifiers(session: Session, channel_id: int) -> None:
    stmt = delete(ChannelNotifierState).where(ChannelNotifierState.channel_id == str(channel_id))
    session.execute(stmt)
