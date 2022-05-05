from celery import Celery

import notifier_bot
from notifier_bot import tasks
from notifier_bot.db.session import connection_string

app = Celery(
    notifier_bot.__name__,
    broker="redis://redis:6379/0",
    backend=f"db+{connection_string}",
    include=[tasks.__name__],
)
