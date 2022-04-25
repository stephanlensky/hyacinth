from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any, Callable, Pattern

import discord
import wrapt
from discord import Message, Thread

from notifier_bot.discord.notifier_setup import CraigslistSetupHandler, ThreadBasedSetupHandler
from notifier_bot.models import SearchSpecSource
from notifier_bot.monitor import MarketplaceMonitor
from notifier_bot.notifier import DiscordNotifier
from notifier_bot.settings import get_settings
from notifier_bot.util.craigslist import get_areas

settings = get_settings()
_logger = logging.getLogger(__name__)

_discord_notifier_bot_commands: dict[Pattern, Callable] = {}

AFFIRMATIONS = ["Okay", "Sure", "Sounds good", "No problem", "Roger that", "Got it"]
DEBUG_COMMAND_PREFIX = r"(d|debug) "


class DiscordNotifierBot:
    def __init__(
        self,
        client: discord.Client,
        command_prefix: str | None = "$",
    ) -> None:

        self.client = client
        self.command_prefix = command_prefix

        self.monitor = MarketplaceMonitor()
        self.notifiers: dict[int, DiscordNotifier] = {}  # channel ID -> notifier
        self.active_threads: dict[int, ThreadBasedSetupHandler] = {}  # thread ID -> setup handler

    def get_command_from_message(self, message: Message) -> str | None:
        """
        Get the bot command string from a raw Discord message.

        If the message is not a bot command, return None.
        """
        # all mentions are automatically interpreted as commands
        if self.client.user is not None and self.client.user.mentioned_in(message):
            mention_regex = rf"<@!?{self.client.user.id}>"
            command = re.sub(mention_regex, "", message.content, 1).strip()
            return command

        # alternatively, commands can be prefixed with a string to indicate they are for the bot
        elif self.command_prefix is not None and message.content.startswith(self.command_prefix):
            command = message.content[len(self.command_prefix) :].strip()
            return command

        return None

    async def on_message(self, message: Message) -> None:
        _logger.debug(f"Received message: {message}")
        # if this bot sent the message, never do anything
        if message.author == self.client.user:
            return

        # if the message is in a thread with an ongoing setup process, pass it to the setup handler
        if isinstance(message.channel, Thread) and message.channel.id in self.active_threads:
            handler = self.active_threads[message.channel.id]
            await handler.on_message(message)
            if handler.is_complete():
                _logger.debug(f"Completed handler on thread {message.channel.id}")
                self.active_threads.pop(message.channel.id)
            return

        # otherwise check if the message is a command and pass it to the appropriate command handler
        command = self.get_command_from_message(message)
        if command is None:
            return

        _logger.info(f"Received command: {command}")
        for pattern in _discord_notifier_bot_commands:
            match = pattern.match(command)
            if match:
                await _discord_notifier_bot_commands[pattern](self, message, match)
                break

    @staticmethod
    def command(r: str) -> Callable[..., Any]:
        """
        Helper decorator for defining bot commands matching a given regex.

        After receiving a command, the bot will call the first @command function whose regex
        matches the given command.
        """

        def deco(f: Callable[..., Any]) -> Callable[..., Any]:
            @wrapt.decorator
            def wrapper(
                wrapped: Callable[..., Any], _instance: Any, args: list, kwargs: dict
            ) -> Any:
                return wrapped(*args, **kwargs)

            _discord_notifier_bot_commands[re.compile(r, re.IGNORECASE)] = f

            return wrapper

        return deco

    def affirmation(self) -> str:
        return random.choice(AFFIRMATIONS)

    @command(r"notify (?P<source_name>.+)")
    async def create_notifier(self, message: Message, command: re.Match) -> None:
        source_name: str = command.group("source_name").lower()
        _logger.info(f"Received request to create notifier from source={source_name}")
        try:
            source = SearchSpecSource(source_name)
        except ValueError:
            await message.channel.send(
                f'Sorry {message.author.mention}, "{source_name}" is not a source I support sending'
                " notifications for."
            )
            return

        thread = await message.create_thread(
            name=f"Create a new {source.capitalize()} notifier", auto_archive_duration=60
        )
        notifier_setup_handler = CraigslistSetupHandler(
            self,
            message.channel,
            thread,
            message.author,
            self.notifiers.get(message.channel.id, None),
        )
        self.active_threads[thread.id] = notifier_setup_handler
        await notifier_setup_handler.send_first_message()

    @command(
        rf"{DEBUG_COMMAND_PREFIX}notify-with-params (?P<source_name>.+?) (?P<params>(\w+=\w+ ?)+)"
    )
    async def debug_create_notifier_from_params(self, message: Message, command: re.Match) -> None:
        source_name: str = command.group("source_name").lower()
        params: dict[str, str] = dict((p.split("=") for p in command.group("params").split(" ")))
        _logger.info(f"Creating notifier from params source={source_name} params={params}")
        notifier_setup_handler = CraigslistSetupHandler(
            self,
            message.channel,
            None,  # type: ignore
            message.author,
            self.notifiers.get(message.channel.id, None),
        )
        notifier_setup_handler.area = get_areas()[list(get_areas())[int(params["area"])]]
        notifier_setup_handler.category = params["category"]
        notifier_setup_handler.min_price = int(params["min_price"])
        notifier_setup_handler.max_price = int(params["max_price"])
        notifier_setup_handler.max_distance_miles = int(params["max_distance_miles"])
        notifier_setup_handler.create_search()

        await message.channel.send(
            f"```Created notifier from params source={source_name} params={params}```"
        )


def run() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    intents = discord.Intents(messages=True, guild_messages=True, message_content=True, guilds=True)
    client = discord.Client(intents=intents, loop=loop)
    discord_bot: DiscordNotifierBot = DiscordNotifierBot(client)

    @client.event
    async def on_ready() -> None:
        _logger.info(f"We have logged in as {client.user}")

    @client.event
    async def on_message(message: Message) -> None:
        await discord_bot.on_message(message)

    client.run(settings.discord_token)
