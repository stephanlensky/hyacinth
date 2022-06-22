from celery import Celery

import hyacinth
from hyacinth.db.session import connection_string

app = Celery(
    hyacinth.__name__,
    broker="redis://redis:6379/0",
    backend=f"db+{connection_string}",
    include=[f"{hyacinth.__name__}.tasks"],
)
