from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import discord

from hyacinth.db.crud.notifier import add_notifier_state
from hyacinth.db.models import NotifierSearch
from hyacinth.db.session import Session
from hyacinth.discord.views.confirm_delete import ConfirmDelete
from hyacinth.models import BaseSearchParams
from hyacinth.notifier import ChannelNotifier
from hyacinth.plugin import Plugin

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot

_logger = logging.getLogger(__name__)


async def create_search(
    bot: DiscordBot, interaction: discord.Interaction, plugin: Plugin, name: str
) -> None:
    async def callback(interaction: discord.Interaction, search_params: BaseSearchParams) -> None:
        await _create_search_with_params(bot, interaction, name, plugin, search_params)

    modal = plugin.get_setup_modal(callback)  # type: ignore
    await interaction.response.send_modal(modal)


async def _create_search_with_params(
    bot: DiscordBot,
    interaction: discord.Interaction,
    name: str,
    plugin: Plugin,
    search_params: BaseSearchParams,
) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "Search notifications can only be created on text channels.", ephemeral=True
        )
        return

    created_notifier = False
    if channel.id not in bot.notifiers:
        _logger.info(f"Creating search notification for channel {channel.id}")
        bot.notifiers[channel.id] = ChannelNotifier(
            channel, bot.monitor, ChannelNotifier.Config(paused=True)
        )
        # persist the new notifier to the database
        with Session() as session:
            notifier_state = add_notifier_state(session, bot.notifiers[channel.id])
            session.commit()
            bot.notifiers[channel.id].config.id = notifier_state.id
        created_notifier = True

    # if this is the first search set up on this channel, the notifier starts paused. add some
    # helpful information about that for the user if necessary.
    created_notifier_part = (
        "\n\nNotifications are currently paused. When you are done configuring your desired"
        " filter rules, toggle notifications back on with the `/pause` command."
        if created_notifier
        else ""
    )

    # create the search
    search_params_json = json.loads(search_params.json())  # dump and load to serialize subclasses
    bot.notifiers[channel.id].create_search(name, plugin, search_params_json)

    await interaction.response.send_message(
        (
            f"{bot.affirm()} {interaction.user.mention}, I've set up a search for new"
            f" {plugin.display_name} listings on this channel.{created_notifier_part}"
        ),
        ephemeral=True,
    )


async def _get_notifier_and_search(
    bot: DiscordBot, interaction: discord.Interaction, name: str
) -> tuple[ChannelNotifier, NotifierSearch] | tuple[None, None]:
    if interaction.channel is None:
        raise ValueError("Interaction channel is None")

    # check if a notifier exists for this channel
    notifier = bot.notifiers.get(interaction.channel.id)
    if not notifier:
        await interaction.response.send_message(
            (
                f"Sorry {interaction.user.mention}, this channel is not configured to send"
                " notifications. Try creating a new search with `/search add`."
            ),
            ephemeral=True,
        )
        return None, None

    # check if a search with the selected name exists
    selected_search = next(
        (search for search in notifier.config.active_searches if search.name == name),
        None,
    )
    if not selected_search:
        await interaction.response.send_message(
            (
                f"Sorry {interaction.user.mention}, I couldn't find a search named {name} on this"
                " channel."
            ),
            ephemeral=True,
        )
        return None, None

    return notifier, selected_search


async def edit_search(bot: DiscordBot, interaction: discord.Interaction, name: str) -> None:
    notifier, selected_search = await _get_notifier_and_search(bot, interaction, name)
    if not notifier or not selected_search:
        return
    plugin = selected_search.search_spec.plugin

    async def callback(interaction: discord.Interaction, search_params: BaseSearchParams) -> None:
        # type narrowing from above does not apply to nested functions
        # do a quick check here for the linter
        if not notifier or not selected_search:
            raise ValueError("Notifier or search is None")

        # dump and load to serialize subclasses
        search_params_json = json.loads(search_params.json())

        notifier.update_search(selected_search, search_params_json)

        await interaction.response.send_message(
            (
                f"{bot.affirm()} {interaction.user.mention}, I've updated your"
                f" {plugin.display_name} search {name}."
            ),
            ephemeral=True,
        )

    modal = plugin.get_setup_modal(callback, selected_search.search_spec.search_params)  # type: ignore
    await interaction.response.send_modal(modal)


async def delete_search(bot: DiscordBot, interaction: discord.Interaction, name: str) -> None:
    notifier, selected_search = await _get_notifier_and_search(bot, interaction, name)
    if not notifier or not selected_search:
        return

    # send confirmation dialog before deleting
    confirm = ConfirmDelete()
    confirmation_message = await interaction.channel.send(  # type: ignore
        (
            "Are you sure you want to continue? This will permanently delete your"
            f" {selected_search.search_spec.plugin.display_name} search {name}."
        ),
        view=confirm,
    )
    await interaction.response.defer(ephemeral=True)
    await confirm.wait()
    await confirmation_message.delete()

    if confirm.value:
        notifier.remove_search(selected_search)
        await interaction.followup.send(
            content=f"{bot.affirm()} {interaction.user.mention}, I deleted your search {name}.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            "Operation cancelled.",
            ephemeral=True,
        )
