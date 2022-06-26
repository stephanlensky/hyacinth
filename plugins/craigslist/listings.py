import logging
import re
from datetime import datetime
from functools import cache
from typing import Any

from craigslist import CraigslistForSale

from hyacinth.models import Listing
from hyacinth.settings import get_settings
from hyacinth.util.geo import reverse_geotag
from hyacinth.util.s3 import mirror_image
from plugins.craigslist.models import CraigslistSearchParams
from plugins.craigslist.util import get_geotag_from_url

settings = get_settings()
_logger = logging.getLogger(__name__)


CRAIGSLIST_DATE_FORMAT = "%Y-%m-%d %H:%M"


@cache
def get_craigslist_client(search_params: CraigslistSearchParams) -> CraigslistForSale:
    filters = {
        "search_nearby": 2,
        "nearby_area": search_params.nearby_areas,
    }

    return CraigslistForSale(
        site=search_params.site,
        category=search_params.category,
        filters=filters,
    )


def get_listings(
    search_params: CraigslistSearchParams, after_time: datetime, limit: int | None = None
) -> list[Listing]:
    cl_client = get_craigslist_client(search_params)
    listings = []
    for search_result in cl_client.get_results(
        geotagged=True, include_details=True, sort_by="newest", limit=limit
    ):
        listing = _make_listing(search_result)
        if listing.updated_at > after_time > listing.created_at:
            _logger.debug(f"Skipping updated listing {listing.title}")
            continue
        if listing.created_at <= after_time:
            break

        _logger.debug(f"Found listing {listing.title} at {listing.created_at}")
        listings.append(listing)

    return listings


def _make_listing(listing_json: dict[str, Any]) -> Listing:
    geotag = (
        listing_json["geotag"]
        if listing_json["geotag"]
        else get_geotag_from_url(listing_json["url"])
    )
    if listing_json["price"] is None:  # item is free
        listing_json["price"] = "0"
    listing_json["price"] = re.sub(r"[\$,]", "", str(listing_json["price"]))
    try:
        price = int(str(listing_json["price"]))
    except ValueError:
        _logger.error(
            f"Couldn't parse price {listing_json['price']} for listing {listing_json['url']}!"
        )
        price = 0

    image_urls: list[str] = listing_json["images"]
    thumbnail_url: str | None = image_urls[0] if image_urls else None
    if thumbnail_url and settings.enable_s3_thumbnail_mirroring:
        thumbnail_url = mirror_image(thumbnail_url)

    return Listing(
        title=listing_json["name"],
        url=listing_json["url"],
        body=listing_json["body"],
        image_urls=image_urls,
        thumbnail_url=thumbnail_url,
        price=price,
        location=reverse_geotag(geotag),
        created_at=datetime.strptime(listing_json["created"], CRAIGSLIST_DATE_FORMAT),
        updated_at=datetime.strptime(listing_json["last_updated"], CRAIGSLIST_DATE_FORMAT),
    )
