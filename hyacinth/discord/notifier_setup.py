from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING, Any

from discord import Message

from hyacinth.db.notifier import save_notifier as save_notifier_to_db
from hyacinth.discord.thread_interaction import FMT_USER, ThreadInteraction
from hyacinth.models import SearchSpec
from hyacinth.notifier import DiscordNotifier
from hyacinth.plugin import Plugin

if TYPE_CHECKING:
    # avoid circular import
    from hyacinth.discord.discord_bot import DiscordNotifierBot

_logger = logging.getLogger(__name__)


class NotifierSetupInteraction(ThreadInteraction):
    def __init__(
        self, bot: DiscordNotifierBot, initiating_message: Message, plugin: Plugin
    ) -> None:
        super().__init__(
            bot,
            initiating_message,
            thread_title=f"Create a new {plugin.display_name} notifier",
            first_message=f"Hi {FMT_USER}! Let's get that set up for you.",
            questions=plugin.get_setup_questions(),
        )
        self.plugin = plugin

    async def finish(self) -> dict[str, Any]:
        try:
            created_notifier = self.configure_notifier()
        except Exception:
            await self.send(
                f"Sorry {FMT_USER}! Something went wrong while configuring the notifier for this"
                f" channel. ```{traceback.format_exc()}```"
            )
            await super().finish()
            raise

        # if this is the first search set up on this channel, the notifier starts paused. add some
        # helpful information about that for the user if necessary.
        created_notifier_part = (
            "\n\nNotifications are currently paused. When you are done configuring your desired"
            " filter rules, start sending notifications with `$start`."
            if created_notifier
            else ""
        )
        await self.send(
            f"{self.bot.thank()} {FMT_USER}! I've set up a search for new"
            f" {self.plugin.display_name} listings on this channel.{created_notifier_part}"
        )

        return await super().finish()

    def configure_notifier(self) -> bool:
        search_spec = SearchSpec(
            plugin_path=self.plugin.path,
            search_params=self.plugin.search_param_cls.parse_obj(self._answers),
        )
        _logger.debug(f"Parsed search spec from answers {search_spec}")

        channel = self.initiating_message.channel
        created_notifier = False
        if channel.id not in self.bot.notifiers:
            _logger.info(f"Creating notifier for channel {channel.id}")
            self.bot.notifiers[channel.id] = DiscordNotifier(
                channel, self.bot.monitor, DiscordNotifier.Config(paused=True)
            )
            created_notifier = True
        self.bot.notifiers[channel.id].create_search(search_spec)
        save_notifier_to_db(self.bot.notifiers[channel.id])
        return created_notifier
