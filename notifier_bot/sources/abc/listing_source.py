import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

_T = TypeVar("_T")


class ListingSource(ABC, Generic[_T]):
    def __init__(self, start_time: datetime | None = None) -> None:
        if start_time is None:
            start_time = datetime.now()
        self._last_checked = start_time

    @abstractmethod
    async def get_listings(self, after_time: datetime, limit: int | None = None) -> list[_T]:
        pass

    async def new_listings(self) -> list[_T]:
        listings = await self.get_listings(self._last_checked)
        self._last_checked = datetime.now()
        return listings


class PeriodicCheckListingSource(ListingSource[_T]):
    def __init__(
        self,
        start_time: datetime | None = None,
        interval_seconds: int = 600,
        loop: asyncio.AbstractEventLoop | None = None,
        start_search_task: bool = True,
    ) -> None:
        super().__init__(start_time)
        self.__new_listings: list[_T] = []
        self.interval_seconds = interval_seconds
        self.search_task: asyncio.Task | None = None
        if start_search_task:
            self.start_search_task(loop)

    def start_search_task(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()
        self.search_task = loop.create_task(self.__collect_new_listings_loop())

    async def __collect_new_listings_loop(self) -> None:
        while True:
            try:
                listings = await self.get_listings(self._last_checked)
                self.__new_listings.extend(listings)
                self._last_checked = datetime.now()
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def new_listings(self) -> list[_T]:
        temp = self.__new_listings.copy()
        self.__new_listings.clear()
        return temp
