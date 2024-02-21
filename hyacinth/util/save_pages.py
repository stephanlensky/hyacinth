import logging
import re
from datetime import datetime
from pathlib import Path

from hyacinth.settings import get_settings

_logger = logging.getLogger(__name__)
settings = get_settings()


def save_scraped_page(url: str, content: str) -> None:
    """
    Save a scraped page to a file.
    """
    now = datetime.now()
    sanitized_url = re.sub(r"^https:\/\/(www\.)?|[^a-zA-Z0-9\-_]", "", url)
    fname = Path(settings.scraped_pages_save_folder) / Path(
        f"page_content_{now.isoformat()}_{sanitized_url}.html"
    )
    _logger.info(f"Saving page content to {fname}")
    fname.parent.mkdir(parents=True, exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"<!-- Hyacinth scrape of {url} at {now.isoformat()} -->\n")
        f.write(content)
