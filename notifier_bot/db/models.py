from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import declarative_base

from notifier_bot.models import Listing, SearchSpec

if TYPE_CHECKING:
    from notifier_bot.monitor import MarketplaceMonitor
    from notifier_bot.notifier import DiscordNotifier

Base = declarative_base()


class DbListing(Base):
    __tablename__ = "listing"

    id = Column(Integer, primary_key=True)
    created_at = Column(Integer, index=True, nullable=False)
    search_spec_json = Column(Text, nullable=False)
    listing_json = Column(Text, nullable=False)

    def to_listing(self) -> Listing:
        return Listing.parse_raw(self.listing_json)  # type: ignore

    @classmethod
    def from_listing(cls, search_spec: SearchSpec, listing: Listing) -> DbListing:
        return cls(
            created_at=int(listing.created_at.timestamp()),
            search_spec_json=search_spec.json(),
            listing_json=listing.json(),
        )


class DbDiscordNotifier(Base):
    __tablename__ = "notifier"

    channel_id = Column(Text, primary_key=True)
    config_json = Column(Text, nullable=False)

    def to_notifier(
        self, client: discord.Client, monitor: MarketplaceMonitor
    ) -> DiscordNotifier | None:
        """
        Create a DiscordNotifier this database model.

        If the channel referenced by the saved notifier no longer exists, return None.
        """
        # avoid circular import
        from notifier_bot.notifier import DiscordNotifier  # pylint: disable=import-outside-toplevel

        channel = client.get_channel(int(self.channel_id))  # type: ignore
        if channel is None:
            return None
        return DiscordNotifier(
            channel=channel,  # type: ignore
            monitor=monitor,
            config=DiscordNotifier.Config.parse_raw(self.config_json),  # type: ignore
        )

    @classmethod
    def from_notifier(cls, notifier: DiscordNotifier) -> DbDiscordNotifier:
        return cls(
            channel_id=str(notifier.channel.id),
            config_json=notifier.config.json(),
        )
