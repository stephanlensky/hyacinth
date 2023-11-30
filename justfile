set dotenv-load

PYTHON_DIRS := "hyacinth plugins tests"
TEST_RESOURCES_DIR := "tests/resources"

# sample pages used for testing
CRAIGSLIST_SAMPLE_SEARCH_URL := "https://boston.craigslist.org/search/sss"
CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME := "craigslist-search-results-sample.html"
CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME := "craigslist-result-details-sample.html"

# plugin data files
CRAIGSLIST_AREAS_URL := "https://reference.craigslist.org/Areas"
CRAIGSLIST_AREAS_FILE := "plugins/craigslist/craigslist_areas.json"
MARKETPLACE_CATEGORIES_URL := "https://www.facebook.com/marketplace/categories"
MARKETPLACE_CATEGORIES_FILE := "plugins/marketplace/categories.html"

# disable metrics for recipes which use hyacinth code directly
export METRICS_ENABLED := "false"

default:
    just --list

install:
	@poetry install --only main

install-dev:
	@poetry install

test:
	poetry run ruff --fix {{PYTHON_DIRS}}
	poetry run black {{PYTHON_DIRS}}
	poetry run mypy {{PYTHON_DIRS}}
	poetry run pytest -rP

run:
	@poetry run hyacinth

docs:
	@poetry run mkdocs serve

get-craigslist-areas:
	@echo "Downloading craigslist areas"
	curl -s -o {{CRAIGSLIST_AREAS_FILE}} --compressed \
		"{{CRAIGSLIST_AREAS_URL}}"

get-marketplace-categories:
	@echo "Downloading marketplace categories"
	curl -s -o {{MARKETPLACE_CATEGORIES_FILE}} \
		-X POST "${BROWSERLESS_URL}/content" \
		-H 'Content-Type: application/json' \
		-d '{"url": "{{MARKETPLACE_CATEGORIES_URL}}"}'

# requires active poetry environment
get-craigslist-page-sample:
	#!/usr/bin/env python
	import asyncio
	import sys
	from plugins.craigslist.client import _get_detail_content, _get_search_results_content, _parse_search_results

	# search results page
	search_results = asyncio.run(_get_search_results_content('boston','sss',0))
	with open('{{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME}}', 'w') as f:
		f.write(search_results)
	print('Wrote {{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME}} successfully')

	# listing page
	if not search_results:
		print('No search results found, skipping listing page')
		sys.exit(0)
	listing_url = _parse_search_results(search_results)[1][0]
	listing_page = asyncio.run(_get_detail_content(listing_url))
	with open('{{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME}}', 'w') as f:
		f.write(listing_page)
	print('Wrote {{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME}} successfully')
