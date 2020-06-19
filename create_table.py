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


def get_coords(wp_info):
    # S'il existe des coordonnées dans l'infobox du pays
    # (cas le plus courant)
    if 'coordinates' in wp_info:

        # (?i) - ignorecase - matche en majuscules ou en minuscules
        # ça commence par "{{coord" et se poursuit avec zéro ou plusieurs
        #   espaces suivis par une barre "|"
        # après ce motif, on mémorise la chaîne la plus longue possible
        #   ne contenant pas de },
        # jusqu'à la première occurence de "}}"
        m = re.match('(?i).*{{coord\s*\|([^}]*)}}', wp_info['coordinates'])

        # l'expression régulière ne colle pas, on affiche la chaîne analysée pour nous aider
        # mais c'est un aveu d'échec, on ne doit jamais se retrouver ici
        if m is None:
            print(' Could not parse coordinates info {}'.format(wp_info['coordinates']))
            return None

        # cf. https://en.wikipedia.org/wiki/Template:Coord#Examples
        # on a récupère une chaîne comme :
        # 57|18|22|N|4|27|32|W|display=title
        # 44.112|N|87.913|W|display=title
        # 44.112|-87.913|display=title
        str_coords = m.group(1)

        # on convertit en numérique et on renvoie
        if str_coords[0:1] in '0123456789':
            return cv_coords(str_coords)

    # FIX manuel (l'infobox ne contient pas d'information directement exploitable)
    if 'common_name' in wp_info and wp_info['common_name'] == 'the Philippines':
        return cv_coords('14|35|45|N|120|58|38|E')
    if 'common_name' in wp_info and wp_info['common_name'] == 'Tanzania':
        return cv_coords('6|10|23|S|35|44|31|E')

    # On n'a pas trouvé de coordonnées dans l'infobox du pays
    # on essaie avec la page de la capitale
    capital = get_capital(wp_info)
    if capital:
        print(' Fetching capital coordinates...')
        return get_coords(get_info(capital))

    # Aveu d'échec, on ne doit jamais se retrouver ici
    print(' Could not fetch country coordinates')
    return None


def get_info(country):
    # récupération de la page du pays passé en argument
    # on peut ajouter silent=True pour éviter le message sur fond rose
    page = wptools.page(country, silent=True)

    # analyse du contenu de la page
    # l'argument False sert à ne pas afficher de message sur fond rose
    page.get_parse(False)

    # On renvoie l'infobox
    return page.data['infobox']


def cv_coords(str_coords):
    """Conversion d'une chaine de caracteres decrivant une position géographisuqe en coordonnees numeriques latitude
    et longitude"""
    # on découpe au niveau des "|"
    c = str_coords.split('|')

    # on extrait la latitude en tenant compte des divers formats
    lat = float(c.pop(0))
    if c[0] == 'N':
        c.pop(0)
    elif c[0] == 'S':
        lat = -lat
        c.pop(0)
    elif len(c) > 1 and c[1] == 'N':
        lat += float(c.pop(0)) / 60
        c.pop(0)
    elif len(c) > 1 and c[1] == 'S':
        lat += float(c.pop(0)) / 60
        lat = -lat
        c.pop(0)
    elif len(c) > 2 and c[2] == 'N':
        lat += float(c.pop(0)) / 60
        lat += float(c.pop(0)) / 3600
        c.pop(0)
    elif len(c) > 2 and c[2] == 'S':
        lat += float(c.pop(0)) / 60
        lat += float(c.pop(0)) / 3600
        lat = -lat
        c.pop(0)

    # on fait de même avec la longitude
    lon = float(c.pop(0))
    if c[0] == 'W':
        lon = -lon
        c.pop(0)
    elif c[0] == 'E':
        c.pop(0)
    elif len(c) > 1 and c[1] == 'W':
        lon += float(c.pop(0)) / 60
        lon = -lon
        c.pop(0)
    elif len(c) > 1 and c[1] == 'E':
        lon += float(c.pop(0)) / 60
        c.pop(0)
    elif len(c) > 2 and c[2] == 'W':
        lon += float(c.pop(0)) / 60
        lon += float(c.pop(0)) / 3600
        lon = -lon
        c.pop(0)
    elif len(c) > 2 and c[2] == 'E':
        lon += float(c.pop(0)) / 60
        lon += float(c.pop(0)) / 3600
        c.pop(0)

    # on renvoie un dictionnaire avec les deux valeurs
    return {'lat': lat, 'lon': lon}


def save_country(database, country, info):
    # préparation de la commande SQL
    c = database.cursor()
    sql = 'REPLACE INTO countries (wp, name, capital, latitude, longitude, currency, superficie, government_type)' \
          ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)'

    # les infos à enregistrer
    name = get_name(info)
    capital = get_capital(info)
    coords = get_coords(info)
    currency = get_currency(info)
    superficie = get_superficie(info)
    government_type = get_government_type(info)

    # soumission de la commande (noter que le second argument est un tuple)
    c.execute(sql, (country, name, capital, coords['lat'], coords['lon'], currency, superficie, government_type))
    conn.commit()


if __name__ == '__main__':
    init_db('africa')

    
    
    
    
    
    
    
    
    
    
    
    
    
