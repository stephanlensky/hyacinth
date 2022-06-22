from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Member, Message, User

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot

FMT_USER = "{user}"

GENERAL_HELP = (
    f"""Hi {FMT_USER}! I have not written the copy for this command yet :). Lorem ipsum etc."""
)


def _format(message: str, *, user: User | Member) -> str:
    return message.format_map({FMT_USER[1:-1]: user.mention})


async def show_help(_bot: DiscordNotifierBot, message: Message, command: str | None) -> None:
    if command is None:
        await message.channel.send(_format(GENERAL_HELP, user=message.author))
