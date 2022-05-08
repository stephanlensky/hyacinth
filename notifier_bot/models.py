from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from boolean import Expression
from pydantic import BaseModel, Field


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
    price: float
    location: Location
    distance_miles: float
    created_at: datetime
    updated_at: datetime


class SearchSpecSource(str, Enum):
    CRAIGSLIST = "craigslist"


class SearchParams(HashableBaseModel):
    pass


class SearchSpec(HashableBaseModel):
    source: SearchSpecSource
    search_params: SearchParams

    @classmethod
    def parse_obj(cls, obj: dict[str, Any]) -> SearchSpec:
        source = obj["source"]
        search_params = obj["search_params"]
        if source == SearchSpecSource.CRAIGSLIST:
            # pylint: disable=import-outside-toplevel
            from notifier_bot.sources.craigslist import CraigslistSearchParams

            return SearchSpec(
                source=source, search_params=CraigslistSearchParams.parse_obj(search_params)
            )

        raise NotImplementedError(f"{source} not implemented")


class FilterRules(BaseModel):
    rules: list[tuple[str, Expression]] = []  # list of tuples (original user rule str, Expression)
    preremoval_rules: list[str] = []  # remove these words before applying rules
    disallowed_words: list[str] = []  # auto fail any listing with these words

    class Config:
        arbitrary_types_allowed = True
