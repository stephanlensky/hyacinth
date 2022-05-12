from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from notifier_bot.db.models import DbDiscordNotifier
from notifier_bot.db.session import Session

if TYPE_CHECKING:
    from notifier_bot.monitor import MarketplaceMonitor
    from notifier_bot.notifier import DiscordNotifier

_logger = logging.getLogger(__name__)


def save_discord_notifier(notifier: DiscordNotifier) -> None:
    with Session() as session:
        session.query(DbDiscordNotifier).filter(
            DbDiscordNotifier.channel_id == str(notifier.channel.id)
        ).delete()
        session.add(DbDiscordNotifier.from_notifier(notifier))
        session.commit()


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
            print(db_notifier)
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
