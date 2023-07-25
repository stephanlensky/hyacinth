from __future__ import annotations

import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.app_commands import Choice

from hyacinth.db.crud.notifier import get_channel_notifiers
from hyacinth.db.session import Session
from hyacinth.discord.autocomplete import (
    get_filter_autocomplete,
    get_filter_field_autocomplete,
    get_search_autocomplete,
)
from hyacinth.discord.commands.filter import create_filter, delete_filter, edit_filter
from hyacinth.discord.commands.pause import pause as pause_cmd
from hyacinth.discord.commands.search import create_search, delete_search, edit_search
from hyacinth.discord.commands.show import show as show_cmd
from hyacinth.enums import RuleType
from hyacinth.monitor import MarketplaceMonitor
from hyacinth.notifier import ChannelNotifier
from hyacinth.plugin import Plugin, register_plugin
from hyacinth.settings import get_settings
from hyacinth.util.decorators import log_exceptions

settings = get_settings()
_logger = logging.getLogger(__name__)

AFFIRMATIONS = ["Okay", "Sure", "Sounds good", "No problem", "Roger that", "Got it"]
THANKS = [*AFFIRMATIONS, "Thanks", "Thank you"]


class DiscordBot:
    def __init__(self, client: discord.Client) -> None:
        self.client = client
        self.tree = app_commands.CommandTree(client)

        self.monitor = MarketplaceMonitor()
        self.notifiers: dict[int, ChannelNotifier] = {}  # channel ID -> notifier
        self.plugins: list[Plugin] = []

    async def on_ready(self) -> None:
        _logger.info(f"We have logged in as {self.client.user}")

        self.load_plugins()
        self.load_saved_notifiers()
        await self.register_commands()

    def load_plugins(self) -> None:
        for plugin_path in settings.plugins:
            _logger.info(f"Loading plugin {plugin_path}")
            self.plugins.append(register_plugin(plugin_path))

    def load_saved_notifiers(self) -> None:
        with Session() as session:
            notifiers = get_channel_notifiers(session, self.client, self.monitor)
        for notifier in notifiers:
            self.notifiers[notifier.channel.id] = notifier
        _logger.info(f"Loaded {len(notifiers)} saved notifiers from the database!")

    async def register_commands(self) -> None:
        self.tree.add_command(self.search_command_group)
        self.tree.add_command(self.filter_command_group)
        self.tree.add_command(self.pause_command)
        self.tree.add_command(self.show_command)

        for guild in self.client.guilds:
            _logger.info(f"Adding commands to guild {guild.name}")
            self.tree.copy_global_to(guild=guild)  # type: ignore
            await self.tree.sync(guild=guild)  # type: ignore

    def affirm(self) -> str:
        return random.choice(AFFIRMATIONS)

    def thank(self) -> str:
        return random.choice(THANKS)

    @property
    def search_command_group(self) -> app_commands.Group:
        @app_commands.command(description="Add a new search to this channel.")  # type: ignore
        @app_commands.describe(
            plugin="The plugin to use for this search.",
            name=(
                "The name to use for this search, used to reference the search with other commands."
            ),
        )
        @app_commands.choices(
            plugin=[
                Choice(name=plugin.command_reference_name, value=i)
                for i, plugin in enumerate(self.plugins)
            ]
        )
        @log_exceptions(_logger)
        async def add(interaction: discord.Interaction, plugin: int, name: str) -> None:
            await create_search(self, interaction, self.plugins[plugin], name)

        @app_commands.command(  # type: ignore
            description="Edit an existing search on this channel.",
        )
        @app_commands.describe(search="The search to edit.")
        @app_commands.autocomplete(search=get_search_autocomplete(self))
        @log_exceptions(_logger)
        async def edit(interaction: discord.Interaction, search: str) -> None:
            await edit_search(self, interaction, search)

        @app_commands.command(  # type: ignore
            description="Delete an existing search on this channel.",
        )
        @app_commands.describe(search="The search to delete.")
        @app_commands.autocomplete(search=get_search_autocomplete(self))
        @log_exceptions(_logger)
        async def delete(interaction: discord.Interaction, search: str) -> None:
            await delete_search(self, interaction, search)

        search_command_group = app_commands.Group(
            name="search", description="Manage search notifications for this channel."
        )
        search_command_group.add_command(add)
        search_command_group.add_command(edit)
        search_command_group.add_command(delete)

        return search_command_group

    @property
    def filter_command_group(self) -> app_commands.Group:
        @app_commands.command(  # type: ignore
            name="add", description="Add a new filter rule for notifications on this channel."
        )
        @app_commands.describe(
            field="The field to apply this filter to.",
            rule_type="The type of rule to add.",
            rule="The rule to add.",
        )
        @app_commands.autocomplete(field=get_filter_field_autocomplete(self))
        @app_commands.choices(
            rule_type=[
                Choice(name=rule_type.value, value=rule_type.value) for rule_type in RuleType
            ]
        )
        @log_exceptions(_logger)
        async def add(
            interaction: discord.Interaction, field: str, rule_type: str, rule: str
        ) -> None:
            await create_filter(self, interaction, field, RuleType(rule_type), rule)

        @app_commands.command(  # type: ignore
            name="edit",
            description="Edit an existing filter rule for notifications on this channel.",
        )
        @app_commands.describe(
            filter="The filter rule to edit.",
            new_rule="The new rule to apply.",
        )
        @app_commands.autocomplete(filter=get_filter_autocomplete(self))
        @log_exceptions(_logger)
        async def edit(interaction: discord.Interaction, filter: int, new_rule: str) -> None:
            await edit_filter(self, interaction, filter, new_rule)

        @app_commands.command(  # type: ignore
            name="delete",
            description="Delete an existing filter rule for notifications on this channel.",
        )
        @app_commands.describe(
            filter="The filter rule to delete.",
        )
        @app_commands.autocomplete(filter=get_filter_autocomplete(self))
        @log_exceptions(_logger)
        async def delete(interaction: discord.Interaction, filter: int) -> None:
            await delete_filter(self, interaction, filter)

        filter_command_group = app_commands.Group(
            name="filter", description="Manage filter rules for this channel."
        )
        filter_command_group.add_command(add)
        filter_command_group.add_command(edit)
        filter_command_group.add_command(delete)

        return filter_command_group

    @property
    def pause_command(self) -> app_commands.Command:
        @app_commands.command(  # type: ignore
            description="Temporarily pause or resume notifications on this channel."
        )
        @log_exceptions(_logger)
        async def pause(interaction: discord.Interaction) -> None:
            await pause_cmd(self, interaction)

        return pause

    @property
    def show_command(self) -> app_commands.Command:
        @app_commands.command(  # type: ignore
            description="Show a summary of existing notifiers and filter rules for this channel."
        )
        @log_exceptions(_logger)
        async def show(interaction: discord.Interaction) -> None:
            await show_cmd(self, interaction)

        return show


async def start() -> None:
    loop = asyncio.get_running_loop()

    intents = discord.Intents(guilds=True)
    client = discord.Client(intents=intents, loop=loop)
    discord_bot: DiscordBot = DiscordBot(client)

    @client.event
    async def on_ready() -> None:
        try:
            await discord_bot.on_ready()
        except Exception:
            _logger.exception("Error in on_ready")
            await client.close()

    await client.start(settings.discord_token)
