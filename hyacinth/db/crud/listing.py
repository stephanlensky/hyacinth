from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from hyacinth.db.models import Listing


def get_listings(session: Session, search_spec_id: int, after_time: datetime) -> Sequence[Listing]:
    stmt = (
        select(Listing)
        .where(Listing.creation_time > after_time)
        .where(Listing.search_spec_id == search_spec_id)
        .order_by(Listing.creation_time.asc())
    )

    return session.execute(stmt).scalars().all()


def get_last_listing(session: Session, search_spec_id: int) -> Listing | None:
    stmt = (
        select(Listing)
        .where(Listing.search_spec_id == search_spec_id)
        .order_by(Listing.creation_time.desc())
        .limit(1)
    )

    return session.execute(stmt).scalars().first()
