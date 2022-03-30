import configparser
import json
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from craigslist import CraigslistForSale
from geopy.distance import geodesic
from geopy.geocoders import Nominatim


def tsprint(msg, **kwargs):
    ts = datetime.now().strftime("[%H:%M:%S]")
    print(f"{ts} {msg}", **kwargs)


def get_craigslist_areas(config_path="craigslist.ini"):
    cl_config = configparser.ConfigParser()
    cl_config.read(config_path)
    areas = {}
    for area in cl_config:
        if area == "DEFAULT":
            continue
        areas[area] = {
            "site": cl_config[area]["site"],
            "nearby_areas": cl_config[area]["nearbyAreas"].split(","),
        }

    return areas


def get_areas_reference(areas_json_path=Path("craigslist_areas.json")):
    if not areas_json_path.exists():
        r = requests.get("https://reference.craigslist.org/Areas")
        with areas_json_path.open("w", encoding="utf-8") as areas_json_file:
            areas_json_file.write(r.text)
        areas_json = json.loads(r.text)
    else:
        with areas_json_path.open(encoding="utf-8") as areas_json_file:
            areas_json = json.load(areas_json_file)
    areas_reference = {}
    for a in areas_json:
        areas_reference[a["Hostname"]] = a

    return areas_reference


CRAIGSLIST_AREAS = get_craigslist_areas()
CRAIGSLIST_AREA_NAMES = list(CRAIGSLIST_AREAS.keys())
geolocator = Nominatim(user_agent="craigslist_notifier")
CRAIGSLIST_AREAS_REFERENCE = get_areas_reference()


def get_listings(
    last_run=None,
    area=CRAIGSLIST_AREAS["New England/New York"],
    category="sss",
    min_price=2,
    max_price=6000,
    home_lat_long=(42.771, -71.510),
    search_filter=None,
):
    cl_fs = CraigslistForSale(
        site=area["site"],
        category=category,
        filters={
            "min_price": min_price,
            "max_price": max_price,
            "search_nearby": 2,
            "nearby_area": area["nearby_areas"],
        },
    )
    # format string for craigslist datetime format
    dt_fmt = "%Y-%m-%d %H:%M"

    results = []
    newest_listing_created = None
    for listing in cl_fs.get_results(sort_by="newest"):
        listing2 = None
        try:
            result = {}
            if not newest_listing_created:
                listing2 = cl_fs.get_listing(listing)
                newest_listing_created = datetime.strptime(listing2["created"], dt_fmt)
            listing["last_updated"] = datetime.strptime(listing["last_updated"], dt_fmt)
            if last_run and listing["last_updated"] <= last_run:
                listing2 = cl_fs.get_listing(listing)
                listing2["created"] = datetime.strptime(listing2["created"], dt_fmt)
                if listing2["created"] <= last_run:
                    break
            if search_filter and not search_filter(listing):
                tsprint(f"\tDiscarding {listing['name']}")
                continue
            listing = cl_fs.get_listing(listing)
            result["created"] = datetime.strptime(listing["created"], dt_fmt)
            result["url"] = listing["url"]
            result["body"] = listing["body"]
            result["images"] = listing["images"]
            result["name"] = listing["name"]
            result["price"] = listing["price"]

            # if there is no location provided, use the lat/long of the craigslist site
            # this is probably a city, e.g. providence, albany, etc.
            if not listing["geotag"]:
                site = re.match(r"http(s)?://(www\.)?(.+)\.craigslist", listing["url"]).groups()[2]
                listing["geotag"] = (
                    CRAIGSLIST_AREAS_REFERENCE[site]["Latitude"],
                    CRAIGSLIST_AREAS_REFERENCE[site]["Longitude"],
                )

            result["distance"] = geodesic(home_lat_long, listing["geotag"]).miles
            location = geolocator.reverse(str(listing["geotag"])[1:-1])
            if location:
                result["location"] = location.address
            # protects against users putting in lat/long in places that can't be geocoded, like
            # the ocean
            else:
                result["location"] = str(listing["geotag"])[1:-1]
            time.sleep(1)  # to comply with geocoder api limit
            results.append(result)
        except KeyError as e:
            print(e)
            tsprint("ERROR PARSING LISTING, SKIPPING")
            tsprint(f"listing: {listing}")
            tsprint(f"listing2: {listing2}")
    return newest_listing_created, results


class CraigslistMonitor(threading.Thread):
    def __init__(self, observers=None, last_run=None):
        if observers is None:
            observers = []

        self.__stop_event = threading.Event()
        self.interval = timedelta(minutes=10)

        self.home_lat_long = (42.771, -71.510)
        if not last_run:
            last_run = datetime.now() - self.interval
        self.last_run = last_run
        self.last_listing = None

        self.observers = observers
        self.observers_lock = threading.Lock()

        super().__init__()
        self.start()

    def run(self):
        # if this was reloaded from disk, it may still have some time it needs to wait before
        # running the first time
        time_to_wait = self.last_run + self.interval - datetime.now()
        if time_to_wait.total_seconds() > 0:
            self.__stop_event.wait(time_to_wait.total_seconds())

        while not self.__stop_event.is_set():
            if self.__stop_event.is_set():
                break
            name_set = set()
            most_new_listing_time = None
            for area in CRAIGSLIST_AREAS:
                category = "mca"
                tsprint(f"Getting new listings for {area}...")
                last_run = self.last_run if self.last_listing is None else self.last_listing
                newest_listing_time, results = get_listings(
                    last_run=last_run,
                    area=CRAIGSLIST_AREAS[area],
                    home_lat_long=self.home_lat_long,
                    category=category,
                )
                if not most_new_listing_time or newest_listing_time > most_new_listing_time:
                    most_new_listing_time = newest_listing_time
                for r in list(results):
                    if r["name"] not in name_set:
                        tsprint(f"\t* Found result {r['name']}")
                        name_set.add(r["name"])
                    else:
                        tsprint(f"\tDiscarding duplicate {r['name']}")
                        results.remove(r)
                self.notify(results, area, category)
            self.last_run = datetime.now()
            self.last_listing = most_new_listing_time
            tsprint("Done!")
            self.__stop_event.wait(self.interval.total_seconds())

    def notify(self, results, area, category):
        with self.observers_lock:
            for observer in self.observers:
                if area in observer.areas and category in observer.categories:
                    observer.update(results)

    def subscribe(self, observer):
        with self.observers_lock:
            self.observers.append(observer)

    def join(self, timeout=None):
        """set stop event and join within a given time period"""
        self.__stop_event.set()
        super().join(timeout)


class CraigslistObserver:
    def __init__(self, categories, areas):
        self.categories = categories
        self.areas = areas
        self.listings = []
        self.listings_lock = threading.Lock()

    def update(self, listings):
        with self.listings_lock:
            self.listings += listings

    def get_new_listings(self):
        with self.listings_lock:
            listings = self.listings
            self.listings = []
            return listings
