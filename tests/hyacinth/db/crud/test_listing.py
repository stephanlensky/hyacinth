from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from hyacinth.db.crud.listing import get_last_listing, get_listings
from tests.sample_data import make_listing, make_search_spec


def test_get_listings__multiple_listings__returns_correctly_ordered_and_filtered_result(
    test_db_session: sessionmaker[Session],
) -> None:
    some_search_spec = make_search_spec()
    some_listings = [
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 8)),
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 3)),
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 4)),
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 1)),
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 9)),
    ]
    with test_db_session() as session:
        session.add_all(some_listings)
        session.commit()

        assert get_listings(session, some_search_spec.id, after_time=datetime(2023, 1, 4)) == [
            some_listings[0],
            some_listings[4],
        ]


def test_get_last_listing__multiple_listings__returns_most_recent_listing(
    test_db_session: sessionmaker[Session],
) -> None:
    some_search_spec = make_search_spec()
    some_listings = [
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 4)),
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 9)),
        make_listing(search_spec=some_search_spec, creation_time=datetime(2023, 1, 1)),
    ]

    with test_db_session() as session:
        session.add_all(some_listings)
        session.commit()

        assert get_last_listing(session, some_search_spec.id) == some_listings[1]


def test_get_last_listing__no_listings__returns_none(
    test_db_session: sessionmaker[Session],
) -> None:
    with test_db_session() as session:
        assert get_last_listing(session, 1) is None
