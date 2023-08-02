from datetime import datetime

from hyacinth.db.models import ChannelNotifierState, Filter, Listing, NotifierSearch, SearchSpec
from hyacinth.enums import RuleType

DEFAULT_SEARCH_SPEC_PLUGIN_PATH = "some_plugin_path"
DEFAULT_SEARCH_SPEC_SEARCH_PARAMS_JSON = "{}"


def make_search_spec(
    plugin_path: str = DEFAULT_SEARCH_SPEC_PLUGIN_PATH,
    search_params_json: str = DEFAULT_SEARCH_SPEC_SEARCH_PARAMS_JSON,
) -> SearchSpec:
    return SearchSpec(
        plugin_path=plugin_path,
        search_params_json=search_params_json,
    )


DEFAULT_NOTIFIER_SEARCH_NAME = "some_search_name"
DEFAULT_NOTIFIER_SEARCH_LAST_NOTIFIED = datetime.now()


def make_notifier_search(
    name: str = DEFAULT_NOTIFIER_SEARCH_NAME,
    last_notified: datetime = DEFAULT_NOTIFIER_SEARCH_LAST_NOTIFIED,
    search_spec: SearchSpec | None = None,
) -> NotifierSearch:
    if search_spec is None:
        search_spec = make_search_spec()

    return NotifierSearch(
        name=name,
        last_notified=last_notified,
        search_spec=search_spec,
    )


DEFAULT_FILTER_FIELD = "some_filter_field"
DEFAULT_FILTER_RULE_TYPE = RuleType.OR
DEFAULT_FILTER_RULE_EXPR = "some_filter_rule_expr"


def make_filter(
    field: str = DEFAULT_FILTER_FIELD,
    rule_type: RuleType = DEFAULT_FILTER_RULE_TYPE,
    rule_expr: str = DEFAULT_FILTER_RULE_EXPR,
) -> Filter:
    return Filter(
        field=field,
        rule_type=rule_type,
        rule_expr=rule_expr,
    )


DEFAULT_CHANNEL_NOTIFIER_STATE_CHANNEL_ID = 1
DEFAULT_CHANNEL_NOTIFIER_STATE_NOTIFICATION_FREQUENCY_SECONDS = 60


def make_channel_notifier_state(
    id: int | None = None,
    channel_id: int = DEFAULT_CHANNEL_NOTIFIER_STATE_CHANNEL_ID,
    notification_frequency_seconds: int = DEFAULT_CHANNEL_NOTIFIER_STATE_NOTIFICATION_FREQUENCY_SECONDS,
    active_searches: list[NotifierSearch] | None = None,
    filters: list[Filter] | None = None,
) -> ChannelNotifierState:
    if active_searches is None:
        active_searches = []
    if filters is None:
        filters = []

    return ChannelNotifierState(
        id=id,
        channel_id=channel_id,
        active_searches=active_searches,
        notification_frequency_seconds=notification_frequency_seconds,
        filters=filters,
    )


DEFAULT_LISTING_LISTING_JSON = "{}"
DEFAULT_LISTING_CREATION_TIME = datetime.now()


def make_listing(
    search_spec: SearchSpec | None = None,
    listing_json: str = DEFAULT_LISTING_LISTING_JSON,
    creation_time: datetime = DEFAULT_LISTING_CREATION_TIME,
) -> Listing:
    if search_spec is None:
        search_spec = make_search_spec()

    return Listing(
        listing_json=listing_json,
        search_spec=search_spec,
        creation_time=creation_time,
    )
