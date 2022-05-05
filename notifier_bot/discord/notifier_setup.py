import logging
import re
import traceback
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from discord import Message

from notifier_bot.discord.thread_interaction import FMT_USER, Question, ThreadInteraction
from notifier_bot.models import SearchSpec, SearchSpecSource
from notifier_bot.notifier import DiscordNotifier
from notifier_bot.settings import get_settings
from notifier_bot.sources.craigslist import CraigslistSearchParams
from notifier_bot.util.craigslist import get_areas

if TYPE_CHECKING:
    # avoid circular import
    from notifier_bot.discord.discord_bot import DiscordNotifierBot

settings = get_settings()
_logger = logging.getLogger(__name__)


class CraigslistNotifierSetupInteraction(ThreadInteraction):
    def __init__(self, bot: "DiscordNotifierBot", initiating_message: Message) -> None:
        super().__init__(
            bot,
            initiating_message,
            thread_title="Create a new Craigslist notifier",
            first_message=f"Hi {FMT_USER}! Let's get that set up for you.",
            questions=[
                Question(
                    key="area",
                    prompt=(
                        "Which area of Craigslist would you like to search? Available"
                        f" areas:\n```{self.available_areas}```"
                    ),
                    validator=CraigslistNotifierSetupInteraction.validate_areas,
                ),
                Question(
                    key="category",
                    prompt=(
                        "Which category of Craigslist would you like to search? This is the string"
                        " in the Craigslist URL after `/search`. For example, `mca` for motorcycles"
                        ' or `sss` for general "for sale".'
                    ),
                    validator=CraigslistNotifierSetupInteraction.validate_category,
                ),
                Question(
                    key="price_range",
                    prompt=(
                        "What price range would you like to search for? Enter your answer as two"
                        " dollar values separated by a hyphen. For example, `20-100`."
                    ),
                    validator=CraigslistNotifierSetupInteraction.validate_price_range,
                ),
                Question(
                    key="max_distance_miles",
                    prompt=(
                        "What is the maximum distance away (in miles) that you would like to show"
                        " results for?"
                    ),
                    validator=int,
                ),
            ],
        )

    async def finish(self) -> dict[str, Any]:
        try:
            self.configure_notifier()
        except Exception:
            await self.send(
                f"Sorry {FMT_USER}! Something went wrong while configuring the notifier for this"
                f" channel. ```{traceback.format_exc()}```"
            )
            await super().finish()
            raise

        await self.send(
            f"{self.bot.thank()} {FMT_USER}! I've set up a notifier for new Craigslist listings on"
            " this channel."
        )

        return await super().finish()

    def configure_notifier(self) -> None:
        search_params = dict(self._answers)
        area = get_areas()[search_params.pop("area")]
        search_params["site"] = area.site
        search_params["nearby_areas"] = area.nearby_areas
        search_params["min_price"], search_params["max_price"] = search_params.pop("price_range")
        search_params["home_lat_long"] = settings.home_lat_long

        search_spec = SearchSpec(
            source=SearchSpecSource.CRAIGSLIST,
            search_params=CraigslistSearchParams.parse_obj(search_params).dict(),
        )

        channel = self.initiating_message.channel
        if channel.id not in self.bot.notifiers:
            _logger.info(f"Creating notifier for channel {channel.id}")
            self.bot.notifiers[channel.id] = DiscordNotifier(
                channel, self.bot.monitor, notification_frequency=timedelta(minutes=1)
            )
        self.bot.notifiers[channel.id].create_search(search_spec)

    @property
    def available_areas(self) -> str:
        return "\n".join([f"{i + 1}. {area}" for i, area in enumerate(get_areas().keys())])

    @staticmethod
    def validate_areas(v: str) -> str:
        areas = get_areas()
        try:
            selection = int(v) - 1
            selected_area = list(get_areas())[selection]
        except ValueError:
            if v in areas:
                selected_area = v
            else:
                raise

        return selected_area

    @staticmethod
    def validate_category(v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9]+$", v):
            raise ValueError("Category must be alphanumeric")
        return v

    @staticmethod
    def validate_price_range(v: str) -> tuple[int, int]:
        match = re.match(r"^(?P<min_price>[0-9]+)-(?P<max_price>[0-9]+)$", v)
        if not match:
            raise ValueError("Price range must be two hyphen-separated numbers")

        min_price, max_price = match.group("min_price", "max_price")
        return (int(min_price), int(max_price))
