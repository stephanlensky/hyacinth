from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from hyacinth.db.models import NotifierSearch, SearchSpec

if TYPE_CHECKING:
    from hyacinth.notifier import ListingNotifier

_logger = logging.getLogger(__name__)


def add_notifier_search(
    session: Session,
    notifier: ListingNotifier,
    name: str,
    search_spec: SearchSpec,
    last_notified: datetime,
) -> NotifierSearch:
    _logger.debug("Creating new notifier search")
    notifier_search = NotifierSearch(
        notifier_id=notifier.config.id,
        name=name,
        search_spec=search_spec,
        last_notified=last_notified,
    )
    session.add(notifier_search)
    return notifier_search
