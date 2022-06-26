from pytest_mock import MockerFixture

from hyacinth.discord.notifier_setup import NotifierSetupInteraction
from hyacinth.models import SearchSpec
from hyacinth.plugin import register_plugin
from plugins.craigslist.models import CraigslistSearchParams
from plugins.craigslist.plugin import CraigslistPlugin
from plugins.craigslist.util import get_areas
from tests.conftest import make_message

MODULE = "hyacinth.discord.notifier_setup"

SOME_AREA_INDEX = 0
SOME_CATEGORY = "mca"
SOME_MAX_DISTANCE = 500


def test_craigslist_notifier_setup_interaction__creates_proper_search_spec(
    mocker: MockerFixture,
) -> None:
    plugin = register_plugin(CraigslistPlugin)

    discord_notifier_mock = mocker.patch(f"{MODULE}.DiscordNotifier")
    create_search_mock = mocker.Mock()
    discord_notifier_mock.return_value.create_search = create_search_mock
    bot_mock = mocker.Mock()
    bot_mock.notifiers = {}
    initiating_message_mock = make_message()
    save_notifier_mock = mocker.patch(f"{MODULE}.save_notifier_to_db")
    setup_interaction = NotifierSetupInteraction(bot_mock, initiating_message_mock, plugin)

    setup_interaction.answers = {
        "area": str(SOME_AREA_INDEX + 1),
        "category": SOME_CATEGORY,
    }
    setup_interaction.configure_notifier()

    area = get_areas()[list(get_areas())[SOME_AREA_INDEX]]
    search_spec = SearchSpec(
        plugin_path=plugin.path,
        search_params=CraigslistSearchParams(
            site=area.site,
            nearby_areas=area.nearby_areas,
            category=SOME_CATEGORY,
        ),
    )

    create_search_mock.assert_called_once_with(search_spec)
    save_notifier_mock.assert_called_once()
