import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlparse

import httpx
import pyppeteer

from hyacinth.metrics import METRIC_SCRAPE_COUNT, write_metric
from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)


async def get_page_content(url: str) -> str:
    """
    Get the content of a web page.
    """
    _logger.debug(f"Getting page content for {url}")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.browserless_url}/content?stealth&blockAds=true",
            json={"url": url},
            timeout=30.0,
        )
        domain = urlparse(url).netloc
        write_metric(METRIC_SCRAPE_COUNT, 1, labels={"domain": domain})
        r.raise_for_status()

    return r.text


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
