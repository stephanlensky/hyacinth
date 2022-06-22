from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Message

from hyacinth.filters import NumericFieldFilter, StringFieldFilter
from hyacinth.notifier import ListingNotifier

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot


def _get_string_filter_repr(field: str, filter_: StringFieldFilter) -> str:
    field_filter_repr_parts = []
    if filter_.rules:
        rules_repr = "\n".join(
            f"{i+1}. {repr(rule.expression)}" for i, rule in enumerate(filter_.rules)
        )
        field_filter_repr_parts.append(
            f"The `{field}` field has the following boolean filter rules"
            f" enabled:\n```{rules_repr}```"
        )
    if filter_.preremoval_rules:
        preremoval_rules_repr = "\n".join(
            f"{i+1}. {preremoval_rule}"
            for i, preremoval_rule in enumerate(filter_.preremoval_rules)
        )
        field_filter_repr_parts.append(
            f"Before applying boolean filter rules to the `{field}` field, I will preremove"
            f" the following words:\n```{preremoval_rules_repr}```"
        )
    if filter_.disallowed_words:
        disallowed_words_repr = "\n".join(
            f"{i+1}. {word}" for i, word in enumerate(filter_.disallowed_words)
        )
        field_filter_repr_parts.append(
            f"If any of the following words appear in the `{field}` field, I will not"
            f" notify you of the listing:\n```{disallowed_words_repr}```"
        )

    return "\n".join(field_filter_repr_parts)


def _get_numeric_filter_repr(field: str, filter_: NumericFieldFilter) -> str:
    if filter_.min is None and filter_.max is None:
        return ""

    min_part = ""
    if filter_.min is not None:
        min_part = f">{'=' if filter_.min_inclusive else ''} {filter_.min}"
    max_part = ""
    if filter_.max is not None:
        max_part = f"<{'=' if filter_.max_inclusive else ''} {filter_.max}"
    parts = ", ".join(p for p in (min_part, max_part) if p)
    return f"The `{field}` field has the following filters enabled:\n```{parts}```"


async def show(
    bot: DiscordNotifierBot,
    message: Message,
    notifier: ListingNotifier,
) -> None:
    searches_repr = "\n".join(str(search.spec) for search in notifier.config.active_searches)
    num_searches = len(notifier.config.active_searches)
    searches_part_maybe_singular = (
        "there is 1 active search"
        if num_searches == 1
        else f"there are {num_searches} active searches"
    )
    searches_part = (
        f"{bot.affirm()} {message.author.mention}, {searches_part_maybe_singular} in this"
        f" channel.\n```{searches_repr}```"
    )

    filters_part = "\nThere are not currently any filters for notifications in this channel."
    if notifier.config.filters:
        filters_repr_parts = []
        for field, filter_ in notifier.config.filters.items():
            if isinstance(filter_, StringFieldFilter):
                filter_repr = _get_string_filter_repr(field, filter_)
            elif isinstance(filter_, NumericFieldFilter):
                filter_repr = _get_numeric_filter_repr(field, filter_)
            else:
                raise NotImplementedError(f"{type(filter_)} not implemented")

            if filter_repr:
                filters_repr_parts.append(filter_repr)

        if filters_repr_parts:
            filters_part = "\n" + "\n".join(filters_repr_parts)

    await message.channel.send(f"{searches_part}{filters_part}")
