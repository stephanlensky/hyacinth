import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from discord import Message, Reaction, Thread

if TYPE_CHECKING:
    from notifier_bot.discord.discord_bot import DiscordNotifierBot

FMT_USER = "{user}"
DEFAULT_ERROR_RESPONSE = f"Sorry {FMT_USER}, I didn't recognize that. Please try again."

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Question:
    key: str
    prompt: str
    validator: Callable[[str], Any] | None
    error_response: str | None = None
    accepted_reaction_responses: tuple[str] = ()


class ThreadInteraction:
    def __init__(
        self,
        bot: "DiscordNotifierBot",
        initiating_message: Message,
        thread_title: str,
        first_message: str | None,
        questions: list[Question],
    ) -> None:
        self.bot = bot
        self.initiating_message = initiating_message
        self.initiating_user = initiating_message.author
        self.thread_title = thread_title
        self.first_message = first_message
        self.questions = questions

        self.unaswered_questions = list(questions)
        self._answers: dict[str, Any] = {}

        self.thread: Thread | None = None

        if not self.questions:
            raise ValueError("Must supply at least one question!")

    @property
    def completed(self) -> bool:
        return not self.unaswered_questions

    @property
    def answers(self) -> dict[str, Any]:
        return self._answers

    @answers.setter
    def answers(self, value: dict[str, Any]) -> None:
        # attempt to put supplied answers in the right order before adding
        question_keys = [q.key for q in self.questions]
        answer_keys = sorted(value.keys(), key=question_keys.index)
        # add all answers
        for k in answer_keys:
            self._add_answer(value[k])

    @property
    def thread_id(self) -> int:
        if self.thread is None:
            raise ValueError("Thread is not initialized! must call begin method.")
        return self.thread.id

    def _format(self, message: str) -> str:
        return message.format_map({FMT_USER[1:-1]: self.initiating_user.mention})

    def _ack(self) -> str:
        return self._format(f"{self.bot.thank()} {FMT_USER}")

    async def send(self, message: str) -> None:
        if self.thread is None:
            return
        formatted_message = self._format(message)
        await self.thread.send(formatted_message)

    async def begin(self) -> None:
        self.thread = await self.initiating_message.create_thread(
            name=self.thread_title, auto_archive_duration=60
        )
        if self.first_message:
            await self.send(self.first_message)
        await self.prompt()

    async def finish(self) -> dict[str, Any]:
        if self.thread is not None:
            await self.thread.edit(archived=True)
        return self._answers

    async def on_message(self, message: Message) -> None:
        await self._accept_answer(message.content)

    async def on_reaction(self, reaction: Reaction) -> None:
        question = self.unaswered_questions[0]
        if reaction.emoji not in question.accepted_reaction_responses:
            return
        await self._accept_answer(reaction.emoji)

    async def _accept_answer(self, answer: str) -> None:
        question = self.unaswered_questions[0]
        if not self._add_answer(answer):
            error_response = DEFAULT_ERROR_RESPONSE
            if question.error_response:
                error_response = question.error_response
            await self.send(error_response)
            return

        if self.unaswered_questions:
            await self.prompt(ack=True)

    def _add_answer(self, answer: str) -> bool:
        question = self.unaswered_questions[0]
        if question.validator is not None:
            try:
                validated = question.validator(answer)  # type: ignore
            except Exception as e:
                _logger.debug(f"Validator threw exception {str(e)}")
                return False

        self._answers[question.key] = validated
        self.unaswered_questions.pop(0)
        return True

    async def prompt(self, ack: bool = False) -> None:
        if ack:
            ack_part = f"{self._ack()}. "
        else:
            ack_part = ""

        question = self.unaswered_questions[0]
        await self.send(f"{ack_part}{question.prompt}")
