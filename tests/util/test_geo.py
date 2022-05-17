from typing import Callable

from notifier_bot.models import Location


def test_reverse_geocode__reversable_geotag(
    reverse_geocode_function: Callable[[tuple[float, float]], Location]
) -> None:
    geotag = (42.36052144409481, -71.05801368957714)  # boston city hall
    location = reverse_geocode_function(geotag)
    assert location == Location(
        city="Boston", state="Massachusetts", latitude=geotag[0], longitude=geotag[1]
    )


def test_reverse_geocode__reversable_geotag_two(
    reverse_geocode_function: Callable[[tuple[float, float]], Location]
) -> None:
    geotag = (42.36560231017856, -72.53387976886876)  # hawkins meadow apartments, amherst ma
    location = reverse_geocode_function(geotag)
    assert location == Location(
        city="Amherst", state="Massachusetts", latitude=geotag[0], longitude=geotag[1]
    )


def test_reverse_geocode__middle_of_the_ocean(
    reverse_geocode_function: Callable[[tuple[float, float]], Location]
) -> None:
    geotag = (39.80490085251606, -39.47329574577306)  # atlantic ocean
    location = reverse_geocode_function(geotag)
    assert location == Location(city=None, state=None, latitude=geotag[0], longitude=geotag[1])
