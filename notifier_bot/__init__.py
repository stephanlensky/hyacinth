import logging
import sys

from notifier_bot.settings import get_settings


def _configure_logging() -> None:
    settings = get_settings()
    notifier_bot_root_logger = logging.getLogger(__name__)
    notifier_bot_root_logger.propagate = False
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(settings.log_format, settings.log_date_format)
    stdout_handler.setFormatter(formatter)
    notifier_bot_root_logger.addHandler(stdout_handler)
    notifier_bot_root_logger.setLevel(settings.log_level)


_configure_logging()
