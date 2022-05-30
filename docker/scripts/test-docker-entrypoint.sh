#!/bin/sh
set -e

# format code
echo "Running isort..."
poetry run isort notifier_bot tests migrations
echo "Running black..."
poetry run black notifier_bot tests migrations

# run code tests
echo "Running tests..."
poetry run pytest tests

# run linters
echo "Running mypy..."
poetry run mypy notifier_bot tests migrations
echo "Running pylint..."
poetry run pylint notifier_bot tests migrations
