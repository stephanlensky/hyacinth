import configparser
from datetime import datetime, timedelta
import time
from slack_webhook import Slack
from craigslist import CraigslistForSale
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import dateutil.parser

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
    for result in cl_fs.get_results(sort_by='newest'):
        result['last_updated'] = datetime.strptime(result['last_updated'], dt_fmt)
        if last_run and result['last_updated'] < last_run:
            break
        if filter and not filter(result):
            continue
        result = cl_fs.get_listing(result)
        result['created'] = datetime.strptime(result['created'], dt_fmt)
        result['distance'] = geodesic(home_lat_long, result['geotag']).miles
        result['location'] = geolocator.reverse(str(result['geotag'])[1:-1]).address
        time.sleep(1)  # to comply with geocoder api limit
        results.append(result)
    return results


def notify_results(results, slack):
    for r in results:
        r['location'] = r['location'].split(', ')
        slack.post(attachments=[{
            'title': r['name'],
            'title_link': r['url'],
            'text': '*{} - {}, {} ({} mi.)*\n\n{}'.format(r['price'], r['location'][3], r['location'][5], int(r['distance']), r['body']),
            'thumb_url': r['images'][0] if len(r['images']) else None,
            'ts': time.mktime(r['created'].timetuple())
        }])


def dualsport_filter(result):
    name = result['name'].lower()
    return ('klx' in name
            or ('ktm' in name and '690' not in name and 'duke' not in name and 'sx' not in name)
            or 'exc' in name.replace('excellent', '')
            or 'husqvarna' in name
            or 'wr' in name
            or ('yamaha' in name and 'dual' in name)
            or ('yamaha' in name and 'xt' in name)
            or 'xr' in name
            or 'klr' in name
            or ('dr' in name and 'suzuki' in name)
            or 'drz' in name
            or 'crf' in name and 'crf 50' not in name and 'crf50' not in name)


slack = Slack(url=channels['#bikes-2020'])


if __name__ == '__main__':
    while True:
        now = datetime.now()
        last_run = dateutil.parser.parse(open('last_run.txt', 'r').read())

        all_results = []
        for area in areas:
            print('Getting new listings for {}...'.format(area))
            results = get_listings(last_run=last_run, area=areas[area], filter=dualsport_filter)
            for r in results:
                print("\t* Found result {}".format(r['name']))
                all_results.append(r)
        all_results.sort(key=lambda r: r['created'])
        notify_results(all_results, slack)

        print('Saving last run time...', end='', flush=True)
        open('last_run.txt', 'w').write(now.isoformat())
        print('done')

        print('Sleeping 15 minutes!')
        time.sleep(15 * 60)  # sleep for 15 minutes
