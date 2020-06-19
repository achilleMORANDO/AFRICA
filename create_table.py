import sqlite3
from zipfile import ZipFile
import json
import re
import wptools

conn = sqlite3.connect('pays.sqlite')


def init_db(continent):
    with ZipFile('{}.zip'.format(continent), 'r') as z:
        files = z.namelist()
        for f in files:
            country = f.split('.')[0]
            print(country)
            info = json.loads(z.read(f))
            save_country(conn, country, info)

def get_name(wp_info):
    if 'conventional_long_name' in wp_info:
        name = wp_info['conventional_long_name']
        m = re.match("([\w, -]+?)\s*{{", name)
        if m:
            name = m.group(1)
        m = re.match("{{.*\|([\w, -]+)}}", name)
        if m:
            name = m.group(1)
        return name
    if 'common_name' in wp_info and wp_info['common_name'] == 'Singapore':
        return 'Republic of Singapore'
    if 'common_name' in wp_info:
        name = wp_info['common_name']
        print('using common name {}...'.format(name), end='')
        return name
    print('Could not fetch country name {}'.format(wp_info))
    return None

    
    
    
    
    
    
    
    
    
    
    
    
    
