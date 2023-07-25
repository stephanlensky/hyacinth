import logging
from typing import Awaitable, Callable

from discord import TextStyle
from discord.interactions import Interaction
from discord.ui import Modal, TextInput

from plugins.craigslist.models import CraigslistSearchParams
from plugins.craigslist.util import get_areas_reference

_logger = logging.getLogger(__name__)


class CraigslistSetupModal(Modal):
    site: TextInput = TextInput(
        label="Site",
        placeholder="Name of Craigslist site to search (e.g. boston, sfbay)",
        style=TextStyle.short,
        required=True,
    )
    category: TextInput = TextInput(
        label="Category",
        placeholder="Category to search (e.g. sss, ata)",
        style=TextStyle.short,
        required=True,
    )

    def __init__(
        self,
        callback: Callable[[Interaction, CraigslistSearchParams], Awaitable[None]],
        prefill: CraigslistSearchParams | None = None,
    ):
        self.callback = callback
        super().__init__(title="Craigslist Notifier Setup")

        if prefill is not None:
            self._prefill_fields(prefill)

    def _prefill_fields(self, prefill: CraigslistSearchParams) -> None:
        for child in self.children:
            if not isinstance(child, TextInput):
                continue

            if child == self.site:
                child.default = prefill.site
            elif child == self.category:
                child.default = prefill.category

    async def on_submit(self, interaction: Interaction) -> None:
        if self.site.value not in get_areas_reference():
            await interaction.response.send_message(
                (
                    f"Sorry {interaction.user.mention}, the site you entered does not appear to be"
                    " a valid Craigslist site. Please try again."
                ),
                ephemeral=True,
            )
            return

        try:
            await self.callback(
                interaction,
                CraigslistSearchParams(
                    site=self.site.value,
                    category=self.category.value,
                ),
            )
        except Exception:
            _logger.exception("Error in on_submit")
