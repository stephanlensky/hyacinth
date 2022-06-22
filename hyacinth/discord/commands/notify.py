from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Message

from hyacinth.discord.notifier_setup import CraigslistNotifierSetupInteraction
from hyacinth.models import SearchSpecSource

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot


async def create_notifier(
    bot: DiscordNotifierBot, message: Message, source_name: str, params: dict[str, str] | None
) -> None:
    try:
        source = SearchSpecSource(source_name)
    except ValueError:
        await message.channel.send(
            f'Sorry {message.author.mention}, "{source_name}" is not a source I support sending'
            " notifications for."
        )
        return

    if source == SearchSpecSource.CRAIGSLIST:
        setup_interaction = CraigslistNotifierSetupInteraction(bot, message)
    else:
        raise NotImplementedError(f"{source_name} not implemented")

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
