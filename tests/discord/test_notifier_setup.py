from pytest_mock import MockerFixture

from notifier_bot.discord.notifier_setup import CraigslistNotifierSetupInteraction
from notifier_bot.models import SearchSpec, SearchSpecSource
from notifier_bot.settings import get_settings
from notifier_bot.sources.craigslist import CraigslistSearchParams
from notifier_bot.util.craigslist import get_areas
from tests.conftest import make_message

settings = get_settings()

MODULE = "notifier_bot.discord.notifier_setup"

SOME_AREA_INDEX = 0
SOME_CATEGORY = "mca"
SOME_MIN_PRICE = 2
SOME_MAX_PRICE = 5000
SOME_MAX_DISTANCE = 500


def test_craigslist_notifier_setup_interaction__creates_proper_search_spec(
    mocker: MockerFixture,
) -> None:
    discord_notifier_mock = mocker.patch(f"{MODULE}.DiscordNotifier")
    create_search_mock = mocker.Mock()
    discord_notifier_mock.return_value.create_search = create_search_mock
    bot_mock = mocker.Mock()
    bot_mock.notifiers = {}
    initiating_message_mock = make_message()
    save_notifier_mock = mocker.patch(f"{MODULE}.save_notifier_to_db")
    setup_interaction = CraigslistNotifierSetupInteraction(bot_mock, initiating_message_mock)

    setup_interaction.answers = {
        "area": str(SOME_AREA_INDEX + 1),
        "category": SOME_CATEGORY,
        "price_range": f"{SOME_MIN_PRICE}-{SOME_MAX_PRICE}",
        "max_distance_miles": str(SOME_MAX_DISTANCE),
    }
    setup_interaction.configure_notifier()

    area = get_areas()[list(get_areas())[SOME_AREA_INDEX]]
    search_spec = SearchSpec(
        source=SearchSpecSource.CRAIGSLIST,
        search_params=CraigslistSearchParams(
            site=area.site,
            nearby_areas=area.nearby_areas,
            category=SOME_CATEGORY,
            home_lat_long=settings.home_lat_long,
            min_price=SOME_MIN_PRICE,
            max_price=SOME_MAX_PRICE,
            max_distance_miles=SOME_MAX_DISTANCE,
        ),
    )

    create_search_mock.assert_called_once_with(search_spec)
    save_notifier_mock.assert_called_once()
