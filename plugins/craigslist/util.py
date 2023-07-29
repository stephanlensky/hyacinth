import json
import logging
import os
import re
from functools import cache
from pathlib import Path

from pydantic import TypeAdapter

from plugins.craigslist.models import CraigslistSite

_logger = logging.getLogger(__name__)
AREAS_REFERENCE_JSON_PATH = Path(os.path.realpath(__file__)).parent / "craigslist_areas.json"


@cache
def get_areas_reference(
    areas_json_path: Path = AREAS_REFERENCE_JSON_PATH,
) -> dict[str, CraigslistSite]:
    if not areas_json_path.exists():
        raise FileNotFoundError(areas_json_path)

    _logger.info(f"Reading Craigslist Areas reference from {areas_json_path}")
    with areas_json_path.open(encoding="utf-8") as areas_json_file:
        areas_json = json.load(areas_json_file)

    sites = TypeAdapter(list[CraigslistSite]).validate_python(areas_json)
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
