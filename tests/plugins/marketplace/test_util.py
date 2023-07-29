from plugins.marketplace.util import get_categories


def test_get_categories__with_file_present__returns_categories() -> None:
    get_categories.cache_clear()
    categories = get_categories()

    assert len(categories) > 1000
