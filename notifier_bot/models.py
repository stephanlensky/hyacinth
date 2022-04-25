from datetime import datetime
from enum import Enum
from typing import Any

from boolean import Expression
from pydantic import BaseModel, Field, validator


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


class SearchSpec(HashableBaseModel):
    source: SearchSpecSource
    # use a tuple of key-value pairs instead of a dict so the model can be hashed
    search_params: tuple[tuple[str, Any], ...]

    @validator("search_params", pre=True)
    @classmethod
    def search_param_dict_to_tuple(cls, v: Any) -> tuple:
        if isinstance(v, dict):
            sorted_items = sorted(v.items(), key=lambda i: i[0])
            return tuple(sorted_items)
        return v


class FilterRules(BaseModel):
    rules: list[tuple[str, Expression]] = []  # list of tuples (original user rule str, Expression)
    preremoval_rules: list[str] = []  # remove these words before applying rules
    disallowed_words: list[str] = []  # auto fail any listing with these words

    class Config:
        arbitrary_types_allowed = True
