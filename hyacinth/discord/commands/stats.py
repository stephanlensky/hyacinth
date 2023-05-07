from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Message

from hyacinth.notifier import ChannelNotifier

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot


async def global_stats(bot: DiscordNotifierBot, message: Message) -> None:
    def get_notifier_repr(notifier: ChannelNotifier) -> str:
        paused = "(paused) " if notifier.config.paused else ""
        return (
            f"{paused}#{getattr(notifier.channel, 'name', notifier.channel.id)} -"
            f" {len(notifier.config.active_searches)} searches"
        )

    notifiers_repr = "\n".join(get_notifier_repr(n) for n in bot.notifiers.values())
    notifiers_part = (
        f"{bot.affirm()} {message.author.mention}, there are currently {len(bot.notifiers)} channel"
        f" notifiers.\n```{notifiers_repr}```"
    )

    monitor_searches_repr = "\n".join(
        f"spec={s}, refs={r}" for s, r in bot.monitor.search_spec_ref_count.items()
    )
    monitors_part = (
        "The monitor is currently polling"
        f" {len(bot.monitor.search_spec_job_mapping)} searches.\n```{monitor_searches_repr}```"
    )

    await message.channel.send(
        "\n".join(
            (
                notifiers_part,
                monitors_part,
            )
        )
    )


async def channel_stats(bot: DiscordNotifierBot, message: Message, channel_id: int) -> None:
    if channel_id not in bot.notifiers:
        await message.channel.send(
            f"Sorry {message.author.mention}, there is no notifier configured for the given"
            " channel."
        )
        return

    notifier = bot.notifiers[channel_id]
    searches = notifier.config.active_searches
    searches_repr = "\n".join(
        f"spec={search.spec}, last_notified={search.last_notified}" for search in searches
    )
    searches_part = (
        f"{bot.affirm()} {message.author.mention}, there are {len(searches)} active searches for"
        f" this channel.\n```{searches_repr}```"
    )

    await message.channel.send(searches_part)


async def stats(bot: DiscordNotifierBot, message: Message, channel_id: int | None) -> None:
    if channel_id is not None:
        await channel_stats(bot, message, channel_id)
    else:
        await global_stats(bot, message)
