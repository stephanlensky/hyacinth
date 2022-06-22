from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, root_validator


class HashableBaseModel(BaseModel):
    def __hash__(self) -> int:
        return hash((type(self),) + tuple(self.__dict__.values()))

    class Config:
        allow_mutation = False


class CraigslistArea(BaseModel):
    site: str
    nearby_areas: list[str]


class CraigslistSite(BaseModel):
    hostname: str = Field(alias="Hostname")
    latitude: float = Field(alias="Latitude")
    longitude: float = Field(alias="Longitude")


class Location(BaseModel):
    city: str | None
    state: str | None
    latitude: float
    longitude: float


class Listing(BaseModel):
    title: str
    url: str
    body: str
    image_urls: list[str]
    thumbnail_url: str | None = None
    price: float
    location: Location
    distance_miles: float | None = None
    created_at: datetime
    updated_at: datetime


class SearchSpecSource(str, Enum):
    CRAIGSLIST = "craigslist"


class SearchParams(HashableBaseModel):
    pass


class SearchSpec(HashableBaseModel):
    source: SearchSpecSource
    search_params: SearchParams

    @root_validator(pre=True)
    @classmethod
    def parse_search_params(cls, values: dict[str, Any]) -> dict[str, Any]:
        source = values["source"]
        search_params = values["search_params"]
        if source == SearchSpecSource.CRAIGSLIST:
            # pylint: disable=import-outside-toplevel
            from hyacinth.sources.craigslist import CraigslistSearchParams

            values["search_params"] = CraigslistSearchParams.parse_obj(search_params)
        else:
            raise NotImplementedError(f"{source} not implemented")

        return values
