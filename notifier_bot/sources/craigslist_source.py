import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from craigslist import CraigslistForSale

from notifier_bot.models import CraigslistArea, Listing
from notifier_bot.sources.abc import PeriodicCheckListingSource
from notifier_bot.util.craigslist import get_geotag_from_url
from notifier_bot.util.geo import distance_miles, reverse_geotag

_logger = logging.getLogger(__name__)

CRAIGSLIST_DATE_FORMAT = "%Y-%m-%d %H:%M"


class CraigslistSource(PeriodicCheckListingSource[Listing]):
    def __init__(
        self,
        area: CraigslistArea,
        category: str,
        home_lat_long: tuple[float, float],
        min_price: int | None = None,
        max_price: int | None = None,
        max_distance_miles: float | None = None,
        start_time: datetime | None = None,
        interval_seconds: int = 600,
        loop: asyncio.AbstractEventLoop | None = None,
        start_search_task: bool = True,
    ) -> None:
        super().__init__(start_time, interval_seconds, loop, start_search_task)
        self.area = area
        self.category = category
        self.min_price = min_price
        self.max_price = max_price
        self.max_distance_miles = max_distance_miles
        self.home_lat_long = home_lat_long

    def get_craigslist_client(self) -> CraigslistForSale:
        filters = {
            "search_nearby": 2,
            "nearby_area": self.area.nearby_areas,
        }
        if self.min_price is not None:
            filters["min_price"] = self.min_price
        if self.max_price is not None:
            filters["max_price"] = self.max_price

        return CraigslistForSale(
            site=self.area.site,
            category=self.category,
            filters=filters,
        )

    async def get_listings(self, after_time: datetime, limit: int | None = None) -> list[Listing]:
        cl_client = self.get_craigslist_client()
        listings = []
        for search_result in cl_client.get_results(sort_by="newest", limit=limit):
            listing = self.__make_listing(cl_client.get_listing(search_result))
            if listing.updated_at > after_time > listing.created_at:
                _logger.debug(f"Skipping updated listing {listing.title}")
                continue
            if (
                self.max_distance_miles is not None
                and listing.distance_miles > self.max_distance_miles
            ):
                _logger.debug(f"Skipping further than max distance listing {listing.title}")
                continue
            if listing.created_at < after_time:
                break

            _logger.debug(f"Found listing {listing.title}")
            listings.append(listing)

        return listings

    def __make_listing(self, listing_json: dict[str, Any]) -> Listing:
        geotag = (
            listing_json["geotag"]
            if listing_json["geotag"]
            else get_geotag_from_url(listing_json["url"])
        )
        return Listing(
            title=listing_json["name"],
            url=listing_json["url"],
            body=listing_json["body"],
            image_urls=listing_json["images"],
            price=int(re.sub(r"[\$,]", "", listing_json["price"])),
            location=reverse_geotag(geotag),
            distance_miles=distance_miles(self.home_lat_long, geotag),
            created_at=datetime.strptime(listing_json["created"], CRAIGSLIST_DATE_FORMAT),
            updated_at=datetime.strptime(listing_json["last_updated"], CRAIGSLIST_DATE_FORMAT),
        )
