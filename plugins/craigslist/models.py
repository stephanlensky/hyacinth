from datetime import datetime

from pydantic import BaseModel, Field

from hyacinth.models import BaseListing, BaseSearchParams


class CraigslistListing(BaseListing):
    title: str
    url: str
    body: str
    image_urls: list[str]
    thumbnail_url: str | None = None
    price: float
    city: str | None
    state: str | None
    latitude: float | None
    longitude: float | None
    distance_miles: float | None = None
    updated_time: datetime


class CraigslistArea(BaseModel):
    site: str
    nearby_areas: list[str]


class CraigslistSite(BaseModel):
    hostname: str = Field(alias="Hostname")
    latitude: float = Field(alias="Latitude")
    longitude: float = Field(alias="Longitude")


class CraigslistSearchParams(BaseSearchParams):
    site: str
    nearby_areas: list[str] | None = None
    category: str

    def __hash__(self) -> int:  # make hashable to enable use with @cache
        return hash((type(self),) + tuple(self.__dict__.values()))
