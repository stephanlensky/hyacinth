import json

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from hyacinth.db.crud.search_spec import add_search_spec
from hyacinth.db.models import SearchSpec
from tests.sample_data import make_search_spec

SOME_PLUGIN_PATH = "some_plugin_path"
SOME_SEARCH_PARAMS_JSON = {"some": "search_params_json"}


def test_add_search_spec__spec_does_not_exist__creates_new_search_spec(
    test_db_session: sessionmaker[Session],
) -> None:

    with test_db_session() as session:
        add_search_spec(session, SOME_PLUGIN_PATH, SOME_SEARCH_PARAMS_JSON)
        session.commit()

        search_spec = session.execute(select(SearchSpec)).scalars().one()
        assert search_spec.plugin_path == SOME_PLUGIN_PATH
        assert search_spec.search_params_json == json.dumps(SOME_SEARCH_PARAMS_JSON)


def test_add_search_spec__identical_spec_exists__does_not_create_new_search_spec(
    test_db_session: sessionmaker[Session],
) -> None:
    existing_search_spec = make_search_spec(
        plugin_path=SOME_PLUGIN_PATH, search_params_json=json.dumps(SOME_SEARCH_PARAMS_JSON)
    )

    with test_db_session() as session:
        session.add(existing_search_spec)
        session.commit()

        add_search_spec(session, SOME_PLUGIN_PATH, SOME_SEARCH_PARAMS_JSON)
        session.commit()

        search_spec = session.execute(select(SearchSpec)).scalars().one()
        assert search_spec.id == existing_search_spec.id
