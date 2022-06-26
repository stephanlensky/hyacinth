from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Message

from hyacinth.discord.notifier_setup import NotifierSetupInteraction
from hyacinth.plugin import Plugin, get_plugins

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot


async def create_notifier(
    bot: DiscordNotifierBot, message: Message, plugin_name: str, params: dict[str, str] | None
) -> None:
    plugin: Plugin | None = None
    for p in get_plugins():
        if p.command_reference_name == plugin_name:
            plugin = p
            break

    if plugin is None:
        await message.channel.send(
            f'Sorry {message.author.mention}, "{plugin_name}" is not a source I support sending'
            " notifications for."
        )
        return

    setup_interaction = NotifierSetupInteraction(bot, message, plugin)

    if not params:
        await setup_interaction.begin()
        bot.active_threads[setup_interaction.thread_id] = setup_interaction
    else:
        setup_interaction.answers = params
        await setup_interaction.finish()
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I've created a search for you"
            f" based on following parameters:\n```{params}```"
        )
