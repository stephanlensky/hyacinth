from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from apscheduler.triggers.interval import IntervalTrigger
from zoneinfo import ZoneInfo

from hyacinth import filters
from hyacinth.db.crud.filter import add_filter
from hyacinth.db.crud.notifier import save_notifier_state
from hyacinth.db.crud.notifier_search import add_notifier_search
from hyacinth.db.crud.search_spec import add_search_spec
from hyacinth.db.models import Filter, Listing, NotifierSearch
from hyacinth.db.session import Session
from hyacinth.enums import RuleType
from hyacinth.models import ListingMetadata
from hyacinth.monitor import SearchMonitor
from hyacinth.plugin import Plugin
from hyacinth.scheduler import get_async_scheduler
from hyacinth.settings import get_settings

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

settings = get_settings()
_logger = logging.getLogger(__name__)


class ListingNotifier(ABC):
    @dataclass
    class Config:
        id: int | None = None
        notification_frequency_seconds: int = settings.notification_frequency_seconds
        paused: bool = False
        home_location: tuple[float, float] | None = None
        active_searches: list[NotifierSearch] = field(default_factory=list)
        filters: list[Filter] = field(default_factory=list)

    def __init__(self, monitor: SearchMonitor, config: ListingNotifier.Config) -> None:
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

        _logger.debug(
            "Successfully initialized notifier! Notifier state is:"
            f" {'paused' if self.config.paused else 'unpaused'}"
        )

    def get_active_plugins(self) -> list[Plugin]:
        return [search.search_spec.plugin for search in self.config.active_searches]

    def create_search(
        self,
        name: str,
        plugin: Plugin,
        search_params_json: dict[str, Any],
        last_notified: datetime | None = None,
    ) -> None:
        if last_notified is None:
            last_notified = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")) - timedelta(
                hours=settings.notifier_backdate_time_hours
            )

        with Session(expire_on_commit=False) as session:
            search_spec = add_search_spec(session, plugin.path, search_params_json)
            notifier_search = add_notifier_search(session, self, name, search_spec, last_notified)
            self.config.active_searches.append(notifier_search)

            # commit changes to the database
            session.commit()

        self.monitor.register_search(search_spec)

    def remove_search(self, search: NotifierSearch) -> None:
        self.config.active_searches.remove(search)
        self.monitor.remove_search(search.search_spec)

        with Session() as session:
            session.delete(search)
            session.commit()

    def update_search(self, search: NotifierSearch, new_search_params: dict[str, Any]) -> None:
        with Session(expire_on_commit=False) as session:
            new_search_spec = add_search_spec(
                session, search.search_spec.plugin_path, new_search_params
            )

            search.search_spec = new_search_spec

            session.merge(search)
            session.commit()

        self.monitor.remove_search(search.search_spec)
        self.monitor.register_search(new_search_spec)

    def add_filter(self, field: str, rule_type: RuleType, rule_expr: str) -> None:
        if self.config.id is None:
            raise ValueError("Cannot add filter to unsaved notifier!")

        with Session(expire_on_commit=False) as session:
            filter = add_filter(session, self.config.id, field, rule_type, rule_expr)
            session.commit()

        self.config.filters.append(filter)

    def update_filter(self, filter: Filter, new_rule: str) -> None:
        with Session(expire_on_commit=False) as session:
            filter.rule_expr = new_rule

            session.merge(filter)
            session.commit()

    def remove_filter(self, filter: Filter) -> None:
        with Session(expire_on_commit=False) as session:
            session.delete(filter)
            session.commit()

        self.config.filters.remove(filter)

    def set_paused(self, paused: bool) -> None:
        self.config.paused = paused
        if paused:
            self.scheduler.pause_job(self.notify_job.id)
        else:
            self.scheduler.resume_job(self.notify_job.id)

        with Session() as session:
            save_notifier_state(session, self)
            session.commit()

    def set_notification_frequency(self, frequency_seconds: int) -> None:
        self.config.notification_frequency_seconds = frequency_seconds
        self.scheduler.reschedule_job(
            self.notify_job.id, trigger=IntervalTrigger(seconds=frequency_seconds)
        )

        with Session() as session:
            save_notifier_state(session, self)
            session.commit()

    def set_home_location(self, home_location: tuple[float, float] | None) -> None:
        self.config.home_location = home_location

        with Session(expire_on_commit=False) as session:
            save_notifier_state(session, self)
            session.commit()

    def should_notify_listing(self, listing_metadata: ListingMetadata) -> bool:
        """
        Apply filters to the listing to see if we should notify the user.
        """
        listing: dict[str, Any] = json.loads(listing_metadata.listing.listing_json)
        return filters.test(listing, self.config.filters)

    async def _get_new_listings_for_search(self, search: NotifierSearch) -> list[ListingMetadata]:
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
            _logger.debug(
                f"Updating last_notified times for {len(self.config.active_searches)} active"
                " searches"
            )
            with Session() as session:
                for search in self.config.active_searches:
                    session.merge(search)
                session.commit()

        _logger.debug(
            f"Found {len(listings)} to notify for across {len(self.config.active_searches)} active"
            " searches"
        )
        listings.sort(key=lambda lm: lm.listing.updated_at)
        return listings

    async def _notify_new_listings(self) -> None:
        _logger.debug("Running notifier for new listings!")
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
        monitor: SearchMonitor,
        config: ListingNotifier.Config,
    ) -> None:
        super().__init__(monitor, config)
        self.channel = channel

    async def notify(self, plugin: Plugin, listing: Listing) -> None:
        parsed_listing = plugin.listing_cls.model_validate_json(listing.listing_json)
        message = plugin.format_listing(self, parsed_listing)
        await self.channel.send(**message.model_dump())
