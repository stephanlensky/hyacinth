from abc import ABC, abstractmethod
from typing import Annotated, Any, Generic, Literal, Type, TypeVar

from boolean import Expression
from pydantic import BaseModel, Field, PrivateAttr
from pydantic.generics import GenericModel

from notifier_bot.util.boolean_rule_algebra import apply_rules, parse_rule

T = TypeVar("T")
Number = int | float


class ListingFieldFilter(ABC, GenericModel, Generic[T]):
    @abstractmethod
    def test(self, listing_field: T) -> bool:
        pass


class Rule(BaseModel):
    rule_str: str
    _expression: Expression = PrivateAttr()

    @property
    def expression(self) -> Expression:
        return self._expression

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._expression = parse_rule(self.rule_str)


class StringFieldFilter(ListingFieldFilter[str]):
    filter_type: Literal["string"] = "string"
    rules: list[Rule] = []
    preremoval_rules: list[str] = []  # remove these words before applying rules
    disallowed_words: list[str] = []  # auto fail any listing with these words

    def test(self, listing_field: str) -> bool:
        listing_field = listing_field.lower()

        for preremoval_rule in self.preremoval_rules:
            listing_field = listing_field.replace(preremoval_rule, "")

        for disallowed_word in self.disallowed_words:
            if disallowed_word in listing_field:
                return False

        return apply_rules(self.rules, listing_field)


class NumericFieldFilter(ListingFieldFilter[Number]):
    filter_type: Literal["numeric"] = "numeric"
    min: Number | None = None
    max: Number | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True

    def test(self, listing_field: Number) -> bool:
        min_test = self.min is None or (
            listing_field >= self.min if self.min_inclusive else listing_field > self.min
        )
        max_test = self.max is None or (
            listing_field <= self.max if self.max_inclusive else listing_field < self.max
        )
        return min_test and max_test


Filter = Annotated[StringFieldFilter | NumericFieldFilter, Field(discriminator="filter_type")]
filter_type_mapping: dict[Type, Type[Filter]] = {
    str: StringFieldFilter,
    int: NumericFieldFilter,
    float: NumericFieldFilter,
}


def make_filter(cls: Type[BaseModel], field: str) -> Filter:
    if field not in cls.__fields__:
        raise ValueError(f"Given field does not exist on {cls}")

    field_type = cls.__fields__[field].type_
    if field_type not in filter_type_mapping:
        raise NotImplementedError(f"Filters not implemented for field of type {field_type}")

    return filter_type_mapping[field_type]()
