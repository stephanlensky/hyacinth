import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import urlparse

import httpx
import pyppeteer

from hyacinth.metrics import METRIC_SCRAPE_COUNT, write_metric
from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)


async def scrape(url: str, selectors: list[str], waitUntil: str) -> dict[str, Any]:
    """
    Scrape a webpage using the browserless /scrape API.
    """
    _logger.debug(f"Scraping {url}")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.browserless_url}/scrape?stealth&blockAds=true",
            json={
                "url": url,
                "elements": [{"selector": s} for s in selectors],
                "gotoOptions": {"timeout": 10_000, "waitUntil": waitUntil},
            },
            timeout=30.0,
        )
        try:
            r.raise_for_status()
        except Exception:
            _logger.error(f"Failed to scrape {url}: {r.text}")
            raise
        domain = urlparse(url).netloc
        write_metric(METRIC_SCRAPE_COUNT, 1, labels={"domain": domain})

    return r.json()


@asynccontextmanager
async def get_browser_page() -> AsyncIterator[pyppeteer.page.Page]:
    browser = await pyppeteer.launcher.connect(
        browserWSEndpoint="ws://browserless:3000?stealth&blockAds=true"
    )
    page = await browser.newPage()
    await page.setViewport({"width": 1920, "height": 1080})

    old_goto = page.goto

    async def goto_with_log(url: str) -> None:
        _logger.debug(f"Loading page {url}")
        domain = urlparse(url).netloc
        write_metric(METRIC_SCRAPE_COUNT, 1, labels={"domain": domain})
        await old_goto(url)

    page.goto = goto_with_log

    try:
        yield page
    finally:
        await browser.close()
