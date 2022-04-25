import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from notifier_bot.models import Listing, SearchSpec
from notifier_bot.monitor import MarketplaceMonitor

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
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.monitor = monitor
        self.notification_frequency: timedelta = notification_frequency

        if last_notified is None:
            self.last_notified = datetime.now()
        self.paused = paused
        self.active_searches: list[SearchSpec] = []

        self._loop = loop
        self._notification_task: asyncio.Task | None = (
            self._start_notification_task(loop) if not self.paused else None
        )

    def create_search(self, search_spec: SearchSpec) -> None:
        self.monitor.register_search(search_spec)
        self.active_searches.append(search_spec)

    def pause(self) -> None:
        self.paused = True
        if self._notification_task is not None:
            self._notification_task.cancel()
            self._notification_task = None

    def unpause(self) -> None:
        self.paused = False
        if self._notification_task is None:
            self._notification_task = self._start_notification_task(self._loop)

    def _start_notification_task(
        self, loop: asyncio.AbstractEventLoop | None = None
    ) -> asyncio.Task:
        _logger.debug("Starting notifier task!")
        if loop is None:
            loop = asyncio.get_running_loop()
        return loop.create_task(self._notify_new_listings_loop())

    async def _notify_new_listings_loop(self) -> None:
        while True:
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

                await asyncio.sleep(self.notification_frequency.seconds)
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
                break

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
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        super().__init__(monitor, notification_frequency, paused, last_notified, loop)
        self.channel = channel

    async def notify(self, listing: Listing) -> None:
        await self.channel.send(f"{listing}")
