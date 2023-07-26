import logging
import re
from datetime import datetime
from typing import AsyncGenerator
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from hyacinth.settings import get_settings
from hyacinth.util.geo import distance_miles, reverse_geotag
from hyacinth.util.s3 import mirror_image
from hyacinth.util.scraping import get_page_content
from plugins.craigslist.models import CraigslistListing, CraigslistSearchParams
from plugins.craigslist.util import get_geotag_from_url

settings = get_settings()
_logger = logging.getLogger(__name__)


CRAIGSLIST_DATE_FORMAT = "%Y-%m-%d %H:%M"
CRAIGSLIST_SEARCH_URL = "https://{site}.craigslist.org/search/{category}#search=1~gallery~{page}~0"


async def get_listings(
    search_params: CraigslistSearchParams, after_time: datetime, limit: int | None = None
) -> list[CraigslistListing]:
    listings = []
    search = _search(search_params)
    async for listing in search:
        if listing.updated_time > after_time > listing.creation_time:
            _logger.debug(f"Skipping updated listing {listing.title}")
            continue
        if listing.creation_time <= after_time:
            await search.aclose()
            break

        _logger.debug(f"Found listing {listing.title} at {listing.creation_time}")
        listings.append(listing)
        if limit and len(listings) >= limit:
            await search.aclose()
            break

    return listings


async def _search(
    search_params: CraigslistSearchParams,
) -> AsyncGenerator[CraigslistListing, None]:
    page = 0
    while True:
        search_results_url = CRAIGSLIST_SEARCH_URL.format(
            site=search_params.site, category=search_params.category, page=page
        )
        search_results_content = await get_page_content(search_results_url)

        try:
            has_next_page, parsed_search_results = _parse_search_results(search_results_content)
        except Exception:
            _logger.exception(f"Error parsing search results {search_results_url}")
            with open(
                f"crash-{datetime.now().strftime('%Y%m%d%H%M%S')}-craigslist-search-results.html",
                "w",
            ) as f:
                f.write(search_results_content)
            raise

        for result_url in parsed_search_results:
            detail_content = await get_page_content(result_url)

            try:
                listing = _parse_result_details(result_url, detail_content)
            except Exception:
                _logger.exception(f"Error parsing listing {result_url}")
                with open(
                    f"crash-{datetime.now().strftime('%Y%m%d%H%M%S')}-craigslist-result-details.html",
                    "w",
                ) as f:
                    f.write(detail_content)
                raise

            _enrich_listing(listing)
            yield listing

        if not has_next_page:
            break

        page += 1


def _enrich_listing(listing: CraigslistListing) -> None:
    if not listing.latitude or not listing.longitude:
        listing.latitude, listing.longitude = get_geotag_from_url(listing.url)
    listing.distance_miles = distance_miles(
        (listing.latitude, listing.longitude), settings.home_lat_long
    )

    location = reverse_geotag((listing.latitude, listing.longitude))
    listing.city = location.city
    listing.state = location.state

    if listing.thumbnail_url and settings.enable_s3_thumbnail_mirroring:
        listing.thumbnail_url = mirror_image(listing.thumbnail_url)


def _parse_search_results(content: str) -> tuple[bool, list[str]]:
    """
    Parse Craigslist search results page and return a list of listing urls.
    """
    soup = BeautifulSoup(content, "html.parser")

    results_div = soup.find("div", class_="results")
    if not results_div:
        raise ValueError("Couldn't find results div!")
    listing_links = results_div.find_all("a", class_="main", attrs={"href": True})  # type: ignore
    listing_urls = [a.attrs["href"] for a in listing_links]

    page_number = soup.find("span", class_="cl-page-number")
    num_results = re.findall(r"\b(\d+)\b", page_number.text)  # type: ignore
    has_next_page = num_results[1] != num_results[2]

    return has_next_page, listing_urls


def _parse_result_details(url: str, content: str) -> CraigslistListing:
    """
    Parse Craigslist result details page.
    """
    soup = BeautifulSoup(content, "html.parser")

    # basic info
    title = soup.find("span", id="titletextonly").text.strip()  # type: ignore
    postingbody = soup.find("section", id="postingbody")
    postingbody.find("div", class_="print-information").decompose()  # type: ignore
    body = "\n".join(postingbody.stripped_strings)  # type: ignore

    # images
    thumbs_container = soup.find(id="thumbs")
    gallery = soup.find(class_="gallery")
    if thumbs_container:  # multiple images are present
        image_urls = [
            a.attrs["href"]
            for a in thumbs_container.find_all("a", attrs={"href": True})  # type: ignore
        ]
    elif gallery:  # only a single image
        image_urls = [gallery.find("img", attrs={"src": True}).attrs["src"]]  # type: ignore
    else:  # no images
        image_urls = []

    # price
    price_span = soup.find("span", class_="price")
    price = float(price_span.text[1:].replace(",", "").strip()) if price_span else 0  # type: ignore

    # location
    latitude = None
    longitude = None
    if soup.find("div", id="map"):
        latitude = float(soup.find("div", id="map")["data-latitude"])  # type: ignore
        longitude = float(soup.find("div", id="map")["data-longitude"])  # type: ignore

    # timestamps
    postinginfos = soup.find("div", class_="postinginfos")
    posted = postinginfos.find(lambda tag: "posted:" in tag.text and tag.find("time") is not None)  # type: ignore
    creation_time = datetime.fromisoformat(posted.find("time")["datetime"]).astimezone(ZoneInfo("UTC"))  # type: ignore
    updated = postinginfos.find(lambda tag: "updated:" in tag.text and tag.find("time") is not None)  # type: ignore
    updated_time = creation_time
    if updated:
        updated_time = datetime.fromisoformat(updated.find("time")["datetime"]).astimezone(ZoneInfo("UTC"))  # type: ignore

    return CraigslistListing(
        url=url,
        title=title,
        body=body,
        image_urls=image_urls,
        thumbnail_url=image_urls[0] if image_urls else None,
        price=price,
        city=None,
        state=None,
        latitude=latitude,
        longitude=longitude,
        creation_time=creation_time,
        updated_time=updated_time,
    )
