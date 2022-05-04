import anyio

from notifier_bot.discord import discord_bot


def run_discord_bot() -> None:
    anyio.run(discord_bot.run)
