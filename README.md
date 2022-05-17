# marketplace-notifier-bot

[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Local development

This application is built with [Docker](https://www.docker.com/), and the recommended local development flow makes use of the Docker integrations available for modern IDEs (such as [VS Code Remote Development](https://code.visualstudio.com/docs/remote/remote-overview)). To run the local development container in the background, use the following `docker-compose` command:

```
docker-compose up -d devbox
```

Then attach to the container using your preferred IDE.
