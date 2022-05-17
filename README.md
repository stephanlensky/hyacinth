# marketplace-notifier-bot

[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Usage

### Local reverse geocoding

In order to present the most accurate location information, some sources will attempt to detect the city and state of listings based off of their coordinate location (latitude and longitude). This is a process known as **reverse geocoding**.

By default, the [Google Geocoding API](https://developers.google.com/maps/documentation/geocoding/overview) is used for this. However, this is a paid service and usage requires a Google Cloud Platform account with billing set up. For users who do not wish to configure this, a local reverse geocoder is included with much of the same functionality.

To use it, first download the following freely available geospatial datasets and extract them into the `geography/` folder:

- [cities1000.zip](http://download.geonames.org/export/dump/cities1000.zip) from geonames.org
- [gadm36_USA_gpkg.zip](https://biogeo.ucdavis.edu/data/gadm3.6/gpkg/gadm36_USA_gpkg.zip) from GADM

After this, enable local reverse geocoding with the `USE_LOCAL_GEOCODER` environment variable.

(in `.env` file)
```
USE_LOCAL_GEOCODER=true
```


## Local development

This application is built with [Docker](https://www.docker.com/), and the recommended local development flow makes use of the Docker integrations available for modern IDEs (such as [VS Code Remote Development](https://code.visualstudio.com/docs/remote/remote-overview)). To run the local development container in the background, use the following `docker-compose` command:

```
docker-compose up -d devbox
```

Then attach to the container using your preferred IDE.
