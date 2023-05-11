from datetime import datetime

from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from hyacinth.db.models import Filter, Listing, NotifierSearch, SearchSpec
from hyacinth.models import BaseListing, BaseSearchParams
from plugins.craigslist.plugin import CraigslistPlugin
from tests.sample_data import make_channel_notifier_state, make_filter, make_notifier_search

MODULE = "hyacinth.db.models"


def test_listing_from_base_listing__some_listing_model__creates_expected_model() -> None:
    class SomeListingModel(BaseListing):
        title: str

    base_listing = SomeListingModel(creation_time=datetime(2021, 1, 1), title="test title")
    listing = Listing.from_base_listing(base_listing, 1)

    assert listing.search_spec_id == 1
    assert listing.listing_json == '{"creation_time": "2021-01-01T00:00:00", "title": "test title"}'


def test_search_spec_plugin_property__some_plugin_path__loads_expected_plugin(
    load_plugins: None,
) -> None:
    search_spec = SearchSpec(
        plugin_path="plugins.craigslist.plugin:CraigslistPlugin",
    )

    assert isinstance(search_spec.plugin, CraigslistPlugin)


def test_search_spec_search_params_property__mock_plugin_with_some_search_params_model__parses_into_model(
    mocker: MockerFixture,
) -> None:
    class SomeSearchParamsModel(BaseSearchParams):
        query: str

    mocker.patch(f"{MODULE}.SearchSpec.plugin", search_param_cls=SomeSearchParamsModel)
    search_spec = SearchSpec(search_params_json='{"query": "test query"}')

    assert search_spec.search_params == SomeSearchParamsModel(query="test query")


def test_channel_notifier_state_active_searches_relationship__search_is_dissociated__record_is_deleted(
    test_db_session: sessionmaker[Session],
) -> None:
    some_notifier_state = make_channel_notifier_state(active_searches=[make_notifier_search()])
    with test_db_session() as session:
        session.add(some_notifier_state)
        session.commit()

        assert session.execute(select(NotifierSearch)).scalars().all()

        some_notifier_state.active_searches = []
        session.commit()

        assert not session.execute(select(NotifierSearch)).scalars().all()


def test_channel_notifier_state_filters_relationship__filter_is_dissociated__record_is_deleted(
    test_db_session: sessionmaker[Session],
) -> None:
    some_notifier_state = make_channel_notifier_state(filters=[make_filter()])
    with test_db_session() as session:
        session.add(some_notifier_state)
        session.commit()

        assert session.execute(select(Filter)).scalars().all()

        some_notifier_state.filters = []
        session.commit()

        assert not session.execute(select(Filter)).scalars().all()
