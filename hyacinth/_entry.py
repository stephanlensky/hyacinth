import asyncio

from hyacinth.discord import discord_bot


def run_discord_bot() -> None:
    try:
        asyncio.run(discord_bot.start())
    except KeyboardInterrupt:
        pass
