from __future__ import annotations

import logging
from functools import cache
from pathlib import Path
from typing import NamedTuple

import geopandas as gpd
import pandas as pd
from geopandas import GeoDataFrame
from geopy.distance import geodesic
from geopy.geocoders import GoogleV3
from scipy.spatial import KDTree

from hyacinth.models import Location
from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)

GADM_USA_GPKG_PATH = Path("geography/gadm36_USA.gpkg")
GEONAMES_CITIES_PATH = Path("geography/cities1000.txt")


@cache
def get_google_geolocator() -> GoogleV3:
    if not settings.google_geocoding_api_key:
        raise ValueError(
            "To use the Google geolocator, please specify a Google API key using the"
            " HYACINTH_GOOGLE_GEOCODING_API_KEY environment variable"
        )
    return GoogleV3(api_key=settings.google_geocoding_api_key)


def distance_miles(from_location: tuple[float, float], to_location: tuple[float, float]) -> float:
    return geodesic(from_location, to_location).miles


def reverse_geotag(geotag: tuple[float, float]) -> Location:
    if settings.use_local_geocoder:
        return _reverse_geotag_local(geotag)
    return _reverse_geotag_google(geotag)


def _reverse_geotag_google(geotag: tuple[float, float]) -> Location:
    geolocator = get_google_geolocator()
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


class LocalReverseGeocoder:
    """
    Rough implementation of a reverse geocoder using only freely available geospatial data.

    The "reverse" method accepts a lat/long coordinate and attempts to return a 3-pair of a country,
    primary administrative zone (e.g. state), and city. Currently, only locations within the US are
    supported.
    """

    class ReverseGeocodeResult(NamedTuple):
        country: str | None
        primary_adminstrative_zone: str | None
        city: str | None

    def __init__(self) -> None:
        _logger.info("Loading geospatial datasets...")
        self.ensure_geospatial_datasets_downloaded()
        self.gadm_primary_subdivision_datasets: dict[str, GeoDataFrame] = {
            "US": gpd.read_file(GADM_USA_GPKG_PATH, layer="gadm36_USA_1")
        }
        self.geonames_cities_dataset = pd.read_csv(
            GEONAMES_CITIES_PATH,
            sep="\t",
            usecols=[1, 4, 5, 8, 10],
            names=["name", "latitude", "longitude", "country", "admin1"],
        )

        _logger.info("Creating indexes...")
        self.primary_subdivisions_by_country: dict[str, pd.DataFrame] = {
            country: gadm_dataset.rename(columns={"NAME_1": "name", "HASC_1": "hasc"})
            for country, gadm_dataset in self.gadm_primary_subdivision_datasets.items()
        }
        self.cities_by_hasc: dict[str, pd.DataFrame] = {}
        for country in self.primary_subdivisions_by_country:
            for _, subdivision in self.primary_subdivisions_by_country[country].iterrows():
                subdivision_code = subdivision["hasc"].split(".")[-1]
                self.cities_by_hasc[subdivision["hasc"]] = self.geonames_cities_dataset[
                    (self.geonames_cities_dataset["country"] == country)
                    & (self.geonames_cities_dataset["admin1"] == subdivision_code)
                ]
        self.city_index_by_hasc = {
            hasc: KDTree(self.cities_by_hasc[hasc][["latitude", "longitude"]])
            for hasc in self.cities_by_hasc
        }
        _logger.info("Done!")

    def ensure_geospatial_datasets_downloaded(self) -> None:
        if not GADM_USA_GPKG_PATH.exists() or not GEONAMES_CITIES_PATH.exists():
            raise FileNotFoundError(
                "Could not find local geospatial data. Please download gadm36_USA.gpkg and"
                " cities1000.txt to use local geocoding."
            )

    def reverse(self, geotag: tuple[float, float]) -> LocalReverseGeocoder.ReverseGeocodeResult:
        geotag_df = gpd.points_from_xy(y=(geotag[0],), x=(geotag[1],))[0]
        country = "US"

        gadm_dataset = self.gadm_primary_subdivision_datasets[country]
        subdivision_index = gadm_dataset.sindex.query(geotag_df, predicate="within")
        if subdivision_index.size > 0:
            state = gadm_dataset.at[subdivision_index[0], "NAME_1"]
            hasc = gadm_dataset.at[subdivision_index[0], "HASC_1"]
        else:
            state = None
            hasc = None

        if hasc is not None:
            _nn_dist, nn_index = self.city_index_by_hasc[hasc].query([geotag])
            nearest_city = self.cities_by_hasc[hasc].iloc[nn_index[0]]["name"]
        else:
            nearest_city = None

        return LocalReverseGeocoder.ReverseGeocodeResult(
            country=country,
            primary_adminstrative_zone=state,
            city=nearest_city,
        )


@cache
def get_local_geolocator() -> LocalReverseGeocoder:
    return LocalReverseGeocoder()


def _reverse_geotag_local(geotag: tuple[float, float]) -> Location:
    geolocator = get_local_geolocator()
    result = geolocator.reverse(geotag)

    return Location(
        city=result.city,
        state=result.primary_adminstrative_zone,
        latitude=geotag[0],
        longitude=geotag[1],
    )
