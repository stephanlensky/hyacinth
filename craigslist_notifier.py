import configparser
from datetime import datetime, timedelta
import time
from slack_webhook import Slack
from craigslist import CraigslistForSale
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import dateutil.parser
from state_names import state_names
import re
from pathlib import Path
import requests
import json
import threading


def tsprint(msg, **kwargs):
    print('{} {}'.format(datetime.now().strftime("[%H:%M:%S]"), msg), **kwargs)


slack_config = configparser.ConfigParser()
slack_config.read('config.ini')
channels = {}
for e in slack_config['slack.com']:
    channels['#{}'.format(e)] = slack_config['slack.com'][e]
cl_config = configparser.ConfigParser()
cl_config.read('craigslist_areas.ini')
areas = {}
for area in cl_config:
    if area == 'DEFAULT':
        continue
    areas[area] = {
        'site': cl_config[area]['site'],
        'nearby_areas': cl_config[area]['nearbyAreas'].split(',')
    }
geolocator = Nominatim(user_agent="craigslist_notifier")
areas_json_path = 'craigslist_areas.json'
if not Path(areas_json_path).exists():
    r = requests.get('https://reference.craigslist.org/Areas')
    with open(areas_json_path, 'w') as areas_json_file:
        areas_json_file.write(r.text)
    areas_json = json.loads(r.text)
else:
    areas_json = json.load(open(areas_json_path, 'r'))
areas_reference = {}
for a in areas_json:
    areas_reference[a['Hostname']] = a


def get_listings(last_run=None, area=areas['New England/New York'], category='sss', min_price=2, max_price=6000, home_lat_long=(42.771, -71.510), filter=None):
    cl_fs = CraigslistForSale(
        site=area['site'],
        category=category,
        filters={
            'min_price': min_price,
            'max_price': max_price,
            'search_nearby': 2,
            'nearby_area': area['nearby_areas']
        }
    )
    # format string for craigslist datetime format
    dt_fmt = '%Y-%m-%d %H:%M'

    results = []
    newest_listing_created = None
    for listing in cl_fs.get_results(sort_by='newest'):
        try:
            result = {}
            if not newest_listing_created:
                listing2 = cl_fs.get_listing(listing)
                newest_listing_created = datetime.strptime(listing2['created'], dt_fmt)
            listing['last_updated'] = datetime.strptime(listing['last_updated'], dt_fmt)
            if last_run and listing['last_updated'] <= last_run:
                listing2 = cl_fs.get_listing(listing)
                listing2['created'] = datetime.strptime(listing2['created'], dt_fmt)
                if listing2['created'] <= last_run:
                    break
            if filter and not filter(listing):
                tsprint('\tDiscarding {}'.format(listing['name']))
                continue
            listing = cl_fs.get_listing(listing)
            result['created'] = datetime.strptime(listing['created'], dt_fmt)
            result['url'] = listing['url']
            result['body'] = listing['body']
            result['images'] = listing['images']
            result['name'] = listing['name']
            result['price'] = listing['price']

            # if there is no location provided, use the lat/long of the craigslist site
            # this is probably a city, e.g. providence, albany, etc.
            if not listing['geotag']:
                site = re.match(r'http(s)?://(www\.)?(.+)\.craigslist', listing['url']).groups()[2]
                listing['geotag'] = areas_reference[site]['Latitude'], areas_reference[site]['Longitude']

            result['distance'] = geodesic(home_lat_long, listing['geotag']).miles
            location = geolocator.reverse(str(listing['geotag'])[1:-1])
            if location:
                result['location'] = location.address
            else:  # protects against users putting in lat/long in places that can't be geocoded, like the ocean
                result['location'] = str(listing['geotag'])[1:-1]
            time.sleep(1)  # to comply with geocoder api limit
            results.append(result)
        except KeyError:
            tsprint("ERROR PARSING LISTING, SKIPPING: {}".format(listing))
    return newest_listing_created, results


def notify_results(results, slack):
    for r in results:
        r['location'] = r['location'].split(', ')
        # sometimes street address is missing from geocode result, so town/state position in geocoded string varies
        try:
            loc_mod = -1 if r['location'][5].isdigit() else 0
            location = '{}, {}'.format(r['location'][3 + loc_mod], r['location'][5 + loc_mod])
        except Exception:
            location = r['location']
        slack.post(attachments=[{
            'title': r['name'],
            'title_link': r['url'],
            'text': '*{} - {} ({} mi. away)*\n\n{}'.format(r['price'], location, int(r['distance']), r['body']),
            'thumb_url': r['images'][0] if len(r['images']) else None,
            'ts': time.mktime(r['created'].timetuple())
        }])


def dualsport_filter(result):
    name = result['name'].lower().replace('excellent', '').replace('showroom', '').replace('lowrider', '').replace('extras', '')
    return 'harley' not in name and (
           'klx' in name
           or ('ktm' in name and 'duke' not in name and 'sx' not in name and 'rc' not in name)
           or 'exc' in name.replace('exce', '')
           or 'husqvarna' in name
           or 'wr' in name
           or ('yz' in name and 'yz 65' not in name and 'yz65' not in name and 'yzf' not in name and 'yz 85' not in name and 'yz85' not in name)
           or ('yamaha' in name and 'dual' in name)
           or ('yamaha' in name and 'xt' in name)
           or ('xr' in name and 'gsxr' not in name)
           or 'klr' in name
           or ('dr' in name and 'suzuki' in name)
           or ('drz' in name and 'drz 50' not in name and 'drz50' not in name)
           or ('crf' in name and 'crf 50' not in name and 'crf50' not in name and 'crf80' not in name and 'crf 80' not in name)
           or 'beta' in name
           or 'swm' in name
           or 'tw 200' in name or 'tw200' in name)


slack = Slack(url=channels['#bikes-2021'])


class CraigslistNotifier(threading.Thread):

    def __init__(self, results_callback, results_filter):
        self.__stop_event = threading.Event()
        self.__pause_event = threading.Event()
        self.__pause_event.set()
        self.interval = timedelta(minutes=10)

        self.home_lat_long = (42.771, -71.510)
        self.last_run = datetime.now() - self.interval
        # self.last_run = dateutil.parser.parse('2021-03-29T16:04:00')
        self.last_listing = None
        self.results_callback = results_callback
        self.filter = results_filter

        super().__init__()

    def run(self):
        # if this notifier is reloaded from disk, it may still have some time it needs to wait before running the first time
        time_to_wait = self.last_run + self.interval - datetime.now()
        if time_to_wait.total_seconds() > 0:
            self.__stop_event.wait(time_to_wait.total_seconds())

        while not self.__stop_event.isSet():
            self.__pause_event.wait()
            if self.__stop_event.isSet():
                break
            name_set = set()
            all_results = []
            most_new_listing_time = None
            for area in areas:
                tsprint('Getting new listings for {}...'.format(area))
                last_run = self.last_run if self.last_listing is None else self.last_listing
                newest_listing_time, results = get_listings(
                    last_run=last_run,
                    area=areas[area],
                    home_lat_long=self.home_lat_long,
                    category='mca',
                    filter=self.filter
                )
                if not most_new_listing_time or newest_listing_time > most_new_listing_time:
                    most_new_listing_time = newest_listing_time
                for r in results:
                    if r['name'] not in name_set:
                        tsprint("\t* Found result {}".format(r['name']))
                        all_results.append(r)
                        name_set.add(r['name'])
                    else:
                        tsprint('\tDiscarding duplicate {}'.format(r['name']))
            all_results.sort(key=lambda r: r['created'])
            self.last_run = datetime.now()
            self.last_listing = most_new_listing_time
            self.results_callback(all_results)
            tsprint('Done!')
            self.__stop_event.wait(self.interval.total_seconds())

    def pause(self):
        tsprint('Pausing!')
        self.__pause_event.clear()

    def unpause(self):
        tsprint('Unpausing!')
        self.__pause_event.set()

    def join(self, timeout=None):
        """set stop event and join within a given time period"""
        self.__stop_event.set()
        self.__pause_event.set()
        super().join(timeout)


if __name__ == '__main__':
    while True:
        last_run = dateutil.parser.parse(open('last_run.txt', 'r').read())

        name_set = set()
        all_results = []
        most_new_listing_time = None
        for area in areas:
            tsprint('Getting new listings for {}...'.format(area))
            newest_listing_time, results = get_listings(last_run=last_run, area=areas[area], category='mca', filter=dualsport_filter)
            if not most_new_listing_time or newest_listing_time > most_new_listing_time:
                most_new_listing_time = newest_listing_time
            for r in results:
                if r['name'] not in name_set:
                    tsprint("\t* Found result {}".format(r['name']))
                    all_results.append(r)
                    name_set.add(r['name'])
                else:
                    tsprint('\tDiscarding duplicate {}'.format(r['name']))
        all_results.sort(key=lambda r: r['created'])
        notify_results(all_results, slack)

        tsprint('Saving last run time...', end='', flush=True)
        open('last_run.txt', 'w').write(most_new_listing_time.isoformat())
        print('done')

        tsprint('Sleeping 10 minutes!')
        time.sleep(10 * 60)  # sleep for 10 minutes
