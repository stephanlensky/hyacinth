from datetime import datetime

from notifier_bot.db.models import DbListing
from notifier_bot.db.session import Session
from notifier_bot.models import Listing, SearchSpec


def get_listings(search_spec: SearchSpec, after_time: datetime) -> list[Listing]:
    with Session() as session:
        listings: list[DbListing] = (
            session.query(DbListing)
            .filter(DbListing.created_at > after_time.timestamp())
            .filter(DbListing.search_spec_json == search_spec.json())
            .order_by(DbListing.created_at.desc())
            .all()
        )
    return [db_listing.to_listing() for db_listing in listings]


def get_last_listing(search_spec: SearchSpec) -> Listing | None:
    with Session() as session:
        db_listing: DbListing | None = (
            session.query(DbListing)
            .filter(DbListing.search_spec_json == search_spec.json())
            .order_by(DbListing.created_at.desc())
            .first()
        )
    return db_listing.to_listing() if db_listing is not None else None


def save_listings(search_spec: SearchSpec, listings: list[Listing]) -> None:
    db_listings = [DbListing.from_listing(search_spec, listing) for listing in listings]
    with Session() as session:
        session.add_all(db_listings)
        session.commit()
