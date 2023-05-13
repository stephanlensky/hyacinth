from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine

from discord import Interaction
from discord.app_commands import Choice

from hyacinth.db.models import Filter

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot


MAX_AUTOCOMPLETE_CHOICES = 25


def get_search_autocomplete(
    bot: DiscordBot,
) -> Callable[[Interaction, str], Coroutine[Any, Any, list[Choice[str]]]]:
    async def search_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
        channel_id = interaction.channel_id
        if channel_id not in bot.notifiers:
            return []
        channel_notifier = bot.notifiers[channel_id]
        channel_searches = channel_notifier.config.active_searches

        alphabetical_search_names = sorted([search.name for search in channel_searches])

        return [
            Choice(name=search_name, value=search_name)
            for search_name in alphabetical_search_names
            if search_name.lower().startswith(current.lower())
        ][:MAX_AUTOCOMPLETE_CHOICES]

    return search_autocomplete


def get_filter_field_autocomplete(
    bot: DiscordBot,
) -> Callable[[Interaction, str], Coroutine[Any, Any, list[Choice[str]]]]:
    async def filter_field_autocomplete(
        interaction: Interaction, current: str
    ) -> list[Choice[str]]:
        channel_id = interaction.channel_id
        if channel_id not in bot.notifiers:
            return []
        channel_notifier = bot.notifiers[channel_id]
        channel_plugins = channel_notifier.get_active_plugins()

        filterable_fields: set[str] = set()
        for plugin in channel_plugins:
            filterable_fields.update(plugin.listing_cls.__fields__.keys())
        alphabetical_fields = sorted(filterable_fields)

        return [
            Choice(name=field, value=field)
            for field in alphabetical_fields
            if field.lower().startswith(current.lower())
        ][:MAX_AUTOCOMPLETE_CHOICES]

    return filter_field_autocomplete


def _format_filter_autocomplete_option(filter: Filter) -> str:
    return f"{str(filter.rule_type.value).upper()} {filter.field}: {filter.rule_expr}"


def get_filter_autocomplete(
    bot: DiscordBot,
) -> Callable[[Interaction, str], Coroutine[Any, Any, list[Choice[int]]]]:
    async def filter_field_autocomplete(
        interaction: Interaction, current: str
    ) -> list[Choice[int]]:
        channel_id = interaction.channel_id
        if channel_id not in bot.notifiers:
            return []
        channel_notifier = bot.notifiers[channel_id]
        channel_filters = channel_notifier.config.filters

        formatted_options = [
            _format_filter_autocomplete_option(filter) for filter in channel_filters
        ]

        return [
            Choice(name=option, value=idx)
            for idx, option in enumerate(formatted_options)
            if option.lower().startswith(current.lower())
        ][:MAX_AUTOCOMPLETE_CHOICES]

    return filter_field_autocomplete
