import json
import logging
from datetime import datetime
from typing import AsyncGenerator

import pyppeteer
from bs4 import BeautifulSoup
from pyppeteer.errors import TimeoutError
from zoneinfo import ZoneInfo

from hyacinth.exceptions import ParseError
from hyacinth.settings import get_settings
from hyacinth.util.geo import reverse_geotag
from hyacinth.util.scraping import get_browser_page
from plugins.marketplace.models import MarketplaceListing, MarketplaceSearchParams

settings = get_settings()
_logger = logging.getLogger(__name__)

MARKETPLACE_SEARCH_URL = "https://www.facebook.com/marketplace/{location}/{category}/?sortBy=creation_time_descend&exact=false"


async def get_listings(
    search_params: MarketplaceSearchParams, after_time: datetime, limit: int | None = None
) -> list[MarketplaceListing]:
    listings = []
    search = _search(search_params)
    async for listing in search:
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
    search_params: MarketplaceSearchParams,
) -> AsyncGenerator[MarketplaceListing, None]:
    async with get_browser_page() as page:
        _navigate_to_search_results(page, search_params.location, search_params.category)

        num_results = 0
        while True:  # loop while there are new results (scrolling down loads more results)
            _logger.debug("Getting search results page content")
            search_content = await page.content()

            result_urls = _parse_search_results(search_content)
            if len(result_urls) == num_results:  # no more results to load
                break
            num_results = len(result_urls)

            async with get_browser_page() as result_page:
                for url in result_urls:
                    result_content = await _navigate_to_listing_and_get_content(result_page, url)

                    listing = _parse_result_details(url, result_content)

                    await _enrich_listing(listing)
                    yield listing

            _logger.debug("Scrolling down to load more results")
            previous_height = await page.evaluate("""document.body.scrollHeight""")
            await page.evaluate("""{window.scrollBy(0, document.body.scrollHeight);}""")
            try:
                await page.waitForFunction(
                    f"""document.body.scrollHeight > {previous_height}""", {"timeout": 5000}
                )
            except TimeoutError:
                _logger.debug("Timed out waiting for more results to load")
                pass  # page height never increased, likely no more results to load


async def _navigate_to_search_results(
    page: pyppeteer.page.Page, location: str, category: str
) -> None:
    search_results_url = MARKETPLACE_SEARCH_URL.format(location=location, category=category)

    _logger.debug("Loading marketplace search results")
    await page.goto(search_results_url)
    _logger.debug("Waiting for marketplace search results to render")
    try:
        await page.waitForFunction(
            """document.querySelector("div[aria-label='Collection of Marketplace items']") !== null""",
            {"timeout": 5000},  # 5s
        )
    except TimeoutError:
        raise ParseError("Timed out waiting for search results to render", await page.content())
    _logger.debug("Marketplace search results rendered")


async def _navigate_to_listing_and_get_content(page: pyppeteer.page.Page, url: str) -> str:
    await page.goto(url)
    _logger.debug(f"Getting page content for {url}")
    return await page.content()


async def _enrich_listing(listing: MarketplaceListing) -> None:
    location = reverse_geotag((listing.latitude, listing.longitude))
    listing.city = location.city
    listing.state = location.state


def _parse_search_results(content: str) -> list[str]:
    """
    Parse Marketplace search results page and return a list of listing urls.
    """
    try:
        soup = BeautifulSoup(content, "html.parser")
        items_container = soup.find("div", attrs={"aria-label": "Collection of Marketplace items"})
        if not items_container:
            raise ValueError("Could not find items container")

        link_tags = soup.find_all("a", attrs={"href": True})
        result_urls = [
            link["href"] for link in link_tags if link["href"].startswith("/marketplace/item")
        ]
        # remove tracking query params
        result_urls = [url.split("?")[0] for url in result_urls]
        # make urls absolute
        result_urls = [f"https://www.facebook.com{url}" for url in result_urls]

        return result_urls
    except Exception as e:
        raise ParseError("Error parsing search results", content) from e


def _parse_result_details(url: str, content: str) -> MarketplaceListing:
    """
    Parse Marketplace result details page.
    """
    try:
        soup = BeautifulSoup(content, "html.parser")
        scripts = soup.find_all("script")
        product_data_script = None
        for script in scripts:
            if "marketplace_product_details_page" in script.text:
                product_data_script = script
                break

        if product_data_script is None:
            raise ValueError("Could not find product data script")

        json_start = product_data_script.text.find('{"marketplace_product_details_page":')
        json_end = product_data_script.text.find(',"node":{', json_start)
        if json_start == -1 or json_end == -1:
            raise ValueError("Could not find product JSON in product data script")

        raw_product_json = product_data_script.text[json_start:json_end]
        product_json = json.loads(raw_product_json)
        details_json = product_json["marketplace_product_details_page"]

        image_urls = [p["image"]["uri"] for p in details_json["target"]["listing_photos"]]
        # FB gives unix timestamp in user's local timezone
        creation_time = datetime.fromtimestamp(
            details_json["target"]["creation_time"], tz=ZoneInfo(settings.tz)
        )

        return MarketplaceListing(
            url=url,
            title=details_json["target"]["marketplace_listing_title"],
            body=details_json["target"]["redacted_description"]["text"],
            image_urls=image_urls,
            thumbnail_url=image_urls[0] if image_urls else None,
            price=float(details_json["target"]["listing_price"]["amount"]),
            latitude=details_json["marketplace_listing_renderable_target"]["location"]["latitude"],
            longitude=details_json["marketplace_listing_renderable_target"]["location"][
                "longitude"
            ],
            creation_time=creation_time,
        )
    except Exception as e:
        raise ParseError("Error parsing result details", content) from e
