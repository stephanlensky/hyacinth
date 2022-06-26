from typing import Any

from pydantic import BaseModel, Field, validator

from hyacinth.models import SearchParams


class CraigslistArea(BaseModel):
    site: str
    nearby_areas: list[str]


class CraigslistSite(BaseModel):
    hostname: str = Field(alias="Hostname")
    latitude: float = Field(alias="Latitude")
    longitude: float = Field(alias="Longitude")


class CraigslistSearchParams(SearchParams):
    site: str
    nearby_areas: tuple[str, ...]
    category: str

    @validator("nearby_areas", pre=True)
    @classmethod
    def nearby_areas_list_to_tuple(cls, v: Any) -> tuple:
        return tuple(v)
