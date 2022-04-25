from notifier_bot.models import SearchSpec, SearchSpecSource
from notifier_bot.settings import get_settings
from notifier_bot.sources.craigslist import CraigslistSearchParams
from notifier_bot.util.craigslist import get_areas

settings = get_settings()


def test_search_spec__is_hashable() -> None:
    areas = get_areas()

    _search_spec = SearchSpec(
        source=SearchSpecSource.CRAIGSLIST,
        search_params=CraigslistSearchParams(
            site=areas["New England/New York"].site,
            nearby_areas=areas["New England/New York"].nearby_areas,
            category="sss",
            home_lat_long=settings.home_lat_long,
            min_price=0,
            max_price=1000,
            max_distance_miles=100,
        ).dict(),
    )
