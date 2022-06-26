from __future__ import annotations

import logging
from datetime import datetime

from hyacinth.discord.thread_interaction import Question
from hyacinth.models import DiscordMessage, Listing
from hyacinth.plugin import Plugin
from hyacinth.settings import get_settings
from plugins.craigslist.format import format_listing
from plugins.craigslist.listings import get_listings
from plugins.craigslist.models import CraigslistSearchParams
from plugins.craigslist.setup import questions

settings = get_settings()
_logger = logging.getLogger(__name__)


class CraigslistPlugin(Plugin[CraigslistSearchParams, Listing]):
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
    ) -> list[Listing]:
        return get_listings(search_params, after_time, limit)

    def format_listing(self, listing: Listing) -> DiscordMessage:
        return format_listing(listing)

    def get_setup_questions(self) -> list[Question]:
        return questions
