from plugins.marketplace.client import _parse_result_details, _parse_search_results


def test__parse_search_results__sample_search_results__returns_some_urls() -> None:
    with open("tests/resources/marketplace-search-results-sample.html") as f:
        content = f.read()

    urls = _parse_search_results(content)

    assert len(urls) > 0


def test__parse_result_details__sample_result_details__parsed_result_is_valid() -> None:
    with open("tests/resources/marketplace-result-details-sample.html") as f:
        content = f.read()

    listing = _parse_result_details("https://www.facebook.com/marketplace/item/123456789", content)
    print(listing)
