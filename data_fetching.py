import json
import pprint
import csv
import grequests
import time
import itertools

# https://crunchbase.wufoo.com/forms/crunchbase-open-data-map/
PATH_TO_ORGANIZATIONS = 'organizations_map.json'
PATH_TO_COMPANY_PROFILES = 'company_profiles.json'
PATH_TO_FUNDING_ROUNDS = 'funding_rounds.json'

NORDIC_COUNTRY_CODES = ['FIN', 'SWE', 'EST', 'LIE', 'LTU','NOR', 'DMA']

BASE_URL = 'https://api.crunchbase.com/v/2/'

# https://developer.crunchbase.com
API_KEYS = []


# bunch of helpers

pretty = pprint.PrettyPrinter(indent=4).pprint

def read_json_file(source):
    with open(source, 'r') as f:
        return json.loads(f.read())

def write_json_file(path, data):
    open(path, 'w').write(json.dumps(data))

def flatten(arr):
    return sum(arr, [])

def index_by(arr, fn):
    ret = {}
    for elem in arr:
        ret[fn(elem)] = elem
    return ret

def write_csv_dict(path, data):
    with open(path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        for row in data:
            writer.writerow(row)

def coerce_values_to_ascii(obj):
    ret = {}
    for k, v in obj.items():
        if isinstance(v, unicode):
            ret[k] = v.encode('ascii', 'ignore')
        if isinstance(v, list):
            ret[k] = ', '.join([i.encode('ascii', 'ignore') for i in v])
        else:
            ret[k] = v
    return ret

def coerce_array_values_to_ascii(arr):
    return [coerce_values_to_ascii(el) for el in arr]


def parallel_requests(urls, keys, verbose=True):
    '''
    Crunchbase limits 50 req / minute / APIkey.
    This enforces that limit. Also, if provided
    with multiple API keys, this will split the
    requests across all of them, making it possible to
    fetch more than 50req per minute.
    '''
    def add_keys(urls, keys):
        def add_key(url, key):
            return url + '?user_key='+str(key)
        return [add_key(*kv) for kv in zip(urls, itertools.cycle(keys))]

    def chunks(l, n):
        for i in xrange(0, len(l), n):
            yield l[i:i+n]

    ret = []
    for url_chunk in chunks(urls, 50 * len(keys)):
        if verbose:
            print 'Processed %s of %s' % (len(ret), len(urls))
        rs = [grequests.get(url) for url in add_keys(url_chunk, keys)]
        results = grequests.map(rs)
        for result in results:
            try:
                ret.append(result.json())
            except Exception, e:
                print 'Error with url: ', result.url
        time.sleep(60) # 50req / minute / API key
    return ret


# stuff for fetching data from crunchbase

def fetch_companies(organizations_to_fetch):

    def get_org_url(org):
        # eg https://www.crunchbase.com/organization/jaiku?&utm_source=odm_json_v101&utm_medium=export&utm_campaign=dataset
        cb_link = org.get('crunchbase_url', '')
        path = cb_link.replace('https://www.crunchbase.com/organization/', '')
        permalink = path.split('?')[0]
        return '%sorganization/%s' % (BASE_URL, permalink)

    urls = [get_org_url(org) for org in organizations_to_fetch]
    return parallel_requests(urls, API_KEYS)


def fetch_funding_rounds_for_companies(companies):

    def get_funding_rounds(item):
        return item.get('data', {}).get('relationships', {}).get('funding_rounds', {}).get('items', [])

    def get_funding_url(funding):
        return '%s%s' % (BASE_URL, funding.get('path', ''))

    rounds = flatten([get_funding_rounds(c) for c in companies])
    urls = [get_funding_url(r) for r in rounds]
    return parallel_requests(urls, API_KEYS)


# stuff for joining data

def organization_into_companies(organizations, companies):
    orgs_by_uuid = index_by(organizations, lambda x: x['crunchbase_uuid'])
    def add_org(company):
        company['organization'] = orgs_by_uuid[company['data']['uuid']]
        return company
    return [add_org(c) for c in companies]


def companies_into_funding_rounds(companies, funding_rounds):
    companies_by_path = index_by(companies, lambda x: 'organization/' + x['data']['properties']['permalink'])
    for r in funding_rounds:
        for org in r['data']['relationships']['funded_organization']['items']:
            org['company'] = companies_by_path[org['path']]
    return funding_rounds




def build_dataset(funding_rounds):
    ret = []
    for r in funding_rounds:
        company_data = r['data']['relationships']['funded_organization']['items'][0]['company']
        ret.append({
            'date': r['data']['properties']['announced_on'],
            'company_name': company_data['data']['properties']['name'],
            'company_location_country': company_data['organization']['location_country_code'],
            'company_location_city': company_data['organization'].get('location_city',''),
            'company_founders': [i.get('name','') for i in company_data['data']['relationships'].get('founders', {}).get('items',[])],
            'company_categories': [i.get('name','') for i in company_data['data']['relationships'].get('categories', {}).get('items',[])],
            'company_founded_on': company_data['data']['properties'].get('founded_on', ''),
            'funding_size_usd': r['data']['properties'].get('money_raised_usd',''),
            'series': r['data']['properties'].get('series',''),
            'investors': [i['investor'].get('name','') for i in r['data']['relationships'].get('investments', {}).get('items',[])],
        })
    return ret
