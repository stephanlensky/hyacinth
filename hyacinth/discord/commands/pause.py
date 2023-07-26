from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from hyacinth.discord.commands.shared import get_notifier

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot

_logger = logging.getLogger(__name__)


async def pause(
    bot: DiscordBot,
    interaction: discord.Interaction,
) -> None:
    notifier = await get_notifier(bot, interaction)
    if not notifier:
        return

    _logger.debug(f"Received /pause command, current state is: {notifier.config.paused}")
    notifier.set_paused(not notifier.config.paused)
    await interaction.response.send_message(
        (
            f"{bot.affirm()} {interaction.user.mention}, I've"
            f" {'paused' if notifier.config.paused else 'unpaused'} notifications for this channel."
        ),
        ephemeral=True,
    )
