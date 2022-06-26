import logging
from datetime import datetime, timedelta

from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger

from hyacinth.db.listing import get_last_listing as get_last_listing_from_db
from hyacinth.db.listing import get_listings as get_listings_from_db
from hyacinth.db.listing import save_listings as save_listings_to_db
from hyacinth.models import Listing, SearchSpec
from hyacinth.scheduler import get_threadpool_scheduler
from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)


class MarketplaceMonitor:
    def __init__(self) -> None:
        self.scheduler = get_threadpool_scheduler()
        self.search_spec_job_mapping: dict[SearchSpec, Job] = {}
        self.search_spec_ref_count: dict[SearchSpec, int] = {}

    def register_search(self, search_spec: SearchSpec) -> None:
        # check if there is already a scheduled task to poll this search
        if search_spec in self.search_spec_job_mapping:
            _logger.info("Search already exists, not registering new search")
            self.search_spec_ref_count[search_spec] += 1
            return

        # otherwise schedule a job to periodically check results and write them to the db
        _logger.info(f"Scheduling job for new search! {search_spec}")
        self.search_spec_job_mapping[search_spec] = self.scheduler.add_job(
            self.poll_search,
            kwargs={"search_spec": search_spec},
            trigger=IntervalTrigger(
                seconds=search_spec.plugin.polling_interval(search_spec.search_params)
            ),
            next_run_time=datetime.now(),
        )
        self.search_spec_ref_count[search_spec] = 1

    def remove_search(self, search_spec: SearchSpec) -> None:
        self.search_spec_ref_count[search_spec] -= 1
        if self.search_spec_ref_count[search_spec] == 0:
            # there are no more notifiers looking at this search, remove the monitoring job
            _logger.debug(f"Removing search from monitor {search_spec}")
            job = self.search_spec_job_mapping[search_spec]
            self.scheduler.remove_job(job.id)
            del self.search_spec_job_mapping[search_spec]
            del self.search_spec_ref_count[search_spec]

    async def get_listings(self, search_spec: SearchSpec, after_time: datetime) -> list[Listing]:
        return get_listings_from_db(search_spec, after_time)

    def poll_search(self, search_spec: SearchSpec) -> None:
        if settings.disable_search_polling:
            _logger.debug(f"Search polling is disabled, would poll search {search_spec}")
            return

        _logger.debug(f"Polling search {search_spec}")
        after_time = datetime.now() - timedelta(hours=settings.notifier_backdate_time_hours)
        last_listing = get_last_listing_from_db(search_spec)
        if last_listing is not None:
            # resume at the last listing time if it was more recent than 7 days ago
            after_time = max(last_listing.created_at, after_time)
            _logger.debug(
                f"Found recent listing at {last_listing.created_at}, resuming at {after_time}."
            )

        listings = search_spec.plugin.get_listings(search_spec.search_params, after_time)
        save_listings_to_db(search_spec, listings)
        _logger.debug(f"Found {len(listings)} since {after_time} for search_spec={search_spec}")

    def __del__(self) -> None:
        for search_spec in self.search_spec_job_mapping:
            job = self.search_spec_job_mapping[search_spec]
            self.scheduler.remove_job(job.id)
