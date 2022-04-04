import asyncio
from datetime import datetime, timedelta

from notifier_bot.models import Listing, Location
from notifier_bot.sources.abc import PeriodicCheckListingSource


class MockSource(PeriodicCheckListingSource):
    """Mocks one listing per minute"""

    newest_listing: datetime = datetime.fromisoformat("2022-04-03T12:00:00")

    async def get_listings(
        self, after_time: datetime, limit: int | None = None  # pylint: disable=unused-argument
    ) -> list[Listing]:
        listings = []
        last_mock_listing_time = self.newest_listing

        while last_mock_listing_time > after_time:
            listings.append(
                Listing(
                    title="Mock listing",
                    url="mock-url",
                    body="mock body",
                    image_urls=[],
                    price=1,
                    location=Location(latitude=0, longitude=0),
                    distance_miles=0,
                    created_at=last_mock_listing_time,
                    updated_at=last_mock_listing_time,
                )
            )
            last_mock_listing_time -= timedelta(minutes=1)

        return listings


async def test_periodic_check_listing_source__new_listings() -> None:
    start_time = MockSource.newest_listing - timedelta(minutes=1, seconds=59)
    mock_source = MockSource(start_time=start_time)
    await asyncio.sleep(0.1)  # allow time for asyncio to schedule search task
    listings = await mock_source.new_listings()
    assert len(listings) == 2
    mock_source.search_task.cancel()  # type: ignore
