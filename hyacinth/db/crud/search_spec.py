import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hyacinth.db.models import SearchSpec


def add_search_spec(
    session: Session, plugin_path: str, search_params_json: dict[str, Any]
) -> SearchSpec:
    dumped_json = json.dumps(search_params_json)

    # check if there is already a search spec with this plugin path and search params
    stmt = (
        select(SearchSpec)
        .where(SearchSpec.plugin_path == plugin_path)
        .where(SearchSpec.search_params_json == dumped_json)
    )
    if (existing_spec := session.execute(stmt).scalars().first()) is not None:
        return existing_spec.id

    # otherwise create a new search spec
    spec = SearchSpec(
        plugin_path=plugin_path,
        search_params_json=dumped_json,
    )
    session.add(spec)
    session.commit()

    return spec
