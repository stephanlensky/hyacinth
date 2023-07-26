import logging

import httpx

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
        )
        r.raise_for_status()

    return r.text
