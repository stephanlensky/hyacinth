from __future__ import annotations

import ast
import logging
import re
from typing import TYPE_CHECKING

from discord import Message

from hyacinth.filters import NumericFieldFilter, Rule, StringFieldFilter, make_filter
from hyacinth.models import Listing
from hyacinth.notifier import ListingNotifier
from hyacinth.util.boolean_rule_algebra import parse_rule

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot


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
    elif isinstance(field_filter, NumericFieldFilter):
        await _handle_numeric_filter_command(bot, message, field, field_filter, filter_command)
    else:
        raise NotImplementedError("filter type not implemented")


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
        rule = command.group("rule").lower()
        expression = parse_rule(rule)
        field_filter.rules.append(Rule(rule_str=rule))
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I've added the following"
            f" rule:\n```{repr(expression)}```"
        )
    elif command := re.match(EXCLUDE_COMMAND, filter_command):
        disallowed = command.group("disallowed").lower()
        field_filter.disallowed_words.append(disallowed)
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I won't notify you about any listings that"
            f" include the following word:\n```{disallowed}```"
        )
    elif command := re.match(PREREMOVE_COMMAND, filter_command):
        preremove = command.group("preremove").lower()
        field_filter.preremoval_rules.append(preremove)
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I've added the following"
            f" preremoval rule:\n```{preremove}```"
        )


async def _handle_numeric_filter_command(
    bot: DiscordNotifierBot,
    message: Message,
    field: str,
    field_filter: NumericFieldFilter,
    filter_command: str,
) -> None:
    command = re.match(r"(?P<operator><|<=|>|>=)\s*(?P<operand>\d+(\.\d+)?)", filter_command)
    if command is None:
        await message.channel.send(f"Sorry {message.author.mention}, I didn't understand that.")
        return

    operator_str: str = command.group("operator")
    operand_str: str = command.group("operand")

    operand = ast.literal_eval(operand_str)
    if not isinstance(operand, (float, int)):
        await message.channel.send(f"Sorry {message.author.mention}, I didn't understand that.")

    if ">" in operator_str:
        field_filter.min = operand
        field_filter.min_inclusive = "=" in operator_str
    elif "<" in operator_str:
        field_filter.max = operand
        field_filter.max_inclusive = "=" in operator_str

    await message.channel.send(
        f"{bot.affirm()} {message.author.mention}, I'll only notify you of listings where"
        f" `{field} {operator_str} {operand}`."
    )
