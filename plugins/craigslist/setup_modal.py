import logging
from typing import Awaitable, Callable

from discord.interactions import Interaction
from discord.ui import Modal, TextInput

from plugins.craigslist.models import CraigslistSearchParams
from plugins.craigslist.util import get_areas

_logger = logging.getLogger(__name__)


class CraigslistSetupModal(Modal):
    name: TextInput = TextInput(
        label="Area", placeholder="Craigslist area to search", required=True
    )

    def __init__(
        self,
        callback: Callable[[Interaction, CraigslistSearchParams], Awaitable[None]],
        prefill: CraigslistSearchParams | None = None,
    ):
        self.callback = callback
        super().__init__(title="Craigslist Notifier Setup")

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            area = get_areas()["New England/New York"]
            await self.callback(
                interaction,
                CraigslistSearchParams(
                    site=area.site,
                    nearby_areas=area.nearby_areas,
                    category="sss",  # general for sale
                ),
            )
        except Exception:
            _logger.exception("Error in on_submit")
