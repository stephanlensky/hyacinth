import logging
from typing import Awaitable, Callable

from discord import TextStyle
from discord.interactions import Interaction
from discord.ui import Modal, TextInput

from plugins.marketplace.models import MarketplaceSearchParams
from plugins.marketplace.util import has_category

_logger = logging.getLogger(__name__)


class MarketplaceSetupModal(Modal):
    location: TextInput = TextInput(
        label="Location",
        placeholder="Vanity URL or ID of location (see docs)",
        style=TextStyle.short,
        required=True,
    )
    category: TextInput = TextInput(
        label="Category",
        placeholder="SEO URL or ID of category (see docs)",
        style=TextStyle.short,
        required=True,
    )

    def __init__(
        self,
        callback: Callable[[Interaction, MarketplaceSearchParams], Awaitable[None]],
        prefill: MarketplaceSearchParams | None = None,
    ):
        self.callback = callback
        super().__init__(title="Marketplace Notifier Setup")

        if prefill is not None:
            self._prefill_fields(prefill)

    def _prefill_fields(self, prefill: MarketplaceSearchParams) -> None:
        for child in self.children:
            if not isinstance(child, TextInput):
                continue

            if child == self.location:
                child.default = prefill.location
            elif child == self.category:
                child.default = prefill.category

    async def on_submit(self, interaction: Interaction) -> None:
        if not has_category(self.category.value):
            await interaction.response.send_message(
                (
                    f"Sorry {interaction.user.mention}, the category you entered does not appear to"
                    " be a valid marketplace category. Please try again."
                ),
                ephemeral=True,
            )
            return

        try:
            await self.callback(
                interaction,
                MarketplaceSearchParams(
                    location=self.location.value,
                    category=self.category.value,
                ),
            )
        except Exception:
            _logger.exception("Error in on_submit")
