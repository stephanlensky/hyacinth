import logging

from notifier_bot.settings import get_settings

settings = get_settings()
notifier_bot_root_logger = logging.getLogger(__name__)
notifier_bot_root_logger.setLevel(settings.log_level)
