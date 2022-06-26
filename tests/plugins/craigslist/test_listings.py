from datetime import datetime, timedelta

from plugins.craigslist.listings import get_listings
from plugins.craigslist.models import CraigslistSearchParams
from plugins.craigslist.util import get_areas


def test_craigslist_source_get_listings__returns_a_listing() -> None:
    area = get_areas()["New England/New York"]
    listings = get_listings(
        CraigslistSearchParams(
            site=area.site,
            nearby_areas=area.nearby_areas,
            category="sss",  # general for sale
        ),
        datetime.now() - timedelta(days=1000),
        limit=1,
    )
    assert len(listings) == 1
