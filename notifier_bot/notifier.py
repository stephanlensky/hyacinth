from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from apscheduler.triggers.interval import IntervalTrigger
from pydantic import BaseModel

from notifier_bot.models import Listing, ListingFieldFilter, SearchSpec
from notifier_bot.monitor import MarketplaceMonitor
from notifier_bot.scheduler import get_scheduler
from notifier_bot.settings import get_settings

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

settings = get_settings()
_logger = logging.getLogger(__name__)


class ListingNotifier(ABC):
    class Config(BaseModel):
        notification_frequency_seconds: int = settings.notification_frequency_seconds
        paused: bool = False
        active_searches: list[SearchSpec] = []
        last_notified: dict[SearchSpec, datetime] = {}
        filters: dict[str, ListingFieldFilter] = {}

    def __init__(self, monitor: MarketplaceMonitor, config: ListingNotifier.Config) -> None:
        self.monitor = monitor
        self.config = config

        self.scheduler = get_scheduler()
        self.notify_job = self.scheduler.add_job(
            self._notify_new_listings,
            IntervalTrigger(seconds=self.config.notification_frequency_seconds),
            next_run_time=datetime.now(),
        )
        if self.config.paused:
            self.scheduler.pause_job(self.notify_job.id)

    def create_search(self, search_spec: SearchSpec, last_notified: datetime | None = None) -> None:
        self.monitor.register_search(search_spec)
        self.config.active_searches.append(search_spec)

        if last_notified is None:
            last_notified = datetime.now() - timedelta(hours=settings.notifier_backdate_time_hours)
        self.config.last_notified[search_spec] = last_notified

    def pause(self) -> None:
        self.config.paused = True
        self.scheduler.pause_job(self.notify_job.id)

    def unpause(self) -> None:
        self.config.paused = False
        self.scheduler.resume_job(self.notify_job.id)

    async def _get_new_listings_for_search(self, search: SearchSpec) -> list[Listing]:
        """
        Get new listings for a given search.

        Updates the last_notified time for this search, so repeated calls will return only listings
        that have not been seen before.
        """
        new_listings = await self.monitor.get_listings(
            search, after_time=self.config.last_notified[search]
        )
        if new_listings:
            self.config.last_notified[search] = new_listings[0].created_at
            _logger.debug(f"Most recent listing was found at {self.config.last_notified[search]}")

        return new_listings

    async def _get_new_listings(self) -> list[Listing]:
        """
        Collect all new listings from all active searches
        """
        listings: list[Listing] = []
        for search in self.config.active_searches:
            listings.extend(await self._get_new_listings_for_search(search))

        _logger.debug(
            f"Found {len(listings)} to notify for across {len(self.config.active_searches)} active"
            " searches"
        )
        listings.sort(key=lambda l: l.updated_at)
        return listings

    async def _notify_new_listings(self) -> None:
        not_yet_notified_listings: list[Listing] = []
        try:
            listings = await self._get_new_listings()
            not_yet_notified_listings = listings.copy()
            for listing in listings:
                await self.notify(listing)
                not_yet_notified_listings.remove(listing)
        except asyncio.CancelledError:
            # ensure users are notified of all listings even if the task is cancelled partway
            # through notification loop
            if not_yet_notified_listings:
                _logger.debug(
                    "Listing notification process interrupted! Notifying"
                    f" {len(not_yet_notified_listings)} listings before cancelling."
                )
            for listing in not_yet_notified_listings:
                await self.notify(listing)
            raise

    @abstractmethod
    async def notify(self, listing: Listing) -> None:
        pass


class LoggerNotifier(ListingNotifier):
    async def notify(self, listing: Listing) -> None:
        _logger.info(f"Notify listing {listing}")


class DiscordNotifier(ListingNotifier):
    def __init__(
        self,
        channel: MessageableChannel,
        monitor: MarketplaceMonitor,
        config: ListingNotifier.Config,
    ) -> None:
        super().__init__(monitor, config)
        self.channel = channel

    async def notify(self, listing: Listing) -> None:
        match (listing.location.city, listing.location.state):
            case (None, None):
                location_part = ""
            case (city, None):
                location_part = f" - {city}"
            case (None, state):
                location_part = f" - {state}"
            case (city, state):
                location_part = f" - {city}, {state}"
        description = (
            f"**${int(listing.price)}{location_part} ({int(listing.distance_miles)} mi."
            f" away)**\n\n{listing.body}"
        )

        embed = discord.Embed(
            title=listing.title,
            url=listing.url,
            description=description[:2048],
            timestamp=listing.updated_at.astimezone(timezone.utc),
        )
        await self.channel.send(embed=embed)
