import logging
from typing import Awaitable, Callable

from discord.interactions import Interaction
from discord.ui import Modal

from plugins.marketplace.models import MarketplaceSearchParams

_logger = logging.getLogger(__name__)


class MarketplaceSetupModal(Modal):
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
        pass

    async def on_submit(self, interaction: Interaction) -> None:
        pass
