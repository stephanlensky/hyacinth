from __future__ import annotations

from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import declarative_base

from notifier_bot.models import Listing, SearchSpec

Base = declarative_base()


class DbListing(Base):
    __tablename__ = "listing"

    id = Column(Integer, primary_key=True)
    created_at = Column(Integer, index=True, nullable=False)
    search_spec_json = Column(Text, nullable=False)
    listing_json = Column(Text, nullable=False)

    def to_listing(self) -> Listing:
        return Listing.parse_raw(self.listing_json)  # type: ignore

    @classmethod
    def from_listing(cls, search_spec: SearchSpec, listing: Listing) -> DbListing:
        return cls(
            created_at=int(listing.created_at.timestamp()),
            search_spec_json=search_spec.json(),
            listing_json=listing.json(),
        )


class DbDiscordNotifierConfig(Base):
    __tablename__ = "notifier"

    channel_id = Column(Integer, primary_key=True)
    config_json = Column(Text)
