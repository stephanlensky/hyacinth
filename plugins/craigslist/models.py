from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator

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
    latitude: float
    longitude: float
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
    nearby_areas: tuple[str, ...]
    category: str

    @validator("nearby_areas", pre=True)
    @classmethod
    def nearby_areas_list_to_tuple(cls, v: Any) -> tuple:
        return tuple(v)
