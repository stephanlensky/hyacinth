from geopy.distance import geodesic
from geopy.geocoders import GoogleV3

from notifier_bot.models import Location
from notifier_bot.settings import get_settings

settings = get_settings()
geolocator = GoogleV3(api_key=settings.google_geocoding_api_key)


def distance_miles(from_location: tuple[float, float], to_location: tuple[float, float]) -> float:
    return geodesic(from_location, to_location).miles


def reverse_geotag(geotag: tuple[float, float]) -> Location:
    location = geolocator.reverse(geotag)
    address_components = location.raw["address_components"]
    city_component = next(
        filter(
            lambda c: "locality" in c["types"] or "sublocality" in c["types"], address_components
        ),
        None,
    )
    state_component = next(
        filter(lambda c: "administrative_area_level_1" in c["types"], address_components), None
    )
    return Location(
        city=city_component["long_name"] if city_component else None,
        state=state_component["long_name"] if state_component else None,
        latitude=geotag[0],
        longitude=geotag[1],
    )
