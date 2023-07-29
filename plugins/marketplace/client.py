import logging
from datetime import datetime
from typing import AsyncGenerator

from hyacinth.util.scraping import get_page_content
from plugins.marketplace.models import MarketplaceListing, MarketplaceSearchParams

_logger = logging.getLogger(__name__)

MARKETPLACE_SEARCH_URL = "https://www.facebook.com/marketplace/{location}/{category}/?exact=false"


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
    while True:
        search_results_url = MARKETPLACE_SEARCH_URL.format(
            location=search_params.location, category=search_params.category
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

            await _enrich_listing(listing)
            yield listing

        if not has_next_page:
            break


async def _enrich_listing(listing: MarketplaceListing) -> None:
    pass


def _parse_search_results(content: str) -> list[str]:
    """
    Parse Craigslist search results page and return a list of listing urls.
    """
    pass


def _parse_result_details(url: str, content: str) -> MarketplaceListing:
    """
    Parse Craigslist result details page.
    """
    pass
