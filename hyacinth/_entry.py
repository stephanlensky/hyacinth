import asyncio

from hyacinth.discord import discord_bot
from hyacinth.metrics import flush_buffer as flush_metrics_buffer


def run_discord_bot() -> None:
    try:
        asyncio.run(discord_bot.start())
    except KeyboardInterrupt:
        pass
    finally:
        flush_metrics_buffer()
