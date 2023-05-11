from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable

import discord
from discord.ui import Modal

from hyacinth.models import DiscordMessage
from hyacinth.plugin import Plugin
from hyacinth.settings import get_settings
from plugins.craigslist.format import format_listing
from plugins.craigslist.listings import get_listings
from plugins.craigslist.models import CraigslistListing, CraigslistSearchParams
from plugins.craigslist.setup_modal import CraigslistSetupModal

settings = get_settings()
_logger = logging.getLogger(__name__)


class CraigslistPlugin(Plugin[CraigslistSearchParams, CraigslistListing]):
    @property
    def display_name(self) -> str:
        return "Craigslist"

    @property
    def command_reference_name(self) -> str:
        return "craigslist"

    def polling_interval(self, search_params: CraigslistSearchParams) -> int:
        return settings.craigslist_poll_interval_seconds

    def get_listings(
        self, search_params: CraigslistSearchParams, after_time: datetime, limit: int | None = None
    ) -> list[CraigslistListing]:
        return get_listings(search_params, after_time, limit)

    def format_listing(self, listing: CraigslistListing) -> DiscordMessage:
        return format_listing(listing)

    def get_setup_modal(
        self,
        callback: Callable[[discord.Interaction, CraigslistSearchParams], Awaitable[None]],
        existing_search_params: CraigslistSearchParams | None = None,
    ) -> Modal:
        return CraigslistSetupModal(callback, prefill=existing_search_params)
