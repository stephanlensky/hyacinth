import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.triggers.interval import IntervalTrigger

from notifier_bot.models import Listing, SearchSpec
from notifier_bot.monitor import MarketplaceMonitor
from notifier_bot.scheduler import get_scheduler

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

_logger = logging.getLogger(__name__)


class ListingNotifier(ABC):
    def __init__(
        self,
        monitor: MarketplaceMonitor,
        notification_frequency: timedelta = timedelta(minutes=10),
        paused: bool = False,
        last_notified: datetime | None = None,
    ) -> None:
        self.monitor = monitor
        self.notification_frequency: timedelta = notification_frequency

        self.scheduler = get_scheduler()

        if last_notified is None:
            self.last_notified = datetime.now()
        self.paused = paused
        self.active_searches: list[SearchSpec] = []

        self.notify_job = self.scheduler.add_job(
            self._notify_new_listings, IntervalTrigger(seconds=self.notification_frequency.seconds)
        )
        if self.paused:
            self.scheduler.pause_job(self.notify_job.id)

    def create_search(self, search_spec: SearchSpec) -> None:
        self.monitor.register_search(search_spec)
        self.active_searches.append(search_spec)

    def pause(self) -> None:
        self.paused = True
        self.scheduler.pause_job(self.notify_job.id)

    def unpause(self) -> None:
        self.paused = False
        self.scheduler.resume_job(self.notify_job.id)

    async def _notify_new_listings(self) -> None:
        not_yet_notified_listings: list[Listing] = []
        try:
            listings: list[Listing] = []
            for search in self.active_searches:
                listings.extend(
                    await self.monitor.get_listings(search, after_time=self.last_notified)
                )
            _logger.debug(
                f"Found {len(listings)} to notify for across {len(self.active_searches)} active"
                " searches"
            )
            listings.sort(key=lambda l: l.updated_at)

            not_yet_notified_listings = listings.copy()
            for listing in listings:
                await self.notify(listing)
                not_yet_notified_listings.remove(listing)
            self.last_notified = datetime.now()
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
            self.last_notified = datetime.now()
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
        channel: "MessageableChannel",
        monitor: MarketplaceMonitor,
        notification_frequency: timedelta = timedelta(minutes=10),
        paused: bool = False,
        last_notified: datetime | None = None,
    ) -> None:
        super().__init__(monitor, notification_frequency, paused, last_notified)
        self.channel = channel

    async def notify(self, listing: Listing) -> None:
        await self.channel.send(f"{listing}")
