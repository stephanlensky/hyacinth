import logging
import typing
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

from hyacinth.metrics import METRIC_SCRAPE_COUNT, write_metric
from hyacinth.settings import get_settings
from hyacinth.util.save_pages import save_scraped_page

settings = get_settings()
_logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_browser_context() -> AsyncIterator[BrowserContext]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(
            "ws://browserless:3000?stealth&blockAds=true"
        )
        context = await browser.new_context()
        _patch_new_page(context)

        try:
            yield context
        finally:
            await context.close()


def _patch_new_page(context: BrowserContext) -> None:
    old_new_page = context.new_page

    async def new_patched_page() -> Page:
        page = await old_new_page()
        _patch_goto(page)
        _patch_content(page)
        return page

    setattr(context, "new_page", new_patched_page)


def _patch_goto(page: Page) -> None:
    old_goto = page.goto

    async def goto_with_log(
        url: str,
        *,
        timeout: typing.Optional[float] = None,
        wait_until: typing.Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = None,
        referer: typing.Optional[str] = None,
    ) -> None:
        _logger.debug(f"Navigating to page {url}")
        domain = urlparse(url).netloc
        write_metric(METRIC_SCRAPE_COUNT, 1, labels={"domain": domain})
        await old_goto(url, timeout=timeout, wait_until=wait_until, referer=referer)

    setattr(page, "goto", goto_with_log)


def _patch_content(page: Page) -> None:
    old_content = page.content

    async def content_with_page_save() -> str:
        content: str = await old_content()
        if settings.save_scraped_pages:
            save_scraped_page(page.url, content)

        return content

    setattr(page, "content", content_with_page_save)
