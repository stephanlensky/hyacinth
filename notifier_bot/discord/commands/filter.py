from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Type

from discord import Message

from notifier_bot.models import Listing, Rule, StringFieldFilter
from notifier_bot.notifier import ListingNotifier
from notifier_bot.util.boolean_rule_algebra import parse_rule

if TYPE_CHECKING:
    from notifier_bot.discord.discord_bot import DiscordNotifierBot


_logger = logging.getLogger(__name__)

INCLUDE_COMMAND = r"(include|add) (?P<rule>.+)"
EXCLUDE_COMMAND = r"(exclude|not) (?P<disallowed>.+)"
PREREMOVE_COMMAND = r"(preremove) (?P<preremove>.+)"


async def filter_(
    bot: DiscordNotifierBot,
    message: Message,
    notifier: ListingNotifier,
    field: str,
    filter_command: str,
) -> None:
    _logger.debug(f"Using field {field} for command {filter_command}")
    if field not in notifier.config.filters:
        notifier.config.filters[field] = make_filter(Listing, field)
    field_filter = notifier.config.filters[field]

    if isinstance(field_filter, StringFieldFilter):
        await _handle_string_filter_command(bot, message, field_filter, filter_command)
    else:
        raise NotImplementedError("filter type not implemented")


def make_filter(listing_cls: Type[Listing], field: str) -> StringFieldFilter:
    if field not in listing_cls.__fields__:
        raise ValueError(f"Given field does not exist on {listing_cls}")

    field_type = listing_cls.__fields__[field].type_
    if field_type is str:
        return StringFieldFilter()

    raise NotImplementedError(f"Filters not implemented for field of type {field_type}")


def is_valid_string_filter_command(filter_command: str) -> bool:
    return any(
        map(
            lambda p: re.match(p, filter_command),
            (INCLUDE_COMMAND, EXCLUDE_COMMAND, PREREMOVE_COMMAND),
        )
    )


async def _handle_string_filter_command(
    bot: DiscordNotifierBot, message: Message, field_filter: StringFieldFilter, filter_command: str
) -> None:
    if command := re.match(INCLUDE_COMMAND, filter_command):
        rule = command.group("rule")
        expression = parse_rule(rule)
        field_filter.rules.append(Rule(rule_str=rule))
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I've added the following"
            f" rule:\n```{repr(expression)}```"
        )
    elif command := re.match(EXCLUDE_COMMAND, filter_command):
        disallowed = command.group("disallowed")
        field_filter.disallowed_words.append(disallowed)
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I won't notify you about any listings that"
            f" include the following word:\n```{disallowed}```"
        )
    elif command := re.match(PREREMOVE_COMMAND, filter_command):
        preremove = command.group("preremove")
        field_filter.preremoval_rules.append(preremove)
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I've added the following"
            f" preremoval rule:\n```{preremove}```"
        )
