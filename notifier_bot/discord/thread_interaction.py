from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from discord import Message, Thread

if TYPE_CHECKING:
    from notifier_bot.discord.discord_bot import DiscordNotifierBot

FMT_USER = "{user}"
DEFAULT_ERROR_RESPONSE = f"Sorry {FMT_USER}, I didn't recognize that. Please try again."


@dataclass(frozen=True)
class Question:
    key: str
    prompt: str
    validator: Callable[[Message], Any]
    error_response: str | None = None


class ThreadInteraction:
    def __init__(
        self,
        bot: "DiscordNotifierBot",
        initiating_message: Message,
        thread_title: str,
        first_message: str,
        questions: list[Question],
    ) -> None:
        self.bot = bot
        self.initiating_message = initiating_message
        self.initiating_user = initiating_message.author
        self.thread_title = thread_title
        self.first_message = first_message
        self.questions = questions

        self.unaswered_questions = list(questions)
        self.answers: dict[str, Any] = {}

        self.thread: Thread | None = None

        if not self.questions:
            raise ValueError("Must supply at least one question!")

    @property
    def completed(self) -> bool:
        return not self.unaswered_questions

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
        await self.send(self.first_message)
        await self.prompt()

    async def finish(self) -> dict[str, Any]:
        if self.thread is not None:
            await self.thread.edit(archived=True)
        return self.answers

    async def on_message(self, message: Message) -> None:
        question = self.unaswered_questions[0]
        try:
            validated = question.validator(message)  # type: ignore
        except Exception:
            error_response = DEFAULT_ERROR_RESPONSE
            if question.error_response:
                error_response = question.error_response
            await self.send(error_response)
            return

        self.answers[question.key] = validated
        self.unaswered_questions.pop(0)
        if self.unaswered_questions:
            await self.prompt(ack=True)

    async def prompt(self, ack: bool = False) -> None:
        if ack:
            ack_part = f"{self._ack()}. "
        else:
            ack_part = ""

        question = self.unaswered_questions[0]
        await self.send(f"{ack_part}{question.prompt}")
