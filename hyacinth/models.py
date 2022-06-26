from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from pydantic import BaseModel, PrivateAttr, root_validator

from hyacinth.exceptions import MissingPluginError

if TYPE_CHECKING:
    from hyacinth.plugin import Plugin


class HashableBaseModel(BaseModel):
    def __hash__(self) -> int:
        return hash((type(self),) + tuple(self.__dict__.values()))

    class Config:
        allow_mutation = False


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


@dataclass
class ListingMetadata:
    listing: Listing
    plugin: Plugin


class SearchParams(HashableBaseModel):
    pass


class SearchSpec(HashableBaseModel):
    _plugin: Plugin | None = PrivateAttr(default=None)
    plugin_path: str
    search_params: SearchParams

    @property
    def plugin(self) -> Plugin:
        if self._plugin is None:
            # pylint: disable=import-outside-toplevel
            from hyacinth.plugin import get_plugin

            self._plugin = get_plugin(self.plugin_path)

        return self._plugin

    @root_validator(pre=True)
    @classmethod
    def parse_search_params(cls, values: dict[str, Any]) -> dict[str, Any]:
        # pylint: disable=import-outside-toplevel
        from hyacinth.plugin import get_plugin

        plugin = get_plugin(values["plugin_path"])
        if plugin is None:
            raise MissingPluginError(values["plugin_path"])

        values["search_params"] = plugin.search_param_cls.parse_obj(values["search_params"])
        return values
