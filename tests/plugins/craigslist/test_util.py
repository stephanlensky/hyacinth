from plugins.craigslist import util
from plugins.craigslist.models import CraigslistSite
from tests.resources import get_resource_path


def __validate_areas_reference(areas_reference: dict[str, CraigslistSite]) -> None:
    assert "boston" in areas_reference
    assert "worcester" in areas_reference


def test_get_areas_reference__from_disk() -> None:
    util.get_areas_reference.cache_clear()
    areas_reference_path = get_resource_path("areas_reference.json")
    areas_reference = util.get_areas_reference(areas_json_path=areas_reference_path)
    __validate_areas_reference(areas_reference)


def test_get_geotag_from_url__worcester() -> None:
    geotag = util.get_geotag_from_url(
        "https://worcester.craigslist.org/mcy/d/rochdale-2018-ninja-400/7466500248.html"
    )
    assert geotag[0] == 42.262501
    assert geotag[1] == -71.802803
