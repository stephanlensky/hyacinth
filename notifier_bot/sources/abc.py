from abc import ABC, abstractmethod
from datetime import datetime

from notifier_bot.models import Listing


class ListingSource(ABC):
    @abstractmethod
    async def get_listings(self, after_time: datetime, limit: int | None = None) -> list[Listing]:
        pass

    @property
    @abstractmethod
    def recommended_polling_interval(self) -> int:
        "Recommended polling interval in seconds"
