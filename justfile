set dotenv-load

PYTHON_DIRS := "hyacinth plugins tests"
TEST_RESOURCES_DIR := "tests/resources"

# sample pages used for testing
CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME := "craigslist-search-results-sample.html"
CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME := "craigslist-result-details-sample.html"
MARKETPLACE_SEARCH_RESULT_SAMPLE_FILENAME := "marketplace-search-results-sample.html"
MARKETPLACE_RESULT_DETAILS_SAMPLE_FILENAME := "marketplace-result-details-sample.html"

# plugin data files
CRAIGSLIST_AREAS_URL := "https://reference.craigslist.org/Areas"
CRAIGSLIST_AREAS_FILE := "plugins/craigslist/craigslist_areas.json"
MARKETPLACE_CATEGORIES_URL := "https://www.facebook.com/marketplace/categories"
MARKETPLACE_CATEGORIES_FILE := "plugins/marketplace/categories.html"

# disable metrics for recipes which use hyacinth code directly
export HYACINTH_METRICS_ENABLED := "false"

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
	from hyacinth.util.scraping import get_browser_context
	from plugins.craigslist.client import _get_detail_content, _get_search_results_content, _parse_search_results

	async def main():
		async with get_browser_context() as browser_context:
			page = await browser_context.new_page()

			# search results page
			search_results = await _get_search_results_content(page, 'boston', 'sss', 0)
			with open('{{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME}}', 'w') as f:
				f.write(search_results)
			print('Wrote {{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME}} successfully')

			# listing page
			listing_urls = _parse_search_results(search_results)[1]
			if not listing_urls:
				print('No search results found, skipping listing page')
				sys.exit(0)
			listing_page = await _get_detail_content(page, listing_urls[0])
			with open('{{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME}}', 'w') as f:
				f.write(listing_page)
			print('Wrote {{TEST_RESOURCES_DIR}}/{{CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME}} successfully')

	asyncio.run(main())

# requires active poetry environment
get-marketplace-page-sample:
	#!/usr/bin/env python
	import asyncio
	import sys
	from hyacinth.util.scraping import get_browser_context
	from plugins.marketplace.client import (
		_navigate_to_search_results,
		_navigate_to_listing_and_get_content,
		_parse_search_results
	)

	async def main():
		async with get_browser_context() as browser_context:
			page = await browser_context.new_page()

			# search results page
			await _navigate_to_search_results(page, 'boston', 'motorcycles')
			search_results = await page.content()
			with open('{{TEST_RESOURCES_DIR}}/{{MARKETPLACE_SEARCH_RESULT_SAMPLE_FILENAME}}', 'w') as f:
				f.write(search_results)
			print('Wrote {{TEST_RESOURCES_DIR}}/{{MARKETPLACE_SEARCH_RESULT_SAMPLE_FILENAME}} successfully')

			# listing page
			listing_urls = _parse_search_results(search_results)
			if not listing_urls:
				print('No search results found, skipping listing page')
				sys.exit(0)

			listing_page = await _navigate_to_listing_and_get_content(page, listing_urls[0])
			with open('{{TEST_RESOURCES_DIR}}/{{MARKETPLACE_RESULT_DETAILS_SAMPLE_FILENAME}}', 'w') as f:
				f.write(listing_page)
			print('Wrote {{TEST_RESOURCES_DIR}}/{{MARKETPLACE_RESULT_DETAILS_SAMPLE_FILENAME}} successfully')

	asyncio.run(main())
