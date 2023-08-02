from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import discord

from hyacinth.discord.commands.shared import get_notifier
from hyacinth.notifier import ChannelNotifier

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot

_logger = logging.getLogger(__name__)
configurable_settings = ["notification_frequency", "home_location"]


async def configure(
    bot: DiscordBot,
    interaction: discord.Interaction,
    setting: str,
    value: str,
) -> None:
    notifier = await get_notifier(bot, interaction)
    if not notifier:
        return

    if setting == "notification_frequency":
        await _set_notification_frequency(bot, notifier, interaction, value)
    elif setting == "home_location":
        await _set_home_location(bot, notifier, interaction, value)
    else:
        await interaction.response.send_message(
            (
                f"Sorry {interaction.user.mention}, I don't know how to configure the setting"
                f" `{setting}`."
            ),
            ephemeral=True,
        )


async def _set_notification_frequency(
    bot: DiscordBot,
    notifier: ChannelNotifier,
    interaction: discord.Interaction,
    value: str,
) -> None:
    notification_frequency = await _validate_int(interaction, value)
    if notification_frequency is None:
        return

    notifier.set_notification_frequency(notification_frequency)
    await interaction.response.send_message(
        (
            f"{bot.affirm()} {interaction.user.mention}, I've set the notification frequency for"
            f" this channel to {notification_frequency} seconds."
        ),
        ephemeral=True,
    )


async def _set_home_location(
    bot: DiscordBot,
    notifier: ChannelNotifier,
    interaction: discord.Interaction,
    value: str,
) -> None:
    p = r"^\s*\(?(?P<latitude>-?\d+(?:\.\d+)?)\s*[, ]\s*(?P<longitude>-?\d+(?:\.\d+)?)\s*\)?\s*$"
    match = re.match(p, value)

    if match:
        latitude = float(match.group("latitude"))
        longitude = float(match.group("longitude"))
    else:
        return

    notifier.set_home_location((latitude, longitude))
    await interaction.response.send_message(
        (
            f"{bot.affirm()} {interaction.user.mention}, I've set the home location for"
            f" this channel to ({latitude}, {longitude})."
        ),
        ephemeral=True,
    )


async def _validate_int(interaction: discord.Interaction, value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        await interaction.response.send_message(
            (
                f"Sorry {interaction.user.mention}, this setting requires an integer value, not"
                f" {value}."
            ),
            ephemeral=True,
        )
        return None
