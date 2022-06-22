from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from hyacinth.db.models import DbDiscordNotifier
from hyacinth.db.session import Session

if TYPE_CHECKING:
    from hyacinth.monitor import MarketplaceMonitor
    from hyacinth.notifier import DiscordNotifier, ListingNotifier

_logger = logging.getLogger(__name__)


def save_notifier(notifier: ListingNotifier) -> None:
    # avoid circular import
    from hyacinth.notifier import DiscordNotifier  # pylint: disable=import-outside-toplevel

    if isinstance(notifier, DiscordNotifier):
        with Session() as session:
            session.query(DbDiscordNotifier).filter(
                DbDiscordNotifier.channel_id == str(notifier.channel.id)
            ).delete()
            session.add(DbDiscordNotifier.from_notifier(notifier))
            session.commit()
    else:
        raise NotImplementedError(f"{type(notifier)} not implemented")


def get_discord_notifiers(
    client: discord.Client, monitor: MarketplaceMonitor
) -> list[DiscordNotifier]:
    """
    Get all saved DiscordNotifiers from the database.

    If a stale notifier is encountered (for a channel that no longer exists), it is automatically
    deleted from the database.
    """
    with Session() as session:
        db_notifiers: list[DbDiscordNotifier] = session.query(DbDiscordNotifier).all()

        notifiers: list[DiscordNotifier] = []
        stale_notifier_channel_ids: list = []
        for db_notifier in db_notifiers:
            notifier = db_notifier.to_notifier(client, monitor)
            if notifier is not None:
                notifiers.append(notifier)
            else:
                _logger.info(
                    f"Found stale notifier for channel {db_notifier.channel_id}! Deleting."
                )
                stale_notifier_channel_ids.append(db_notifier.channel_id)

        session.query(DbDiscordNotifier).filter(
            DbDiscordNotifier.channel_id.in_(stale_notifier_channel_ids)
        ).delete()
        session.commit()

    return notifiers


def delete_all_discord_notifiers_from_channel(channel_id: int) -> int:
    with Session() as session:
        count = (
            session.query(DbDiscordNotifier)
            .filter(DbDiscordNotifier.channel_id == str(channel_id))
            .count()
        )
        session.query(DbDiscordNotifier).filter(
            DbDiscordNotifier.channel_id == str(channel_id)
        ).delete()
        session.commit()

    return count
