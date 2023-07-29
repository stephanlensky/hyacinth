PYTHON_DIRS=hyacinth plugins tests
TEST_RESOURCES_DIR=tests/resources

CRAIGSLIST_SAMPLE_SEARCH_URL=https://boston.craigslist.org/search/sss
CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME=craigslist-search_results-sample.html
CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME=craigslist-result-details-sample.html

all:
	@echo "Error: please specify a target"

install:
	@poetry install --no-dev

install-dev: install
	@poetry install

test:
	poetry run ruff --fix ${PYTHON_DIRS}
	poetry run black ${PYTHON_DIRS}
	poetry run mypy ${PYTHON_DIRS}
	poetry run pytest -rP

run:
	@poetry run hyacinth

get-craigslist-areas:
	@echo "Downloading craigslist areas"
	curl -s -o plugins/craigslist/craigslist_areas.json --compressed \
		"https://reference.craigslist.org/Areas"

get-craigslist-page-sample:
	@echo "Downloading craigslist search results sample"
	curl -s -o ${TEST_RESOURCES_DIR}/${CRAIGSLIST_SEARCH_RESULT_SAMPLE_FILENAME} \
		-X POST "${BROWSERLESS_URL}/content" \
		-H 'Content-Type: application/json' \
		-d '{"url": "${CRAIGSLIST_SAMPLE_SEARCH_URL}"}'
	@echo "Downloading craigslist result details URL"
	results_url=`grep -m 1 -oP '<a class="main" href="https://.*?">' craigslist-page-sample.html | head -1 | grep -oP '(?<=href=")[^"]+'` && \
		echo $$results_url && \
		curl -s -o ${TEST_RESOURCES_DIR}/${CRAIGSLIST_RESULT_DETAILS_SAMPLE_FILENAME} \
			-X POST "${BROWSERLESS_URL}/content" -H 'Content-Type: application/json' \
			-d '{"url": "'$$results_url'"}'
	@echo "Done"
	@echo "Note: some additional sample pages may need to be updated manually. See relevant test file for more information."
