import logging
import re
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING

from discord import Member, Message, Thread, User

from notifier_bot.models import CraigslistArea, SearchSpec, SearchSpecSource
from notifier_bot.notifier import DiscordNotifier, ListingNotifier
from notifier_bot.settings import get_settings
from notifier_bot.sources.craigslist import CraigslistSearchParams
from notifier_bot.util.craigslist import get_areas

if TYPE_CHECKING:
    # avoid circular import
    from discord.abc import MessageableChannel

    from notifier_bot.discord.discord_bot import DiscordNotifierBot

settings = get_settings()
_logger = logging.getLogger(__name__)


class ThreadBasedSetupHandler(ABC):
    def __init__(
        self,
        discord_bot: "DiscordNotifierBot",
        channel: "MessageableChannel",
        thread: Thread,
        calling_user: User | Member,
        notifier: ListingNotifier | None,
    ) -> None:
        self.calling_user = calling_user
        self.discord_bot = discord_bot
        self.channel = channel
        self.thread = thread
        self.notifier = notifier

    @abstractmethod
    async def send_first_message(self) -> None:
        pass

    @abstractmethod
    async def on_message(self, message: Message) -> None:
        pass

    @abstractmethod
    def is_complete(self) -> bool:
        pass


class CraigslistSetupHandler(ThreadBasedSetupHandler):
    def __init__(
        self,
        discord_bot: "DiscordNotifierBot",
        channel: "MessageableChannel",
        thread: Thread,
        calling_user: User | Member,
        notifier: ListingNotifier | None,
    ) -> None:
        super().__init__(discord_bot, channel, thread, calling_user, notifier)
        self.area: CraigslistArea | None = None
        self.category: str | None = None
        self.min_price: int | None = None
        self.max_price: int | None = None
        self.max_distance_miles: int | None = None
        self.done = False

    async def send_first_message(self) -> None:
        await self.thread.send(f"Hi {self.calling_user.mention}! Let's get that set up for you.")
        await self.thread.send(self.get_area_prompt())

    def get_area_prompt(self) -> str:
        areas = "\n".join([f"{i + 1}. {area}" for i, area in enumerate(get_areas().keys())])
        return f"Which area of Craigslist would you like to search? Available areas:\n```{areas}```"

    def get_category_prompt(self) -> str:
        return (
            "Which category of Craigslist would you like to search? This is the string in the"
            " Craigslist URL after `/search`. For example, `mca` for motorcycles or `sss` for"
            ' general "for sale".'
        )

    def get_price_prompt(self) -> str:
        return (
            "What price range would you like to search for? Enter your answer as two dollar values"
            " separated by a hyphen. For example, `20-100`."
        )

    def get_max_distance_prompt(self) -> str:
        return (
            "What is the maximum distance away (in miles) that you would like to show results for?"
        )

    async def on_message(self, message: Message) -> None:
        # handle area selection
        if self.area is None:
            selected_area: str | None = None
            areas = get_areas()
            try:
                selection = int(message.content) - 1
                if 0 <= selection < len(areas):
                    selected_area = list(areas)[selection]
            except ValueError:
                if message.content in areas:
                    selected_area = message.content

            if selected_area is None:
                await self.thread.send(
                    f"Sorry {message.author.mention}, your selection wasn't recognized. Please try"
                    " again."
                )
                await self.thread.send(self.get_area_prompt())
                return

            self.area = areas[selected_area]
            await self.thread.send(
                f"{self.discord_bot.affirmation()} {message.author.mention}. I'll show you"
                f" results from `{selected_area}`."
            )
            await self.thread.send(self.get_category_prompt())

        # handle category selection
        elif self.category is None:
            if not re.match(r"^[a-zA-Z0-9]+$", message.content):
                await self.thread.send(
                    f"Sorry {message.author.mention}, I didn't recognize that. Categories should"
                    " contain only letters and numbers. Please try again."
                )
                await self.thread.send(self.get_category_prompt())
                return

            self.category = message.content
            await self.thread.send(
                f"{self.discord_bot.affirmation()} {message.author.mention}, I'll look for results"
                f" from category `{self.category}`."
            )
            await self.thread.send(self.get_price_prompt())

        # handle min/max price selection
        elif self.min_price is None or self.max_price is None:
            match = re.match(r"^(?P<min_price>[0-9]+)-(?P<max_price>[0-9]+)$", message.content)
            if not match:
                await self.thread.send(
                    f"Sorry {message.author.mention}, I didn't recognize that. Please try again."
                )
                await self.thread.send(self.get_price_prompt())
                return

            min_price, max_price = match.group("min_price", "max_price")
            self.min_price = int(min_price)
            self.max_price = int(max_price)
            await self.thread.send(
                f"{self.discord_bot.affirmation()} {message.author.mention}, setting a minimum"
                f" price of ${self.min_price} and maximum price of ${self.max_price} for this"
                " search. Almost done! Just one last question."
            )
            await self.thread.send(self.get_max_distance_prompt())

        # handle max distance selection
        elif self.max_distance_miles is None:
            if not re.match(r"^[0-9]+$", message.content):
                await self.thread.send(
                    f"Sorry {message.author.mention}, I didn't recognize that. Please try again."
                )
                await self.thread.send(self.get_max_distance_prompt())
                return

            self.max_distance_miles = int(message.content)
            await self.thread.send(
                f"{self.discord_bot.affirmation()} {message.author.mention}, setting a maximum"
                f" distance of {self.max_distance_miles} miles away."
            )
            await self.thread.send(
                "All done! I will configure the notifier for you now. This thread can be safely"
                " deleted."
            )

            # configuration is done, create the notifier/register search
            self.create_search()

    def create_search(self) -> None:
        if (
            self.area is None
            or self.category is None
            or self.min_price is None
            or self.max_price is None
            or self.max_distance_miles is None
        ):
            raise ValueError("Initialize all parameters before creating search")

        search_spec = SearchSpec(
            source=SearchSpecSource.CRAIGSLIST,
            search_params=CraigslistSearchParams(
                site=self.area.site,
                nearby_areas=self.area.nearby_areas,
                category=self.category,
                home_lat_long=settings.home_lat_long,
                min_price=self.min_price,
                max_price=self.max_price,
                max_distance_miles=self.max_distance_miles,
            ).dict(),
        )
        if self.notifier is None:
            logging.info(f"Creating notifier for channel {self.channel.id}")
            self.discord_bot.notifiers[self.thread.parent_id] = DiscordNotifier(
                self.channel, self.discord_bot.monitor, notification_frequency=timedelta(minutes=1)
            )
            self.notifier = self.discord_bot.notifiers[self.thread.parent_id]
        self.notifier.create_search(search_spec)

        self.done = True

    def is_complete(self) -> bool:
        return self.done
