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

## Limitations

Facebook implements aggressive rate-limiting and anti-bot measures which Hyacinth is not able to bypass. Trying to use Hyacinth from a cloud provider, over a VPN, or simply with too many active Marketplace searches is likely to result in rate-limiting.

After getting rate-limited, Hyacinth will be unable to load Marketplace searches without being logged in. This will result in an error like

```
hyacinth.exceptions.ParseError: Timed out waiting for search results to render
```

during polling of your Marketplace searches. If you encounter this, you might try:

- Running Hyacinth from your home network
- Reducing the number of active Marketplace searches
- Reducing the poll interval for Marketplace searches by setting `MARKETPLACE_POLL_INTERVAL_SECONDS` in your `.env` file (default is 10 minutes).
