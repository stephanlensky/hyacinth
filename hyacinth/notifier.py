from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from apscheduler.triggers.interval import IntervalTrigger

from hyacinth.db.crud.notifier import save_notifier_state
from hyacinth.db.crud.search_spec import add_search_spec
from hyacinth.db.models import Listing, SearchSpec
from hyacinth.db.session import Session
from hyacinth.filters import Filter
from hyacinth.models import ListingMetadata
from hyacinth.monitor import MarketplaceMonitor
from hyacinth.plugin import Plugin
from hyacinth.scheduler import get_async_scheduler
from hyacinth.settings import get_settings

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

settings = get_settings()
_logger = logging.getLogger(__name__)


@dataclass
class ActiveSearch:
    search_spec: SearchSpec
    last_notified: datetime


class ListingNotifier(ABC):
    @dataclass
    class Config:
        notification_frequency_seconds: int = settings.notification_frequency_seconds
        paused: bool = False
        active_searches: list[ActiveSearch] = field(default_factory=list)
        filters: dict[str, Filter] = field(default_factory=dict)

    def __init__(self, monitor: MarketplaceMonitor, config: ListingNotifier.Config) -> None:
        self.monitor = monitor
        self.config = config

        self.scheduler = get_async_scheduler()
        self.notify_job = self.scheduler.add_job(
            self._notify_new_listings,
            IntervalTrigger(seconds=self.config.notification_frequency_seconds),
            next_run_time=datetime.now(),
        )
        if self.config.paused:
            self.scheduler.pause_job(self.notify_job.id)

        for search in config.active_searches:
            self.monitor.register_search(search.search_spec)

    def create_search(
        self,
        plugin: Plugin,
        search_params_json: dict[str, Any],
        last_notified: datetime | None = None,
    ) -> None:
        if last_notified is None:
            last_notified = datetime.now() - timedelta(hours=settings.notifier_backdate_time_hours)

        with Session(expire_on_commit=False) as session:
            search_spec = add_search_spec(session, plugin.path, search_params_json)

        self.config.active_searches.append(
            ActiveSearch(
                search_spec=search_spec,
                last_notified=last_notified,
            )
        )

        self.monitor.register_search(search_spec)

    def pause(self) -> None:
        self.config.paused = True
        self.scheduler.pause_job(self.notify_job.id)

    def unpause(self) -> None:
        self.config.paused = False
        self.scheduler.resume_job(self.notify_job.id)

    def should_notify_listing(self, listing_metadata: ListingMetadata) -> bool:
        """
        Apply filters to the listing to see if we should notify the user.
        """
        listing = listing_metadata.listing
        for filter_field, filter_ in self.config.filters.items():
            if not hasattr(listing, filter_field):
                # this filter is for a field not present in this type of listing
                continue
            listing_field = getattr(listing, filter_field)

            if not filter_.test(listing_field):
                return False

        return True

    async def _get_new_listings_for_search(self, search: ActiveSearch) -> list[ListingMetadata]:
        """
        Get new listings for a given search.

        Updates the last_notified time for this search, so repeated calls will return only listings
        that have not been seen before.
        """
        new_listings = await self.monitor.get_listings(
            search.search_spec, after_time=search.last_notified
        )
        if new_listings:
            search.last_notified = new_listings[0].created_at
            _logger.debug(f"Most recent listing was found at {search.last_notified}")

        # save reference to plugin to format message later
        listing_metadata: list[ListingMetadata] = [
            ListingMetadata(listing=listing, plugin=search.search_spec.plugin)
            for listing in new_listings
        ]

        return listing_metadata

    async def _get_new_listings(self) -> list[ListingMetadata]:
        """
        Collect all new listings from all active searches
        """
        listings: list[ListingMetadata] = []
        for search in self.config.active_searches:
            listings.extend(await self._get_new_listings_for_search(search))
        if listings:
            # persist last_notified times to the database
            with Session() as session:
                save_notifier_state(session, self)

        _logger.debug(
            f"Found {len(listings)} to notify for across {len(self.config.active_searches)} active"
            " searches"
        )
        listings.sort(key=lambda l: l.listing.updated_at)
        return listings

    async def _notify_new_listings(self) -> None:
        not_yet_notified_listings: list[ListingMetadata] = []
        try:
            listings = await self._get_new_listings()
            if not listings:
                return

            # apply filters
            unfiltered_listings_length = len(listings)
            listings = list(filter(self.should_notify_listing, listings))
            _logger.debug(
                f"Filtered out {unfiltered_listings_length - len(listings)} listings. Notifying"
                f" user of remaining {len(listings)} listings."
            )

            not_yet_notified_listings = listings.copy()
            for listing in listings:
                await self.notify(listing.plugin, listing.listing)
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
                await self.notify(listing.plugin, listing.listing)
            raise

    def cleanup(self) -> None:
        _logger.debug("Cleaning up notifier!")
        self.scheduler.remove_job(self.notify_job.id)
        for search in self.config.active_searches:
            self.monitor.remove_search(search.search_spec)

    @abstractmethod
    async def notify(self, plugin: Plugin, listing: Listing) -> None:
        pass


class LoggerNotifier(ListingNotifier):
    async def notify(self, plugin: Plugin, listing: Listing) -> None:
        _logger.info(f"Notify listing {listing.listing_json}")


class ChannelNotifier(ListingNotifier):
    def __init__(
        self,
        channel: MessageableChannel,
        monitor: MarketplaceMonitor,
        config: ListingNotifier.Config,
    ) -> None:
        super().__init__(monitor, config)
        self.channel = channel

    async def notify(self, plugin: Plugin, listing: Listing) -> None:
        parsed_listing = plugin.listing_cls.parse_raw(listing.listing_json)
        message = plugin.format_listing(parsed_listing)
        await self.channel.send(**message.dict())
