#!/bin/sh
poetry run celery -A hyacinth.tasks worker --loglevel=INFO
