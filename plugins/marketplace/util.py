import json
import logging
import os
from functools import cache
from pathlib import Path

from bs4 import BeautifulSoup

from plugins.marketplace.models import MarketplaceCategory

_logger = logging.getLogger(__name__)

CATEGORIES_HTML_PATH = Path(os.path.realpath(__file__)).parent / "categories.html"


@cache
def get_categories() -> list[MarketplaceCategory]:
    if not CATEGORIES_HTML_PATH.exists():
        raise FileNotFoundError(f"File {CATEGORIES_HTML_PATH} not found")

    with open(CATEGORIES_HTML_PATH, "r") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")
    category_data_script = None
    for script in scripts:
        if "marketplace_ranked_categories" in script.text:
            category_data_script = script
            break

    if category_data_script is None:
        raise ValueError("Could not find category data script")

    json_start = category_data_script.text.find('{"marketplace_ranked_categories":')
    json_end = category_data_script.text.find('},"extensions":', json_start)
    if json_start == -1 or json_end == -1:
        raise ValueError("Could not find category JSON in category data script")

    raw_categories_json = category_data_script.text[json_start:json_end]
    categories_json = json.loads(raw_categories_json)
    categories_taxonomy = categories_json["marketplace_ranked_categories"][
        "categories_virtual_taxonomy"
    ]

    categories: list[MarketplaceCategory] = []

    def parse_category(category_json: dict, parent_id: str | None = None) -> None:
        try:
            category = MarketplaceCategory(
                id=category_json["id"],
                name=category_json["name"],
                seo_url=(
                    category_json["seo_info"]["seo_url"] if category_json.get("seo_info") else None
                ),
                parent_id=parent_id,
            )
            categories.append(category)

            children = category_json.get("other_children_categories", []) + category_json.get(
                "virtual_category_ordered_children", []
            )
        except Exception:
            _logger.error("Error parsing category %s", category_json)
            raise

        for child in children:
            parse_category(child, category.id)

    for category in categories_taxonomy:
        parse_category(category)

    return categories


def has_category(category: str) -> bool:
    return any(c.id == category or c.seo_url == category for c in get_categories())
