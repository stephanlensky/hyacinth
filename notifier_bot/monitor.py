import logging
from datetime import datetime, timedelta

from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger

from notifier_bot.celery import app
from notifier_bot.db.listing import get_last_listing as get_last_listing_from_db
from notifier_bot.db.listing import get_listings as get_listings_from_db
from notifier_bot.models import Listing, SearchSpec, SearchSpecSource
from notifier_bot.scheduler import get_scheduler
from notifier_bot.settings import get_settings
from notifier_bot.sources.craigslist import CraigslistSource
from notifier_bot.tasks import get_and_save_listings

settings = get_settings()
_logger = logging.getLogger(__name__)


class MarketplaceMonitor:
    def __init__(self) -> None:
        self.scheduler = get_scheduler()
        self.search_spec_job_mapping: dict[SearchSpec, Job] = {}

        # delete all pending tasks from previous runs of the bot
        app.control.purge()

    def register_search(self, search_spec: SearchSpec) -> None:
        # check if there is already a scheduled task to poll this search
        if search_spec in self.search_spec_job_mapping:
            return

        # otherwise schedule a job to periodically check results and write them to the db
        self.search_spec_job_mapping[search_spec] = self.scheduler.add_job(
            self.poll_search,
            kwargs={"search_spec": search_spec},
            trigger=IntervalTrigger(self._get_polling_interval(search_spec)),
            next_run_time=datetime.now(),
        )

    async def get_listings(self, search_spec: SearchSpec, after_time: datetime) -> list[Listing]:
        return get_listings_from_db(search_spec, after_time)

    @staticmethod
    def _get_polling_interval(search_spec: SearchSpec) -> int:
        if search_spec.source == SearchSpecSource.CRAIGSLIST:
            return CraigslistSource.recommended_polling_interval(search_spec.search_params)

        raise NotImplementedError(f"{search_spec.source} not implemented")

    async def poll_search(self, search_spec: SearchSpec) -> None:
        _logger.debug(f"Polling search {search_spec}")
        after_time = datetime.now() - timedelta(hours=settings.notifier_backdate_time_hours)
        last_listing = get_last_listing_from_db(search_spec)
        if last_listing is not None:
            # resume at the last listing time if it was more recent than 7 days ago
            after_time = max(last_listing.created_at, after_time)
            _logger.debug(
                f"Found recent listing at {last_listing.created_at}, resuming at {after_time}."
            )

        # start a celery task in a separate worker to get and save the listings
        get_and_save_listings.delay(search_spec.json(), after_time.isoformat())

    def __del__(self) -> None:
        for search_spec in self.search_spec_job_mapping:
            job = self.search_spec_job_mapping[search_spec]
            self.scheduler.remove_job(job.id)
