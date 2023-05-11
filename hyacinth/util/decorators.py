import logging
from typing import Any, Awaitable, Callable

import wrapt


def log_exceptions(logger: logging.Logger) -> Callable[..., Awaitable[Any]]:
    """
    A decorator that wraps the passed in function and logs any exceptions that occur.
    """

    @wrapt.decorator
    async def wrapper(wrapped, instance, args, kwargs) -> Any:  # type: ignore
        try:
            return await wrapped(*args, **kwargs)
        except:
            logger.exception(f"Exception caught in {wrapped.__name__}")
            raise

    return wrapper
