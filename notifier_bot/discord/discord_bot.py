from __future__ import annotations

import asyncio
import logging
import random
import re
import traceback
from typing import Any, Callable, Pattern

import discord
import wrapt
from discord import Message, Thread

from notifier_bot.db.notifier import get_discord_notifiers as get_discord_notifiers_from_db
from notifier_bot.db.notifier import save_discord_notifier as save_discord_notifier_to_db
from notifier_bot.discord.commands.filter import filter_, is_valid_string_filter_command
from notifier_bot.discord.commands.notify import create_notifier
from notifier_bot.discord.thread_interaction import ThreadInteraction
from notifier_bot.monitor import MarketplaceMonitor
from notifier_bot.notifier import DiscordNotifier, ListingNotifier
from notifier_bot.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)

_discord_notifier_bot_commands: dict[Pattern, Callable] = {}

AFFIRMATIONS = ["Okay", "Sure", "Sounds good", "No problem", "Roger that", "Got it"]
THANKS = [*AFFIRMATIONS, "Thanks", "Thank you"]
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
        self.active_threads: dict[int, ThreadInteraction] = {}  # thread ID -> setup handler

    def load_saved_notifiers(self) -> None:
        notifiers = get_discord_notifiers_from_db(self.client, self.monitor)
        for notifier in notifiers:
            self.notifiers[notifier.channel.id] = notifier
        _logger.info(f"Loaded {len(notifiers)} saved notifiers from the database!")

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
        # if this bot sent the message, never do anything
        if message.author == self.client.user:
            return

        # if the message is in a thread with an ongoing setup process, pass it to the setup handler
        if isinstance(message.channel, Thread) and message.channel.id in self.active_threads:
            thread_interaction = self.active_threads[message.channel.id]
            await thread_interaction.on_message(message)
            if thread_interaction.completed:
                _logger.debug(f"Completed interaction on thread {message.channel.id}")
                await thread_interaction.finish()
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
                try:
                    await _discord_notifier_bot_commands[pattern](self, message, match)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    await message.channel.send(
                        f"Sorry {message.author.mention}! Something went wrong while running your"
                        f" command.```{traceback.format_exc()[-1900:]}```"
                    )
                    raise
                break

    @staticmethod
    def command(r: str) -> Callable[..., Any]:
        """
        Decorator for defining bot commands matching a given regex.

        After receiving a command, the bot will call the first @command function whose regex
        matches the given command.
        """

        def deco(f: Callable[..., Any]) -> Callable[..., Any]:
            _discord_notifier_bot_commands[re.compile(r, re.IGNORECASE)] = f
            return f

        return deco

    @staticmethod
    def pass_notifier(*, save_changes: bool = False) -> Callable[..., Any]:
        """
        Decorator for use with commands that operate on a notifier in the current channel.

        Commands decorated with this will receive an instance of the notifier in the current
        channel in their arguments, and the notifier's existence will be checked prior to command
        execution.

        If the command makes any changes to the notifier's configuration, these will be persisted
        to the database if "save_changes" is True.
        """

        @wrapt.decorator
        async def wrapper(
            wrapped: Callable[..., Any], _instance: Any, args: list, kwargs: dict
        ) -> Any:
            instance: DiscordNotifierBot = args[0]
            message: Message = args[1]
            if not await instance.check_notifier_exists(message):
                return None

            notifier = instance.notifiers[message.channel.id]
            if save_changes:
                # save original notifier config so we can detect if it was changed
                old_notifier_config = notifier.config.copy(deep=True)
            result = await wrapped(*args, notifier, **kwargs)
            if save_changes and notifier.config != old_notifier_config:
                _logger.debug(f"Notifier for {message.channel} was changed, saving!")
                save_discord_notifier_to_db(notifier)

            return result

        return wrapper

    def affirm(self) -> str:
        return random.choice(AFFIRMATIONS)

    def thank(self) -> str:
        return random.choice(THANKS)

    async def check_notifier_exists(self, message: Message) -> bool:
        if message.channel.id not in self.notifiers:
            await message.channel.send(
                f"Sorry {message.author.mention}, you cannot use this command because there is not"
                " a notifier on this channel. Try setting one up with `$notify <source>`."
            )
            return False
        return True

    @command(r"notify (?P<source_name>.+?)( (?P<params>(\w+=[\w-]+ ?)+)$|$)")
    async def create_notifier(self, message: Message, command: re.Match) -> None:
        source_name: str = command.group("source_name").lower()
        params: dict[str, str] | None = None
        if command.group("params"):
            params = dict((p.split("=") for p in command.group("params").split(" ")))
        _logger.info(f"Received request to create notifier from {source_name=} {params=}")

        await create_notifier(self, message, source_name, params)

    @command(r"(pause|stop)")
    @pass_notifier(save_changes=True)
    async def pause(self, message: Message, _command: re.Match, notifier: ListingNotifier) -> None:
        notifier.pause()
        await message.channel.send(
            f"{self.affirm()} {message.author.mention}, I've paused notifications for this channel."
        )

    @command(r"(unpause|start)")
    @pass_notifier(save_changes=True)
    async def unpause(
        self, message: Message, _command: re.Match, notifier: ListingNotifier
    ) -> None:
        # send response first to ensure resumed notifications appear after this message
        await message.channel.send(
            f"{self.affirm()} {message.author.mention}, I've resumed notifications for this"
            " channel."
        )
        notifier.unpause()

    @command(r"filter (?P<field>.+?) (?P<filter_command>.+)")
    @pass_notifier(save_changes=True)
    async def filter(self, message: Message, command: re.Match, notifier: ListingNotifier) -> None:
        field: str = command.group("field")
        filter_command: str = command.group("filter_command")

        # allow shorthand to default to "title" field
        if is_valid_string_filter_command(f"{field} {filter_command}"):
            filter_command = f"{field} {filter_command}"
            field = "title"

        await filter_(self, message, notifier, field, filter_command)


async def start() -> None:
    loop = asyncio.get_running_loop()

    intents = discord.Intents(messages=True, guild_messages=True, message_content=True, guilds=True)
    client = discord.Client(intents=intents, loop=loop)
    discord_bot: DiscordNotifierBot = DiscordNotifierBot(client)

    @client.event
    async def on_ready() -> None:
        _logger.info(f"We have logged in as {client.user}")
        discord_bot.load_saved_notifiers()

    @client.event
    async def on_message(message: Message) -> None:
        await discord_bot.on_message(message)

    await client.start(settings.discord_token)
