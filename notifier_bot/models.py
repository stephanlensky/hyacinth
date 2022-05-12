from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from boolean import Expression
from pydantic import BaseModel, Field, PrivateAttr
from pydantic.generics import GenericModel

from notifier_bot.util.boolean_rule_algebra import apply_rules, parse_rule

T = TypeVar("T")


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


class Rule(BaseModel):
    rule_str: str
    _expression: Expression = PrivateAttr()

    @property
    def expression(self) -> Expression:
        return self._expression

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)
        self._expression = parse_rule(self.rule_str)


class ListingFieldFilter(ABC, GenericModel, Generic[T]):
    @abstractmethod
    def test(self, listing_field: T) -> bool:
        pass


class StringFieldFilter(ListingFieldFilter[str]):
    rules: list[Rule] = []
    preremoval_rules: list[str] = []  # remove these words before applying rules
    disallowed_words: list[str] = []  # auto fail any listing with these words

    def test(self, listing_field: str) -> bool:
        for preremoval_rule in self.preremoval_rules:
            listing_field = listing_field.replace(preremoval_rule, "")

        for disallowed_word in self.disallowed_words:
            if disallowed_word in listing_field:
                return False

        return apply_rules(self.rules, listing_field)
