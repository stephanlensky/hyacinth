import json
import logging
import re
from functools import cache
from pathlib import Path

import httpx
from pydantic import parse_obj_as

from hyacinth.settings import get_settings
from plugins.craigslist.models import CraigslistSite

settings = get_settings()
_logger = logging.getLogger(__name__)


@cache
def get_areas_reference(
    areas_json_path: Path = settings.craigslist_areas_reference_json_path,
) -> dict[str, CraigslistSite]:
    if areas_json_path.exists():
        _logger.info(f"Reading Craigslist Areas reference from {areas_json_path}")
        with areas_json_path.open(encoding="utf-8") as areas_json_file:
            areas_json = json.load(areas_json_file)
    else:
        _logger.info("Fetching Craigslist Areas reference from reference.craigslist.org")
        r = httpx.get("https://reference.craigslist.org/Areas")
        areas_json = r.json()

    sites = parse_obj_as(list[CraigslistSite], areas_json)
    areas_reference = {s.hostname: s for s in sites}
    _logger.info("Loaded Craigslist Areas reference")

    return areas_reference


def get_geotag_from_url(url: str) -> tuple[float, float]:
    match = re.match(r"http(s)?://(www\.)?(.+)\.craigslist", url)
    if match is None:
        raise ValueError(url)
    site = match.groups()[2]
    areas_reference = get_areas_reference()
    return (
        areas_reference[site].latitude,
        areas_reference[site].longitude,
    )
