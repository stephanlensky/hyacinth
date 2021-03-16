import configparser
from datetime import datetime, timedelta
import time
from slack_webhook import Slack
from craigslist import CraigslistForSale
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import dateutil.parser


def tsprint(msg, **kwargs):
    print('{} {}'.format(datetime.now().strftime("[%H:%M:%S]"), msg), **kwargs)


home_lat_long = (42.771, -71.510)
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


def get_listings(last_run=None, area=areas['New England/New York'], max_price=6000, filter=None):
    cl_fs = CraigslistForSale(
        site=area['site'],
        category='mca',
        filters={
            'min_price': 2,
            'max_price': max_price,
            'search_nearby': 2,
            'nearby_area': area['nearby_areas']
        }
    )
    # format string for craigslist datetime format
    dt_fmt = '%Y-%m-%d %H:%M'

    results = []
    newest_listing_created = None
    for result in cl_fs.get_results(sort_by='newest'):
        if not newest_listing_created:
            result2 = cl_fs.get_listing(result)
            newest_listing_created = datetime.strptime(result2['created'], dt_fmt)
        result['last_updated'] = datetime.strptime(result['last_updated'], dt_fmt)
        if last_run and result['last_updated'] <= last_run:
            result2 = cl_fs.get_listing(result)
            result2['created'] = datetime.strptime(result2['created'], dt_fmt)
            if result2['created'] <= last_run:
                break
        if filter and not filter(result):
            tsprint('\tDiscarding {}'.format(result['name']))
            continue
        result = cl_fs.get_listing(result)
        result['created'] = datetime.strptime(result['created'], dt_fmt)
        result['distance'] = geodesic(home_lat_long, result['geotag']).miles
        result['location'] = geolocator.reverse(str(result['geotag'])[1:-1]).address
        time.sleep(1)  # to comply with geocoder api limit
        results.append(result)
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
    name = result['name'].lower().replace('excellent', '').replace('showroom', '')
    return ('klx' in name
            or ('ktm' in name and 'duke' not in name and 'sx' not in name)
            or 'exc' in name.replace('excellent', '')
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


if __name__ == '__main__':
    while True:
        last_run = dateutil.parser.parse(open('last_run.txt', 'r').read())

        name_set = set()
        all_results = []
        most_new_listing_time = None
        for area in areas:
            tsprint('Getting new listings for {}...'.format(area))
            newest_listing_time, results = get_listings(last_run=last_run, area=areas[area], filter=dualsport_filter)
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
