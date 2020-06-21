import sqlite3
from zipfile import ZipFile
import json
import re
import wptools
#chemin
import os
os.chdir('C:\\Users\\Public\python')
cwd = os.getcwd()

##
conn = sqlite3.connect('pays2.sqlite')


def create_table(continent):
    with ZipFile('{}.zip'.format(continent), 'r') as z:
        files = z.namelist()
        for f in files:
            country = f.split('.')[0]
            print(country)
            info = json.loads(z.read(f))
            save_country(conn, country, info)


def get_name(wp_info):
    # cas général
    if 'conventional_long_name' in wp_info:
        name = wp_info['conventional_long_name']

        # si le nom est composé de mots avec éventuellement des espaces,
        # des virgules et/ou des tirets, situés devant une double {{ ouvrante,
        # on conserve uniquement la partie devant les {{
        m = re.match("([\w, -]+?)\s*{{", name)
        if m:
            name = m.group(1)

        # si le nom est situé entre {{ }} avec un caractère séparateur |
        # on conserve la partie après le |
        m = re.match("{{.*\|([\w, -]+)}}", name)
        if m:
            name = m.group(1)
        return name

    # FIX manuel (l'infobox ne contient pas l'information)
    if 'common_name' in wp_info and wp_info['common_name'] == 'Singapore':
        return 'Republic of Singapore'

    # S'applique uniquement au Vanuatu
    if 'common_name' in wp_info:
        name = wp_info['common_name']
        print('using common name {}...'.format(name), end='')
        return name

    # Aveu d'échec, on ne doit jamais se retrouver ici
    print('Could not fetch country name {}'.format(wp_info))
    return None


def get_capital(wp_info):
    # cas général
    if 'capital' in wp_info:

        # parfois l'information récupérée comporte plusieurs lignes
        # on remplace les retours à la ligne par un espace
        capital = wp_info['capital'].replace('\n', ' ')

        # le nom de la capitale peut comporter des lettres, des espaces,
        # ou l'un des caractères ',.()|- compris entre crochets [[...]]
        m = re.match(".*?\[\[([\w\s',.()|-]+)\]\]", capital)

        # on récupère le contenu des [[...]]
        capital = m.group(1)

        # si on tombe sur une valeur avec des séparateurs |
        # on prend le premier terme
        if '|' in capital:
            capital = capital.split('|').pop()

        # Cas particulier : Singapour, Monaco, Vatican
        if capital == 'city-state':
            capital = wp_info['common_name']

        # Cas particulier : Suisse
        if capital == 'de jure' and wp_info['common_name'] == 'Switzerland':
            capital = 'Bern'

        return capital

    # FIX manuel (l'infobox ne contient pas l'information)
    if 'common_name' in wp_info and wp_info['common_name'] == 'Palestine':
        return 'Ramallah'

    # Aveu d'échec, on ne doit jamais se retrouver ici
    print(' Could not fetch country capital {}'.format(wp_info))
    return None


def get_currency(wp_info):
    if 'currency' in wp_info:
        currency = wp_info['currency']
        m = re.match(".*?\[\[([\w\s',.()|-]+)\]\]", currency)
        if m is None:
            if wp_info['common_name'] == 'Eswatini':
                return 'Lilangeni'
            else:
                print('Error fetching currency')
        else:
            currency = m.group(1)
            separator = currency.find('|')
            if separator is not -1:
                currency = currency[separator+1:]
            return currency
    return None

def get_population(wp_info):
    if 'population_census' in wp_info:
        population = wp_info['population_census']  # type: str
        population = population.replace(',', '')
        population = population.replace(' ', '')
        population=population.replace('', '')
        if population == '24905843{{citationneeded|date|=|April2019}}':
            return 24905843
        if population == '21397000(52nd)':
            return 21397000
        if population == '10515973{{sfn|NationalInstituteofStatisticsofRwanda|2014|p|=|3}}':
            return 10515973
        if population == '51770560{{rp|18}}':
            return 51770560
        if wp_info['common_name']=='South Sudan':
            return 51770560
        if wp_info['common_name']=='Sudan':
            return 30894000
        else :
            population_int = int(population)
            population = f'{population_int:,}'
            return population

    else:
        print('Error fetching population')
        return None

def get_superficie(wp_info):
    if 'area_km2' in wp_info:
        superficie = wp_info['area_km2']  # type: str
        superficie = superficie.replace(',', '')
        superficie = superficie.replace(' ', '')
        superficie_int = int(superficie)
        superficie = f'{superficie_int:,}'
        return superficie
    else:
        print('Error fetching superficie')
        return None

def get_density(wp_info):
    if 'population_density_km2' in wp_info:
        density = wp_info['population_density_km2']  # type: str
        density = density.replace('.',',')
        return density
    else:
        print('Error fetching density')
        return None

def get_hdi(wp_info):
    if 'HDI' in wp_info:
        hdi = wp_info['HDI']  # type: str
        hdi = hdi.replace('.',',')
        return hdi
    else:
        print('Error fetching hdi')
        return None

def get_growth_hdi(wp_info):
    if 'HDI_change' in wp_info:
        hdi_change = wp_info['HDI_change']  # type: str
        return hdi_change
    else:
        print('Error fetching hdi_change')
        return None


def get_government_type(wp_info):
    if 'government_type' in wp_info:
        government_type = wp_info['government_type']  # type: str
        if government_type.find('dictatorship') != -1:
            return 'dictatorship'
        elif government_type.find('republic') != -1:
            return 'republic'
        elif government_type.find('monarchy') != -1:
            return 'monarchy'
        elif government_type.find('provisional') != -1:
            return 'provisional government'
    print('Error fetching Government type')
    return None
