from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING

import sqlalchemy
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from hyacinth.enums import RuleType

if TYPE_CHECKING:
    from hyacinth.models import BaseListing, BaseSearchParams
    from hyacinth.plugin import Plugin


class Base(DeclarativeBase):
    pass


class Listing(Base):
    """
    A Listing is a single result from a search.

    Listings must contain a creation time, indicating the time at which the posting was created.
    This enables both plugins to efficiently scan of the listing source and the notifier to
    efficiently check the database for new listings.

    All other informational fields about the listing are plugin-specific and are stored as a JSON
    blob. Common fields might include a title, URL, price, images, and description, but plugin
    authors are free to store whatever information they want.
    """

    __tablename__ = "listing"

    id: Mapped[int] = mapped_column(primary_key=True)

    search_spec_id: Mapped[int] = mapped_column(ForeignKey("searchspec.id"), index=True)
    listing_json: Mapped[str] = mapped_column()  # details of listing are plugin-specific
    # post date of the listing itself
    creation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # when we saw it
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    search_spec: Mapped[SearchSpec] = relationship("SearchSpec")

    @classmethod
    def from_base_listing(cls, base_listing: BaseListing, search_spec_id: int) -> Listing:
        return cls(
            search_spec_id=search_spec_id,
            listing_json=base_listing.json(),
            creation_time=base_listing.creation_time,
        )


class SearchSpec(Base):
    """
    A SearchSpec is a single search against a single plugin source.

    SearchSpecs contain a plugin path and a plugin-specific JSON blob of search parameters. The
    plugin path is used to determine which plugin to use to poll the source, and the search
    parameters are passed to the plugin to determine what to search for.

    If multiple notifiers are watching the same search, they will all share a reference to the same
    SearchSpec, enabling efficient batching when polling sources.
    """

    __tablename__ = "searchspec"

    id: Mapped[int] = mapped_column(primary_key=True)
    plugin_path: Mapped[str] = mapped_column(index=True)
    search_params_json: Mapped[str] = mapped_column()  # search params are plugin-specific

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    @cached_property
    def plugin(self) -> Plugin:
        from hyacinth.plugin import get_plugin

        return get_plugin(self.plugin_path)

    @cached_property
    def search_params(self) -> BaseSearchParams:
        plugin = self.plugin

        return plugin.search_param_cls.parse_raw(self.search_params_json)


class NotifierSearch(Base):
    """
    A NotifierSearch is a single search that a notifier is watching.

    It encapsulates both a SearchSpec that the notifier is watching and the last time that the
    notifier notified the user about a listing from that search.
    """

    __tablename__ = "notifiersearch"

    id: Mapped[int] = mapped_column(primary_key=True)

    # user-specified name for this search that can be referenced with /notifier commands
    name: Mapped[str]

    notifier_id: Mapped[int] = mapped_column(ForeignKey("channelnotifier.id"), index=True)
    last_notified: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    search_spec_id: Mapped[int] = mapped_column(ForeignKey("searchspec.id"), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    notifier: Mapped[ChannelNotifierState] = relationship(
        "ChannelNotifierState", back_populates="active_searches"
    )
    search_spec: Mapped[SearchSpec] = relationship("SearchSpec")


class Filter(Base):
    """
    A Filter is a single filter that can be applied to a notifier.

    Filters are applied to listings after they are collected by the plugin source, but before they
    are sent to the user. If a listing matches all of the filters, it will be sent to the user.
    """

    __tablename__ = "filter"

    id: Mapped[int] = mapped_column(primary_key=True)
    notifier_id: Mapped[int] = mapped_column(ForeignKey("channelnotifier.id"), index=True)

    field: Mapped[str]
    rule_type: Mapped[RuleType] = mapped_column(
        # note: native enums seem to have some issues on this version of sqlalchemy
        sqlalchemy.Enum(RuleType, native_enum=False),
        index=True,
    )
    rule_expr: Mapped[str]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    notifier: Mapped[ChannelNotifierState] = relationship("ChannelNotifierState")


class ChannelNotifierState(Base):
    """
    A ChannelNotifierState is the state of a single channel notifier.

    During normal operation, the values in this state are stored in memory. However, when
    configuration changes are made, the state is persisted to the database so that it can be
    restored when the bot restarts.
    """

    __tablename__ = "channelnotifier"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(unique=True)
    notification_frequency_seconds: Mapped[int]
    paused: Mapped[bool] = mapped_column(default=False)
    home_latitude: Mapped[float | None]
    home_longitude: Mapped[float | None]
    active_searches: Mapped[list[NotifierSearch]] = relationship(
        "NotifierSearch", back_populates="notifier", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    filters: Mapped[list[Filter]] = relationship(
        "Filter", back_populates="notifier", cascade="all, delete-orphan"
    )
