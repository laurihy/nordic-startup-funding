import datetime
from copy import deepcopy
from collections import defaultdict
import pystache
import pprint
from jinja2 import Environment, FileSystemLoader


from data import DATA

def to_year(s):
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%d').year
    except Exception, e:
        return 'N/A'

def to_month(s):
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%d').month
    except Exception, e:
        return 'N/A'

def listify(data):
    # if data is list, return it, otherwise return list where only element is data
    if isinstance(data, list):
        return data
    return [data]

def group_by(data, fn=None):
    ret = defaultdict(list)
    for d in data:
        for key in listify(fn(d)):
            ret[key].append(deepcopy(d))
    return ret


def get_data_by_year(data):
    return group_by(data, fn=lambda x: to_year(x.get('date')))

def get_data_by_month(data):
    return group_by(data, fn=lambda x: to_month(x.get('date')))

def get_data_founded_by_year(data):
    return group_by(data, fn=lambda x: to_year(x.get('company_founded_on')))

def get_data_by_company_name(data):
    return group_by(data, fn=lambda x: x.get('company_name'))

def get_data_by_investor(data):
    return group_by(data, fn=lambda x: x.get('investors'))

def get_data_by_founders(data):
    return group_by(data, fn=lambda x: x.get('company_founders'))

def get_data_by_country(data):
    return group_by(data, fn=lambda x: x.get('company_location_country'))

def get_data_by_city(data):
    return group_by(data, fn=lambda x: x.get('company_location_city'))

def get_data_by_series(data):
    return group_by(data, fn=lambda x: (x.get('series') or 'Unknown').upper())

def index_by(arr, fn):
    ret = {}
    for elem in arr:
        ret[fn(elem)] = elem
    return ret

def index_by_name(arr):
    return index_by(arr, lambda x: x.get('name'))

def get_values_split_by(fn):
    def ret_fn(data):
        ret = {}
        for k, v in fn(data).items():
            count = len([e.get('funding_size_usd') or 0 for e in v])
            total = sum([e.get('funding_size_usd') or 0 for e in v])
            ret[k] = {
                'count': count,
                'total': total,
                'mean': (total / count) if count > 0 else 0
            }
        return ret
    return ret_fn


def top_list(n, key):

    def _obj_to_list(obj):
        ret = []
        for k, v in obj.items():
            ret.append({
                'key': k,
                'values': v,
            })
        return ret

    def fn(obj):
        return [el for el in sorted(_obj_to_list(obj), key=key, reverse=True) if el.get('key')][:n]

    return fn



def build_table(data, fns):
    if not fns:
        return []
    ret = []

    data_fn, value_fn, process_fn = fns[0]

    for k, v in data_fn(data).items():
        ret.append({
            'name': k,
            'values':  process_fn(value_fn(v)), #get_values_split_by(v, x_fn),
            'children': build_table(v, fns[1:])
        })

    return index_by_name(ret)

def identity(data): return data


top_10_by_total = top_list(10, lambda x: x.get('values', {}).get('total'))
top_10_by_count = top_list(10, lambda x: x.get('values', {}).get('count'))
top_10_by_mean = top_list(10, lambda x: x.get('values', {}).get('mean'))

x_axis = {
    'countries': sorted(list(set([x.get('company_location_country') for x in DATA]))),
    'years': sorted(list(set([to_year(x.get('date')) for x in DATA]))),
    'series': sorted(list(set([(x.get('series') or 'Unknown').upper() for x in DATA])))
}

by_year_and_series_and_location = build_table(DATA, [
    (get_data_by_country, get_values_split_by(get_data_by_series), identity),
    (get_data_by_series, get_values_split_by(get_data_by_year), identity)
])

by_year_and_location = build_table(DATA, [
    (get_data_by_country, get_values_split_by(get_data_by_year), identity)
])

top_investors_by_location_and_year = build_table(DATA, [
    (get_data_by_country, get_values_split_by(get_data_by_investor), top_10_by_count),
    (get_data_by_year, get_values_split_by(get_data_by_investor), top_10_by_count),
])

top_companies_by_location = build_table(DATA, [
    (get_data_by_country, get_values_split_by(get_data_by_company_name), top_10_by_total)
])

top_founders_by_location = build_table(DATA, [
    (get_data_by_country, get_values_split_by(get_data_by_founders), top_10_by_total)
])