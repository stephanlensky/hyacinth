# Hyacinth

[![Documentation](https://img.shields.io/github/workflow/status/stephanlensky/hyacinth/docs?label=docs)](https://slensky.com/hyacinth)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


**Documentation:** https://slensky.com/hyacinth

## Overview 🦜

**Hyacinth** is a Discord bot which will automatically send you notifications for new listings or postings anywhere on the web.

Currently, only Craigslist is supported, but the application is built to be easily extensible. Taking inspiration from the venerable [youtube-dl](https://youtube-dl.org/), Hyacinth provides a single interface for filtering listings and sending notifications while allowing new sources to be developed in a pluggable fashion.

Hyacinth offers a number of advanced features for power-users, including:

- Complex filtering rules, including text-based filtering using arbitrary boolean rules
- Customizable polling intervals, allowing full control over how often the bot checks for new listings
- Search batching, reducing the number of times listing sources are polled for each search and allowing for more searches before hitting the anti-bot measures many classified ad sites have in place

For more information and the user guide, please head over to the [documentation](https://slensky.com/hyacinth/).

## Local development

This application is built with [Docker](https://www.docker.com/), and the recommended local development flow makes use of the Docker integrations available for modern IDEs (such as [VS Code Remote Development](https://code.visualstudio.com/docs/remote/remote-overview)). To run the local development container in the background, use the following `docker-compose` command:

```
docker-compose up -d devbox
```

Then attach to the container using your preferred IDE.
