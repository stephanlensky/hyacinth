import logging
import traceback
from datetime import datetime
from pathlib import Path

from hyacinth.exceptions import ParseError
from hyacinth.settings import get_settings

_logger = logging.getLogger(__name__)
settings = get_settings()


def save_poll_failure_report(e: Exception):
    """
    Save a poll failure report to a file.
    """
    if not settings.save_crash_reports:
        return

    fname = (
        Path(settings.crash_report_save_folder) / f"poll_failure_{datetime.now().isoformat()}.txt"
    )
    _logger.info(f"Saving error report to {fname}")
    fname.parent.mkdir(parents=True, exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
        if isinstance(e, ParseError):
            f.write("\n\nThis error was caused while parsing the following content:\n\n")
            f.write(e.page_content)
