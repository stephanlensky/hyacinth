#!/bin/sh
poetry run celery -A notifier_bot.tasks worker --loglevel=INFO
