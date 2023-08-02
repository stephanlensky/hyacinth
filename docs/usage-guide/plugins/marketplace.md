The `marketplace` plugin connects Hyacinth to [Facebook Marketplace](https://www.facebook.com/marketplace).

## Search configuration

Two fields are available for configuration when creating a new Marketplace search.

**Location**

: The location to search. Facebook Marketplace identifies locations either by a "vanity URL" (for larger cities) or by a numerical ID. To identify the vanity URL or ID for a given location, navigate to marketplace in a web browser and filter by your desired location. Then, in the URL, the URL part directly after `/marketplace/` is the vanity URL or ID.

    For example, in the URL `https://www.facebook.com/marketplace/boston`, `boston` is the vanity URL. In the URL `https://www.facebook.com/marketplace/107620962593801`, `107620962593801` is the location ID. Either can be used when configuring a search.

**Category**

: The category to search. Similar to locations, categories are identified by either an "SEO URL" or a numerical ID.

    As previously, the URL part or ID can be identified by searching for the category in your browser and picking it out of the URL. For example, In the URL `https://www.facebook.com/marketplace/boston/vehicles`, `vehicles` is the SEO URL. In the URL `https://www.facebook.com/marketplace/boston/731115930902473`, `731115930902473` is the category ID. Either can be used when configuring a search.

    A complete list of categories can be easily browsed on Marketplace [here](https://www.facebook.com/marketplace/categories).
