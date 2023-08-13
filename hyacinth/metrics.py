import logging
import time
from functools import cache
from threading import Lock

import httpx
from apscheduler.triggers.interval import IntervalTrigger

from hyacinth.exceptions import MetricsWriteError
from hyacinth.scheduler import get_threadpool_scheduler
from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)

__buffer_lock = Lock()


METRIC_SCRAPE_COUNT = "hyacinth_scrape_count"
METRIC_POLL_JOB_EXECUTION_COUNT = "hyacinth_poll_job_execution_count"


@cache
def __get_buffer() -> list[str]:
    return []


def start_metrics_write_task() -> None:
    if not settings.metrics_enabled:
        _logger.info("Metrics disabled, will not start metrics write task")
        return
    scheduler = get_threadpool_scheduler()
    scheduler.add_job(flush_buffer, trigger=IntervalTrigger(seconds=30))
    _logger.info("Scheduled metrics write task")


def flush_buffer() -> None:
    if not settings.metrics_enabled:
        return
    buffer = __get_buffer()
    if not buffer:
        return

    _logger.debug(f"Writing {len(buffer)} metrics")
    content = "\n".join(buffer)
    with __buffer_lock:
        try:
            r = httpx.post(
                f"{settings.victoria_metrics_host}/api/v1/import/prometheus", content=content
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise MetricsWriteError() from e

        buffer.clear()
    _logger.debug("Metrics written successfully")


def write_metric(
    metric_name: str, value: int | float, labels: dict[str, str] | None = None
) -> None:
    if not settings.metrics_enabled:
        return
    buffer = __get_buffer()

    label_data = ""
    if labels:
        label_parts = (f'{k}="{v}"' for k, v in labels.items())
        label_data = f"{{{','.join(label_parts)}}}"
    data = f"{metric_name}{label_data} {value} {int(time.time())}"
    with __buffer_lock:
        buffer.append(data)
    _logger.debug(f"Saved metric {metric_name}={value}, {labels=}")
