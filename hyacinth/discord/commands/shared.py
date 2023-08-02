from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from hyacinth.notifier import ChannelNotifier

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot


async def get_notifier(bot: DiscordBot, interaction: discord.Interaction) -> ChannelNotifier | None:
    if interaction.channel is None:
        raise ValueError("Interaction channel is None")

    # check if a notifier exists for this channel
    notifier = bot.notifiers.get(interaction.channel.id)
    if not notifier:
        await interaction.response.send_message(
            (
                f"Sorry {interaction.user.mention}, this channel is not configured to send"
                " notifications. Try creating a new search with `/search add`."
            ),
            ephemeral=True,
        )
        return None

    return notifier
