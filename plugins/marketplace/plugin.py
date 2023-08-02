from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable

import discord
from discord.ui import Modal

from hyacinth.models import DiscordMessage
from hyacinth.notifier import ChannelNotifier
from hyacinth.plugin import Plugin
from hyacinth.settings import get_settings
from plugins.marketplace.client import get_listings
from plugins.marketplace.format import format_listing
from plugins.marketplace.models import MarketplaceListing, MarketplaceSearchParams
from plugins.marketplace.setup_modal import MarketplaceSetupModal

settings = get_settings()
_logger = logging.getLogger(__name__)


class MarketplacePlugin(Plugin[MarketplaceSearchParams, MarketplaceListing]):
    @property
    def display_name(self) -> str:
        return "Marketplace"

    @property
    def command_reference_name(self) -> str:
        return "marketplace"

    def polling_interval(self, search_params: MarketplaceSearchParams) -> int:
        return settings.marketplace_poll_interval_seconds

    async def get_listings(
        self, search_params: MarketplaceSearchParams, after_time: datetime, limit: int | None = None
    ) -> list[MarketplaceListing]:
        return await get_listings(search_params, after_time, limit)

    def format_listing(
        self, notifier: ChannelNotifier, listing: MarketplaceListing
    ) -> DiscordMessage:
        return format_listing(notifier, listing)

    def get_setup_modal(
        self,
        callback: Callable[[discord.Interaction, MarketplaceSearchParams], Awaitable[None]],
        existing_search_params: MarketplaceSearchParams | None = None,
    ) -> Modal:
        return MarketplaceSetupModal(callback, prefill=existing_search_params)
