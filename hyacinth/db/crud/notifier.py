from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from sqlalchemy import delete
from sqlalchemy.orm import Session

from hyacinth.db.models import ChannelNotifierState

if TYPE_CHECKING:
    from hyacinth.monitor import MarketplaceMonitor
    from hyacinth.notifier import ChannelNotifier, ListingNotifier

_logger = logging.getLogger(__name__)


def add_notifier_state(session: Session, notifier: ListingNotifier) -> ChannelNotifierState:
    from hyacinth.notifier import ChannelNotifier

    if not isinstance(notifier, ChannelNotifier):
        raise NotImplementedError(f"{type(notifier)} not implemented")

    _logger.debug("Creating new notifier state")
    notifier_state = ChannelNotifierState(
        channel_id=str(notifier.channel.id),
        notification_frequency_seconds=notifier.config.notification_frequency_seconds,
        paused=notifier.config.paused,
        active_searches=list(notifier.config.active_searches),
        filters=list(notifier.config.filters),
    )
    session.add(notifier_state)
    return notifier_state


def save_notifier_state(session: Session, notifier: ListingNotifier) -> None:
    from hyacinth.notifier import ChannelNotifier

    if not isinstance(notifier, ChannelNotifier):
        raise NotImplementedError(f"{type(notifier)} not implemented")
    if notifier.config.id is None:
        raise ValueError("Cannot save notifier state with no ID")

    _logger.debug(f"Saving notifier state for channel {notifier.channel.id}")
    notifier_state = (
        session.query(ChannelNotifierState)
        .filter(ChannelNotifierState.id == notifier.config.id)
        .one()
    )

    notifier_state.paused = notifier.config.paused


def get_channel_notifiers(
    session: Session, client: discord.Client, monitor: MarketplaceMonitor
) -> list[ChannelNotifier]:
    """
    Get all saved ChannelNotifiers from the database.

    If a stale notifier is encountered (for a channel that no longer exists), it is automatically
    deleted from the database.
    """
    from hyacinth.notifier import ChannelNotifier

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
                id=notifier_state.id,
                notification_frequency_seconds=notifier_state.notification_frequency_seconds,
                paused=notifier_state.paused,
                active_searches=list(notifier_state.active_searches),
                filters=list(notifier_state.filters),
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
