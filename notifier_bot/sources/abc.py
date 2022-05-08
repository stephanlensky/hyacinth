from abc import ABC, abstractmethod
from datetime import datetime

from notifier_bot.models import Listing, SearchParams


class ListingSource(ABC):
    @abstractmethod
    async def get_listings(self, after_time: datetime, limit: int | None = None) -> list[Listing]:
        pass

    @classmethod
    @abstractmethod
    def recommended_polling_interval(cls, search_params: SearchParams) -> int:
        "Recommended polling interval in seconds"
