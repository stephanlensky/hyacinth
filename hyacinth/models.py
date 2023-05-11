from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from pydantic import BaseModel, root_validator

from hyacinth.db.models import Listing

if TYPE_CHECKING:
    from hyacinth.plugin import Plugin


class DiscordMessage(BaseModel):
    content: str | None = None
    embed: discord.Embed | None = None

    @root_validator(pre=True)
    @classmethod
    def ensure_content(cls, values: dict[str, Any]) -> dict[str, Any]:
        content, embed = values.get("content"), values.get("embed")
        if content is None and embed is None:
            raise ValueError("at least one of content or embed must be provided")

        return values

    class Config:
        arbitrary_types_allowed = True


class Location(BaseModel):
    city: str | None
    state: str | None
    latitude: float
    longitude: float


class BaseListing(BaseModel):
    creation_time: datetime


@dataclass
class ListingMetadata:
    listing: Listing
    plugin: Plugin


class BaseSearchParams(BaseModel):
    pass
