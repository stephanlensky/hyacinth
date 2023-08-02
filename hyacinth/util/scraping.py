import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import pyppeteer

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
            f"{settings.browserless_url}/content?stealth",
            json={"url": url},
            timeout=15.0,
        )
        r.raise_for_status()

    return r.text


@asynccontextmanager
async def get_browser_page() -> AsyncIterator[pyppeteer.page.Page]:
    browser = await pyppeteer.launcher.connect(browserWSEndpoint="ws://browserless:3000")
    page = await browser.newPage()
    await page.setViewport({"width": 1920, "height": 1080})
    try:
        yield page
    finally:
        await browser.close()
