This plugin periodically polls a Craigslist "For sale" category on a given regional site.

## Search configuration

Two fields are available for configuration when creating a new Craigslist search.

**Site**

: The regional site to poll. This is the first part of the Craigslist domain, e.g. `boston` in [boston.craigslist.org](https://boston.craigslist.org) or `sfbay` in [sfbay.craigslist.org](https://sfbay.craigslist.org).

**Category**

: The category to poll. Must be one of the subcategories under the "for sale" section on the homepage, or `sss` to search everything. Category should be entered as the 3-digit code at the end of the Craigslist URL when clicking into this category.

    For example, clicking into [motorcycles](https://sfbay.craigslist.org/search/mca) brings you to `https://sfbay.craigslist.org/search/mca/`, so `mca` is the code for this category.
