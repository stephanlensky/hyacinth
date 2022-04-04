from datetime import datetime

from pydantic import BaseModel, Field


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
