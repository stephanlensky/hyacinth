from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Awaitable, Callable, Generic, Type, TypeVar, get_args

import discord

from hyacinth.exceptions import MissingPluginError
from hyacinth.models import BaseListing, BaseSearchParams, DiscordMessage

SearchParamsType = TypeVar("SearchParamsType", bound=BaseSearchParams)
ListingType = TypeVar("ListingType", bound=BaseListing)

_plugins: list[Plugin] = []
_plugin_path_dict: dict[str, Plugin] = {}


class Plugin(ABC, Generic[SearchParamsType, ListingType]):
    def __init__(self) -> None:
        super().__init__()
        try:
            self.__search_params_type, self.__listing_type = self.__get_params_and_listing_type()
        except (AttributeError, ValueError) as e:
            raise TypeError(
                "plugin class must concretely set generic types for search param and listing class"
            ) from e

    @property
    def path(self) -> str:
        return f"{self.__class__.__module__}:{self.__class__.__name__}"

    @property
    def search_param_cls(self) -> Type[BaseSearchParams]:
        return self.__search_params_type

    @property
    def listing_cls(self) -> Type[BaseListing]:
        return self.__listing_type

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Name used when printing information about this plugin.

        Can include spaces.
        """

    @property
    @abstractmethod
    def command_reference_name(self) -> str:
        """
        Name used when referencing this plugin from bot commands.

        Should not include spaces.
        """

    @abstractmethod
    def polling_interval(self, search_params: SearchParamsType) -> int:
        """Recommended polling interval in seconds"""

    @abstractmethod
    def get_listings(
        self, search_params: SearchParamsType, after_time: datetime, limit: int | None = None
    ) -> list[ListingType]:
        pass

    @abstractmethod
    def format_listing(self, listing: ListingType) -> DiscordMessage:
        pass

    @abstractmethod
    def get_setup_modal(
        self,
        callback: Callable[[discord.Interaction, SearchParamsType], Awaitable[None]],
        # plugins should prefill modal if this is set
        existing_search_params: SearchParamsType | None = None,
    ) -> discord.ui.Modal:
        pass

    def __get_params_and_listing_type(self) -> tuple[Type[BaseSearchParams], Type[BaseListing]]:
        search_params_cls, listing_cls = get_args(
            self.__class__.__orig_bases__[0]  # type: ignore # pylint: disable=no-member
        )
        return search_params_cls, listing_cls


def _get_plugin_from_path(plugin_path: str) -> Type[Plugin]:
    path_parts = plugin_path.split(":")
    if len(path_parts) != 2:
        raise ValueError("Plugin path must be in the format your.plugin.module.path:PluginClass")

    module_path, cls_name = path_parts
    module = importlib.import_module(module_path)
    plugin_cls = getattr(module, cls_name)
    if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, Plugin):
        raise ValueError(
            f"{plugin_path} is not a Plugin! Plugins must inherit from hyacinth.plugin.Plugin."
        )

    return plugin_cls


def register_plugin(plugin_cls: str | Type[Plugin]) -> Plugin:
    """
    Register a source plugin.
    """
    if isinstance(plugin_cls, str):
        plugin_cls = _get_plugin_from_path(plugin_cls)

    if any(type(plugin) is plugin_cls for plugin in _plugins):
        raise ValueError(f"plugin {plugin_cls} already registered")

    plugin = plugin_cls()
    _plugins.append(plugin)
    _plugin_path_dict[plugin.path] = plugin

    return plugin


def get_plugins() -> list[Plugin]:
    return _plugins


def get_plugin(plugin_path: str) -> Plugin:
    try:
        return _plugin_path_dict[plugin_path]
    except KeyError as e:
        raise MissingPluginError(plugin_path) from e
