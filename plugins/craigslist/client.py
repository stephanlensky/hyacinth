import logging
import re
from datetime import datetime
from typing import AsyncGenerator
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from hyacinth.exceptions import ParseError
from hyacinth.settings import get_settings
from hyacinth.util.geo import reverse_geotag
from hyacinth.util.s3 import mirror_image
from hyacinth.util.scraping import scrape
from plugins.craigslist.models import CraigslistListing, CraigslistSearchParams
from plugins.craigslist.util import get_geotag_from_url

settings = get_settings()
_logger = logging.getLogger(__name__)


CRAIGSLIST_DATE_FORMAT = "%Y-%m-%d %H:%M"
CRAIGSLIST_SEARCH_URL = "https://{site}.craigslist.org/search/{category}#search=1~gallery~{page}~0"

METRIC_CRAIGSLIST_PARSE_ERROR_COUNT = "craigslist_parse_error_count"


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
        search_results_content = await _get_search_results_content(
            site=search_params.site, category=search_params.category, page=page
        )
        has_next_page, parsed_search_results = _parse_search_results(search_results_content)

        for result_url in parsed_search_results:
            detail_content = await _get_detail_content(result_url)
            listing = _parse_result_details(result_url, detail_content)
            await _enrich_listing(listing)
            yield listing

        if not has_next_page:
            break

        page += 1


async def _get_search_results_content(site: str, category: str, page: int) -> str:
    """
    Get the content of a Craigslist search results page.
    """
    search_results_url = CRAIGSLIST_SEARCH_URL.format(site=site, category=category, page=page)
    # selectors=["html"] to grab entire page
    scrape_result = await scrape(search_results_url, selectors=["html"], waitUntil="networkidle2")
    return "<html>" + scrape_result["data"][0]["results"][0]["html"] + "</html>"


async def _get_detail_content(url: str) -> str:
    """
    Get the content of a Craigslist listing details page.
    """
    # selectors=["html"] to grab entire page
    scrape_result = await scrape(url, selectors=["html"], waitUntil="networkidle2")
    return "<html>" + scrape_result["data"][0]["results"][0]["html"] + "</html>"


async def _enrich_listing(listing: CraigslistListing) -> None:
    if not listing.latitude or not listing.longitude:
        listing.latitude, listing.longitude = get_geotag_from_url(listing.url)

    location = reverse_geotag((listing.latitude, listing.longitude))
    listing.city = location.city
    listing.state = location.state

    if listing.thumbnail_url and settings.enable_s3_thumbnail_mirroring:
        listing.thumbnail_url = await mirror_image(listing.thumbnail_url)


def _parse_search_results(content: str) -> tuple[bool, list[str]]:
    """
    Parse Craigslist search results page and return a list of listing urls.
    """
    try:
        soup = BeautifulSoup(content, "html.parser")

        cl_results_page = soup.find("div", class_="cl-results-page")
        if not cl_results_page:
            raise ParseError("Couldn't find cl_results_page!", content)
        listing_links = cl_results_page.find_all("a", class_="main", attrs={"href": True})  # type: ignore
        listing_urls = [a.attrs["href"] for a in listing_links]

        page_number = soup.find("span", class_="cl-page-number")
        num_results = re.findall(r"\b(\d+)\b", page_number.text)  # type: ignore
        has_next_page = num_results[1] != num_results[2]

        return has_next_page, listing_urls
    except Exception as e:
        if isinstance(e, ParseError):
            raise
        raise ParseError("Error parsing search results", content) from e


def _parse_result_details(url: str, content: str) -> CraigslistListing:
    """
    Parse Craigslist result details page.
    """
    try:
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
    except Exception as e:
        raise ParseError(f"Error parsing listing {url}", content) from e
