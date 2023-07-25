from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from hyacinth.discord.commands.shared import get_notifier
from hyacinth.plugin import get_plugin

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot

_logger = logging.getLogger(__name__)


async def show(
    bot: DiscordBot,
    interaction: discord.Interaction,
) -> None:
    notifier = await get_notifier(bot, interaction)
    if not notifier:
        return

    active_searches = "\n".join(
        [
            f"- {get_plugin(s.search_spec.plugin_path).display_name} -"
            f" {s.name}\n```json\n{s.search_spec.search_params_json}```"
            for s in notifier.config.active_searches
        ]
    )
    filters = (
        "\n".join(
            [f"- `{f.rule_type.name} {f.field}: {f.rule_expr}`" for f in notifier.config.filters]
        )
        if notifier.config.filters
        else "No filters set. Try using `/filter add` to create one."
    )
    notifier_details = f"""
    The notifier on this channel is currently {'paused' if notifier.config.paused else 'active and ready to send notifications'}.

**Active searches:**
{active_searches}
**Filters:**
{filters}
"""

    await interaction.response.send_message(
        notifier_details,
        ephemeral=True,
    )
