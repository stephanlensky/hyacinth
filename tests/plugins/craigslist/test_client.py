from pytest_mock import MockerFixture

from plugins.craigslist.client import _parse_result_details, _parse_search_results, _search
from plugins.craigslist.models import CraigslistSearchParams

MODULE = "plugins.craigslist.client"


def test__parse_search_results__sample_search_results__returns_some_urls() -> None:
    with open("tests/resources/craigslist-search-results-sample.html") as f:
        content = f.read()

    has_next_page, urls = _parse_search_results(content)

    assert has_next_page
    assert len(urls) > 0
    assert all(url.startswith("https://boston.craigslist.org") for url in urls)
    assert all(url.endswith(".html") for url in urls)


def test__parse_search_results__sample_last_page_search_results__returns_no_next_page() -> None:
    # note, the following file was manually saved from craigslist and will not be refreshed automatically
    with open("tests/resources/craigslist-search-results-last-page-sample.html") as f:
        content = f.read()

    has_next_page, _ = _parse_search_results(content)

    assert not has_next_page


def test__parse_result_details__sample_result_details__returns_updated() -> None:
    with open("tests/resources/craigslist-result-details-sample.html") as f:
        content = f.read()

    listing = _parse_result_details("some-url", content)
    print(listing)


def test__parse_result_details__sample_result_details_with_update__returns_updated_at_different_than_creation_time() -> (
    None
):
    # note, the following file was manually saved from craigslist and will not be refreshed automatically
    with open("tests/resources/craigslist-result-details-with-update-sample.html") as f:
        content = f.read()

    listing = _parse_result_details("some-url", content)
    assert listing.updated_time != listing.creation_time


def test__parse_result_details__sample_result_details_without_price__returns_price_0() -> None:
    # note, the following file was manually saved from craigslist and will not be refreshed automatically
    with open("tests/resources/craigslist-result-details-no-price-sample.html") as f:
        content = f.read()

    listing = _parse_result_details("some-url", content)
    assert listing.price == 0


def test__parse_result_details__sample_result_details_single_image__returns_one_image() -> None:
    # note, the following file was manually saved from craigslist and will not be refreshed automatically
    with open("tests/resources/craigslist-result-details-single-image-sample.html") as f:
        content = f.read()

    listing = _parse_result_details("some-url", content)
    assert len(listing.image_urls) == 1


async def test__search__mocked_content__returns_all_listings_on_page_and_follows_next_page(
    mocker: MockerFixture,
) -> None:
    mocker.patch(f"{MODULE}.scrape")
    mocker.patch(f"{MODULE}._enrich_listing")
    mocker.patch(
        f"{MODULE}._parse_search_results",
        side_effect=[(True, ["some-url-1", "some-url-2"]), (False, ["some-url-3"])],
    )
    mocker.patch(f"{MODULE}._parse_result_details", side_effect=lambda url, _: f"listing for {url}")

    listings = []
    search = _search(CraigslistSearchParams(site="boston", category="sss"))
    async for listing in search:
        listings.append(listing)

    assert listings == [
        "listing for some-url-1",
        "listing for some-url-2",
        "listing for some-url-3",
    ]
