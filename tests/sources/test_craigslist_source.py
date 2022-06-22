from datetime import datetime, timedelta

from hyacinth.sources.craigslist import CraigslistSearchParams, CraigslistSource
from hyacinth.util.craigslist import get_areas


async def test_craigslist_source_get_listings__returns_a_listing() -> None:
    area = get_areas()["New England/New York"]
    craigslist_source = CraigslistSource(
        CraigslistSearchParams(
            site=area.site,
            nearby_areas=area.nearby_areas,
            category="sss",  # general for sale
        )
    )
    listings = await craigslist_source.get_listings(datetime.now() - timedelta(days=1000), limit=1)
    assert len(listings) == 1
