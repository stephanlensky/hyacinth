import asyncio
import logging
from datetime import datetime, timedelta

from notifier_bot.db.listing import get_last_listing as get_last_listing_from_db
from notifier_bot.db.listing import get_listings as get_listings_from_db
from notifier_bot.db.listing import save_listings as save_listings_to_db
from notifier_bot.models import Listing, SearchSpec, SearchSpecSource
from notifier_bot.sources.abc import ListingSource
from notifier_bot.sources.craigslist import CraigslistSearchParams, CraigslistSource

_logger = logging.getLogger(__name__)


class MarketplaceMonitor:
    def __init__(self) -> None:
        self.search_spec_source_mapping: dict[SearchSpec, ListingSource] = {}

    def register_search(self, search_spec: SearchSpec) -> None:
        if search_spec in self.search_spec_source_mapping:
            return

        source = self._make_source(search_spec)
        self.search_spec_source_mapping[search_spec] = source
        self._start_poll_task(source, search_spec)

    async def get_listings(self, search_spec: SearchSpec, after_time: datetime) -> list[Listing]:
        return get_listings_from_db(search_spec, after_time)

    @staticmethod
    def _make_source(search_spec: SearchSpec) -> ListingSource:
        if search_spec.source == SearchSpecSource.CRAIGSLIST:
            return CraigslistSource(
                CraigslistSearchParams.parse_obj(dict(search_spec.search_params)),
            )

        raise NotImplementedError(f"{search_spec.source} not implemented")

    def _start_poll_task(
        self,
        source: ListingSource,
        search_spec: SearchSpec,
    ) -> asyncio.Task:
        loop = asyncio.get_running_loop()
        return loop.create_task(self._poll_loop(source, search_spec))

    async def _poll_loop(self, source: ListingSource, search_spec: SearchSpec) -> None:
        _logger.debug(f"Starting poll loop for search {search_spec}")
        start_time = datetime.now() - timedelta(days=7)
        last_listing = get_last_listing_from_db(search_spec)
        if last_listing is not None:
            # resume at the last listing time if it was more recent
            start_time = max(last_listing.created_at, start_time)
            _logger.debug(
                f"Found recent listing at {last_listing.created_at}, resuming at {start_time}."
            )

        while True:
            try:
                listings = await source.get_listings(after_time=start_time)
                _logger.debug(
                    f"Found {len(listings)} since {start_time} for search_spec={search_spec}"
                )
                save_listings_to_db(search_spec, listings)
                await asyncio.sleep(source.recommended_polling_interval)
            except asyncio.CancelledError:
                break
