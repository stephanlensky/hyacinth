from datetime import datetime

from notifier_bot.models import Listing, SearchSpec, SearchSpecSource
from notifier_bot.sources.abc import ListingSource
from notifier_bot.sources.craigslist import CraigslistSearchParams, CraigslistSource


class MarketplaceMonitor:
    def __init__(self) -> None:
        self.search_spec_source_mapping: dict[SearchSpec, ListingSource]

    def register_search(self, search_spec: SearchSpec) -> None:
        if search_spec in self.search_spec_source_mapping:
            return

        source = self._make_source(search_spec)
        self.search_spec_source_mapping[search_spec] = source
        self._start_poll_task(source)

    async def get_listings(self, search_spec: SearchSpec, after_time: datetime) -> list[Listing]:
        # retrieve listings from db
        pass

    @staticmethod
    def _make_source(search_spec: SearchSpec) -> ListingSource:
        if search_spec.source == SearchSpecSource.CRAIGSLIST:
            return CraigslistSource(
                CraigslistSearchParams(**dict(search_spec.search_params)),
            )

        raise NotImplementedError(f"{search_spec.source} not implemented")

    def _start_poll_task(self, source: ListingSource) -> None:
        # periodically poll for new listings from the source and write to db
        pass
