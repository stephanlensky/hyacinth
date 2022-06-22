#!/bin/sh
set -e

# format code
echo "Running isort..."
poetry run isort hyacinth tests migrations
echo "Running black..."
poetry run black hyacinth tests migrations

# run code tests
echo "Running tests..."
poetry run pytest tests

# run linters
echo "Running mypy..."
poetry run mypy hyacinth tests migrations
echo "Running pylint..."
poetry run pylint hyacinth tests migrations
