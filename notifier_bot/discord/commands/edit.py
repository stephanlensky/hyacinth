from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from discord import Message

from notifier_bot.db.notifier import save_notifier
from notifier_bot.discord.thread_interaction import FMT_USER, Question, ThreadInteraction
from notifier_bot.models import Rule, StringFieldFilter
from notifier_bot.notifier import ListingNotifier

if TYPE_CHECKING:
    from notifier_bot.discord.discord_bot import DiscordNotifierBot


_logger = logging.getLogger(__name__)


class EditStringFilterInteraction(ThreadInteraction):
    def __init__(
        self, bot: "DiscordNotifierBot", initiating_message: Message, filter_: StringFieldFilter
    ) -> None:
        self.filter_ = filter_

        available_rules_parts: list[str] = []
        if filter_.rules:
            rules_repr = "\n".join(
                f"{i+1}. {repr(rule.expression)}" for i, rule in enumerate(filter_.rules)
            )
            available_rules_parts.append(f"Boolean filter rules:\n```{rules_repr}```")
        if filter_.preremoval_rules:
            preremoval_rules_repr = "\n".join(
                f"{i+1+len(filter_.rules)}. {preremoval_rule}"
                for i, preremoval_rule in enumerate(filter_.preremoval_rules)
            )
            available_rules_parts.append(f"Preremoval rules:\n```{preremoval_rules_repr}```")
        if filter_.disallowed_words:
            disallowed_words_repr = "\n".join(
                f"{i+1+len(filter_.rules)+len(filter_.preremoval_rules)}. {word}"
                for i, word in enumerate(filter_.disallowed_words)
            )
            available_rules_parts.append(f"Disallowed words:\n```{disallowed_words_repr}```")
        available_rules_part = "".join(available_rules_parts)

        super().__init__(
            bot,
            initiating_message,
            thread_title="Edit a filter",
            first_message=None,
            questions=[
                Question(
                    key="selection",
                    prompt=(
                        f"Hi {FMT_USER}! Which filter would you like to"
                        f" edit?\n\n{available_rules_part}"
                    ),
                    validator=self.validate_choice,
                ),
                Question(
                    key="requested_change",
                    prompt=(
                        "What would you like to change this filter to? If you'd like to delete the"
                        " filter, just react with an \u274C (`:x:`)."
                    ),
                    validator=self.validate_change,
                    accepted_reaction_responses=("\u274C",),  # :x:
                ),
            ],
        )

    async def finish(self) -> dict[str, Any]:
        selection = self.answers["selection"]
        requested_change = self.answers["requested_change"]
        should_delete = requested_change == ""

        choice_type: str
        original_repr: str
        change_repr: str = requested_change
        if selection < len(self.filter_.rules):
            choice_type = "boolean filter rule"
            original_repr = repr(self.filter_.rules[selection].expression)
            change_repr = repr(requested_change.expression)
            if should_delete:
                self.filter_.rules.pop(selection)
            else:
                self.filter_.rules[selection] = requested_change

        elif selection < len(self.filter_.rules) + len(self.filter_.preremoval_rules):
            selection -= len(self.filter_.rules)
            choice_type = "preremoval rule"
            original_repr = self.filter_.preremoval_rules[selection]
            if should_delete:
                self.filter_.preremoval_rules.pop(selection)
            else:
                self.filter_.preremoval_rules[selection] = requested_change

        else:
            selection -= len(self.filter_.rules) + len(self.filter_.preremoval_rules)
            choice_type = "disallowed word"
            original_repr = self.filter_.disallowed_words[selection]
            if should_delete:
                self.filter_.disallowed_words.pop(selection)
            else:
                self.filter_.disallowed_words[selection] = requested_change

        save_notifier(self.bot.notifiers[self.initiating_message.channel.id])
        if should_delete:
            await self.send(
                f"{self.bot.affirm()} {FMT_USER}, I've deleted the following"
                f" {choice_type}:```{original_repr}```"
            )
        else:
            await self.send(
                f"{self.bot.affirm()} {FMT_USER}, I've changed the following"
                f" {choice_type}:```{original_repr} -> {change_repr}```"
            )

        return await super().finish()

    def validate_choice(self, v: str) -> int:
        try:
            selection = int(v) - 1
        except ValueError:
            raise

        max_selection = (
            len(self.filter_.rules)
            + len(self.filter_.preremoval_rules)
            + len(self.filter_.disallowed_words)
        )
        if selection < 0 or selection >= max_selection:
            raise ValueError(f"selection {selection} must be >=1 and <={max_selection}")

        return selection

    def validate_change(self, v: str) -> str | Rule:
        if v == "\u274C":
            return ""

        if self.answers["selection"] < len(self.filter_.rules):
            return Rule(rule_str=v)

        return v


async def edit(
    bot: DiscordNotifierBot, message: Message, notifier: ListingNotifier, field: str
) -> None:
    _logger.debug(f"Editing filters for field {field}")
    if field not in notifier.config.filters:
        await message.channel.send(
            f"Sorry {message.author.mention}, there are not currently any filters configured for"
            f" the `{field}` field. Try adding some with `$filter`!"
        )
        return
    field_filter = notifier.config.filters[field]

    if isinstance(field_filter, StringFieldFilter):
        edit_interaction = EditStringFilterInteraction(bot, message, field_filter)
        await edit_interaction.begin()
        bot.active_threads[edit_interaction.thread_id] = edit_interaction
    else:
        raise NotImplementedError("filter type not implemented")
