from notifier_bot.models import Location
from notifier_bot.util import geo


def test_reverse_geocode__reversable_geotag() -> None:
    geotag = (42.36052144409481, -71.05801368957714)  # boston city hall
    location = geo.reverse_geotag(geotag)
    assert location == Location(
        city="Boston", state="Massachusetts", latitude=geotag[0], longitude=geotag[1]
    )


def test_reverse_geocode__middle_of_the_ocean() -> None:
    geotag = (39.80490085251606, -39.47329574577306)  # atlantic ocean
    location = geo.reverse_geotag(geotag)
    assert location == Location(city=None, state=None, latitude=geotag[0], longitude=geotag[1])
