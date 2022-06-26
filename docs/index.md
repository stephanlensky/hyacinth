# Overview 🦜

**Hyacinth** is a Discord bot which will automatically send you notifications for new listings or postings anywhere on the web.

Taking inspiration from the venerable [youtube-dl](https://youtube-dl.org/), Hyacinth provides a core interface for filtering listings and sending notifications while allowing new listing sources to be added using a flexible plugin system.

Hyacinth is offered only in **self-hosted** form. This means you are the "administrator" of the bot, which entails:

- You provide infrastructure for the bot to run on. If you turn the bot off, you will stop receiving notifications!
- You provide the necessary API credentials, both for Discord and for any other services used by the bot
- You ensure the bot stays updated

Because of this, usage of this bot is recommended only for technically advanced users. Familiarity with Docker and comfort with the command-line are both required.

In return, you free yourself from the limitations of existing notification services, gaining access to advanced features such as:

- Complex filtering rules, including text-based filtering using arbitrary boolean rules
- Customizable polling intervals, allowing full control over how often the bot checks for new listings
- Search batching, reducing the number of times listing sources are polled for each search and allowing for more searches before hitting the anti-bot measures many classified ad sites have in place

When you're ready, head over to the [Getting Started](getting-started.md) page!
