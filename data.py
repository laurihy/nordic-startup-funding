import json

DATA_PATH = 'fetched_data/basedata.json'

def read_json_file(source):
    with open(source, 'r') as f:
        return json.loads(f.read())

DATA = read_json_file(DATA_PATH)