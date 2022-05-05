from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from craigslist import CraigslistForSale
from pydantic import BaseModel, validator

from notifier_bot.models import Listing
from notifier_bot.settings import get_settings
from notifier_bot.sources.abc import ListingSource
from notifier_bot.util.craigslist import get_geotag_from_url
from notifier_bot.util.geo import distance_miles, reverse_geotag

settings = get_settings()
_logger = logging.getLogger(__name__)

CRAIGSLIST_DATE_FORMAT = "%Y-%m-%d %H:%M"


class CraigslistSearchParams(BaseModel):
    site: str
    nearby_areas: tuple[str, ...]
    category: str
    home_lat_long: tuple[float, float]
    min_price: int | None = None
    max_price: int | None = None
    max_distance_miles: float | None = None

    @validator("nearby_areas", pre=True)
    @classmethod
    def nearby_areas_list_to_tuple(cls, v: Any) -> tuple:
        return tuple(v)


class CraigslistSource(ListingSource):
    def __init__(self, search_params: CraigslistSearchParams) -> None:
        self.search_params = search_params

    @property
    def recommended_polling_interval(self) -> int:
        return settings.craigslist_poll_interval_seconds

    def get_craigslist_client(self) -> CraigslistForSale:
        filters = {
            "search_nearby": 2,
            "nearby_area": self.search_params.nearby_areas,
        }
        if self.search_params.min_price is not None:
            filters["min_price"] = self.search_params.min_price
        if self.search_params.max_price is not None:
            filters["max_price"] = self.search_params.max_price

        return CraigslistForSale(
            site=self.search_params.site,
            category=self.search_params.category,
            filters=filters,
        )

    async def get_listings(self, after_time: datetime, limit: int | None = None) -> list[Listing]:
        cl_client = self.get_craigslist_client()
        listings = []
        for search_result in cl_client.get_results(sort_by="newest", limit=limit):
            listing = self._make_listing(cl_client.get_listing(search_result))
            if listing.updated_at > after_time > listing.created_at:
                _logger.debug(f"Skipping updated listing {listing.title}")
                continue
            if (
                self.search_params.max_distance_miles is not None
                and listing.distance_miles > self.search_params.max_distance_miles
            ):
                _logger.debug(f"Skipping further than max distance listing {listing.title}")
                continue
            if listing.created_at <= after_time:
                break

            _logger.debug(f"Found listing {listing.title} at {listing.created_at}")
            listings.append(listing)

        return listings

    def _make_listing(self, listing_json: dict[str, Any]) -> Listing:
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
            distance_miles=distance_miles(self.search_params.home_lat_long, geotag),
            created_at=datetime.strptime(listing_json["created"], CRAIGSLIST_DATE_FORMAT),
            updated_at=datetime.strptime(listing_json["last_updated"], CRAIGSLIST_DATE_FORMAT),
        )
