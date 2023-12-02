import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlparse

import pyppeteer

from hyacinth.metrics import METRIC_SCRAPE_COUNT, write_metric
from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_browser_page() -> AsyncIterator[pyppeteer.page.Page]:
    browser = await pyppeteer.launcher.connect(
        browserWSEndpoint="ws://browserless:3000?stealth&blockAds=true"
    )
    page = await browser.newPage()
    await page.setViewport({"width": 1920, "height": 1080})

    old_goto = page.goto

    async def goto_with_log(url: str, opts: dict | None = None) -> None:
        _logger.debug(f"Navigating to page {url}")
        domain = urlparse(url).netloc
        write_metric(METRIC_SCRAPE_COUNT, 1, labels={"domain": domain})
        if not opts:
            opts = {}
        await old_goto(url, opts)

    page.goto = goto_with_log

    try:
        yield page
    finally:
        await browser.close()
