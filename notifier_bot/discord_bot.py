import asyncio
import logging
import re
from asyncio import AbstractEventLoop

import discord
from discord import Message

from notifier_bot.monitor import MarketplaceMonitor
from notifier_bot.notifier import LoggerNotifier
from notifier_bot.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)


class DiscordNotifierBot:
    def __init__(
        self,
        client: discord.Client,
        command_prefix: str = "$",
        loop: AbstractEventLoop | None = None,
    ) -> None:
        if loop is None:
            loop = asyncio.get_running_loop()

        self.client = client
        self.command_prefix = command_prefix
        self.loop = loop
        self.monitor = MarketplaceMonitor(self.loop)
        self.notifiers: list[LoggerNotifier] = []

    def on_message(self, message: Message) -> None:
        if message.author == self.client.user:
            return
        if self.client.user.mentioned_in(message):
            mention_regex = rf"<@!?{self.client.user.id}>"
            message.content = re.sub(mention_regex, "", message.content, 1).strip()
        elif message.content.startswith(self.command_prefix):
            message.content = message.content[len(self.command_prefix) :].strip()
        else:
            return  # this is not a bot command
        _logger.info(f"Received command: {message.content}")


def run() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop)
    discord_bot: DiscordNotifierBot = DiscordNotifierBot(client, loop=loop)

    @client.event
    async def on_ready() -> None:
        _logger.info("We have logged in as {client.user}")

    @client.event
    async def on_message(message: Message) -> None:
        discord_bot.on_message(message)

    client.run(settings.discord_token)
