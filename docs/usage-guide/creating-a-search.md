In order to start receiving notifications for new listings, the first thing you need to do is create a new search for Hyacinth to monitor.

## The `/search add` command

To do this, navigate to the channel you would like to receive notifications in and type `/search add`. This command takes two arguments:

`plugin`

: Plugins power Hyacinth's search capabilities, acting as sources for new listings. The following plugins are currently available:

    - [`craigslist`](plugins/craigslist.md)
    - [`marketplace`](plugins/marketplace.md)

`name`

: A name of your choice for this search. When referencing the search in other commands (for example, `/search edit` or `/search delete`), you will select it by this name.

For example, to create a new Craigslist search:

![create a new search](../assets/create_search.png)

## Configuring the search

After submitting the `/search add` command, a plugin-specific dialog will appear where you can enter additional information about your search.

For example, for the Craigslist search shown above, this dialog will ask which site and category you would like to search. For this tutorial, you might pick `boston` and `sss` (general for-sale) respectively. For full details on these fields, please see the [Craigslist plugin page](plugins/craigslist.md).

!!! question

    **Only site and category? Where do I enter my actual search terms?**

    This is what filters are for! Hyacinth supports complex filtering on any listing field, but intentionally keeps searches as wide as possible. When creating new searches, Hyacinth will attempt to reuse data from an existing search, reducing the number of outgoing network requests to plugin sources. Then, filters on each channel narrow down the results.

    This allows you to create notifications for a variety of different items without getting rate-limited and is the true power of Hyacinth!

After creating your first search in a channel, the notifier starts paused. [Add some filters](adding-filters.md), then unpause when you are ready!
