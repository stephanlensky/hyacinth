import asyncio

from notifier_bot.discord import discord_bot


def run_discord_bot() -> None:
    asyncio.run(discord_bot.run())
