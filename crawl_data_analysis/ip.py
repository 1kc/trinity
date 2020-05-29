import time
from pprint import pprint
import requests
import json

from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
from geopandas import GeoDataFrame
import matplotlib.pyplot as plt
import numpy as np

API_KEY = '3c42c1343bddae3a6dba48f9979cbc94' # normal account

FILENAME = 'crawled_ips.txt'
RESPONSE_FILE = 'responses.json'

def get_ips(filename: str) -> list:
    """ Reads ips from a list of files """
    ips = []
    with open(filename, 'r') as f:
        ips = f.read().splitlines()

    return ips

def fetch_locations(ips: list) -> list:
    """ Use ips give in list format to make API calls to ipstack 
    to get locations 
    """
    info = []  
    count = 1
    responses = []
    for ip in ips:
        api = 'http://api.ipstack.com/' + ip + '?access_key=' + API_KEY 
        response = requests.get(api).json()
        print('({}/{}) Found location for {} at {}, {} ({}, {})'.format(      \
            count,
            len(ips),
            ip,
            response['country_name'],
            response['city'],
            response['latitude'],
            response['longitude']))
        info.append((response['latitude'], response['longitude'],             \
            response['country_name'], response['city'],                       \
            response['connection']['isp']))
        count += 1
        responses.append(response)
    save_response_to_file(responses)
    return info 

def load_from_file(filename: str) -> list:
    """Can load the files provided they are in the same json format as
    what is given in the free version of ipstack
    """ 
    with open(filename, 'r') as f:
        responses = json.load(f)
    info = []  
    for response in responses:

        info.append((response['latitude'], response['longitude'],             \
            response['country_name'], response['city'],                      \
            response['connection']['isp']))
    return info 

def save_response_to_file(responses: dict):
    """ Saves the responses from fetching to a file"""
    with open(RESPONSE_FILE, 'w') as f:
        j = json.dumps(responses, indent=4)
        print(j, file=f)

def format_pct(df_column):
    """Used for formatting the numbers on the pie chart the pie function accepts formatpct as a 
    keyword arg that requires a function reference"""
    def format(val):
        a  = np.round(val/100*sum(df_column.tolist()), 0)
        return '%d(%.2f%s)' % (int(a), val, '%')
    return format

def country_breakdown(info:list, countries: list):
    """Provides a country breakdown visualisation as a pie chart"""
    d = {'isp': [], 'country': []}
    for coord in info:
        d['isp'].append(coord[-1])
        d['country'].append(coord[2])
    df = pd.DataFrame(data=d)

    mask1 = df['country'].isin(countries)
    others = df[~mask1]
    print(others)

    others = others.groupby('country', as_index=False)['country'].agg({'isp_country_count':'count'}).set_index('country')
    others = others.sort_values(by='isp_country_count', ascending=False)

    for country in countries:
        print('####' + country + '####')
        mask = df['country'] == country
        df_isp = df.loc[mask]


        df_isp = df_isp.groupby('isp', as_index=False)['isp'].agg({'isp_country_count':'count'}).set_index('isp')
        df_isp = df_isp.sort_values(by='isp_country_count', ascending=False)
        if len(df_isp) > 7:
            tmp = df_isp[:7].copy() # Take the top 10 countries
            new_row = pd.DataFrame(data={
                'isp': ['others'],
                'isp_country_count': [df_isp['isp_country_count'][7:].sum()]
            }).set_index('isp')
            df_isp = pd.concat([tmp, new_row])

        df_isp.plot.pie(y='isp_country_count', autopct=format_pct(df_isp['isp_country_count']), pctdistance=0.8, colors=plt.cm.tab20.colors)
        legend = plt.legend()
        legend.remove()
        plt.axis('off')
        plt.savefig('breakdown_for_' + country + '.png', bbox_inches='tight')

def breakdown_isp_cities(info: list, cities: list):
    """ Provides a visualization using a pie chart of all ISPs on where their nodes are located by city"""
    d = {'isp': [], 'city': []}
    for coord in info:
        d['isp'].append(coord[-1])
        d['city'].append(coord[3])
    df = pd.DataFrame(data=d)

    for city in cities:
        print('####' + city + '####')
        mask = df['city'] == city
        df_isp = df.loc[mask]


        df_isp = df_isp.groupby('isp', as_index=False)['isp'].agg({'isp_city_count':'count'}).set_index('isp')
        df_isp = df_isp.sort_values(by='isp_city_count', ascending=False)
        if len(df_isp) > 8:
            tmp = df_isp[:8].copy() # Take the top 10 countries
            new_row = pd.DataFrame(data={
                'isp': ['others'],
                'isp_city_count': [df_isp['isp_city_count'][8:].sum()]
            }).set_index('isp')
            df_isp = pd.concat([tmp, new_row])

        df_isp.plot.pie(y='isp_city_count', autopct=format_pct(df_isp['isp_city_count']), pctdistance=0.7, colors=plt.cm.tab20.colors)
        legend = plt.legend()
        legend.remove()
        plt.axis('off')
        plt.savefig('isp_breakdown_for_' + city + '.png')
        
    

def breakdown_isp_countries(info: list, isps: list):
    """ Provides a visualization of all ISPs on where their nodes are located by country"""
    d = {'isp': [], 'country': []}
    for coord in info:
        d['isp'].append(coord[-1])
        d['country'].append(coord[2])
    df = pd.DataFrame(data=d)

    mask1 = df['isp'].isin(isps)

    for isp in isps:
        print('####' + isp + '####')
        mask = df['isp'] == isp
        df_isp = df.loc[mask]

        df_isp = df_isp.groupby('country', as_index=False)['country'].agg({'isp_country_count':'count'}).set_index('country')
        df_isp = df_isp.sort_values(by='isp_country_count', ascending=False)
        if len(df_isp) > 8:
            tmp = df_isp[:8].copy() # Take the top 10 countries
            new_row = pd.DataFrame(data={
                'country': ['others'],
                'isp_country_count': [df_isp['isp_country_count'][8:].sum()]
            }).set_index('country')
            df_isp = pd.concat([tmp, new_row])
        if isp == 'Alibaba (Us) Technology Co. Ltd.':
            tmp = df_isp[:5].copy() # Take the top 10 countries
            new_row = pd.DataFrame(data={
                'country': ['others'],
                'isp_country_count': [df_isp['isp_country_count'][5:].sum()]
            }).set_index('country')
            df_isp = pd.concat([tmp, new_row])


        df_isp.plot.pie(y='isp_country_count', autopct=format_pct(df_isp['isp_country_count']), pctdistance=0.7, colors=plt.cm.tab20.colors)
        legend = plt.legend()
        legend.remove()
        plt.axis('off')
        plt.savefig('breakdown_for_' + isp + '.png', bbox_inches='tight')
        
    
def breakdown_isp_alt(info: list):
    """ Piechart to visualize the top 10 cloud hosts on the network"""
    d = {'isp': []}
    for coord in info:
        d['isp'].append(coord[-1])
    df = pd.DataFrame(data=d)
    
    df = df.groupby('isp', as_index=False)['isp'].agg({'isp_count':'count'}).set_index('isp')
    df = df.sort_values(by='isp_count', ascending=False)
    alt_row = pd.DataFrame(data={
        'isp': ['Cloud hosted'],
        'isp_count': [df['isp_count'][:10].sum()]
    }).set_index('isp')
    new_row = pd.DataFrame(data={
        'isp': ['Individually hosted'],
        'isp_count': [df['isp_count'][10:].sum()]
    }).set_index('isp')
    df_final = pd.concat([alt_row, new_row])

    df_final.plot.pie(y='isp_count', autopct=format_pct(df['isp_count']), colors=plt.cm.tab20.colors)
    legend = plt.legend()
    legend.remove()
    plt.axis('off')
    plt.savefig('isp_count_alt.png', bbox_inches='tight')

def breakdown_isp(info: list):
    """ Break down of ISPs for all nodes across the world and graphed on a 
    pie chart
    """
    d = {'isp': []}
    for coord in info:
        d['isp'].append(coord[-1])
    df = pd.DataFrame(data=d)
    df_country = pd.DataFrame(data=d)
    
    df = df.groupby('isp', as_index=False)['isp'].agg({'isp_count':'count'}).set_index('isp')
    df = df.sort_values(by='isp_count', ascending=False)
    df_final = df[:14].copy() # Take the top 14 countries
    new_row = pd.DataFrame(data={
        'isp': ['others'],
        'isp_count': [df['isp_count'][14:].sum()]
    }).set_index('isp')
    df_final = pd.concat([df_final, new_row])

    df_final.plot.pie(y='isp_count', autopct=format_pct(df['isp_count']), colors=plt.cm.tab20.colors)
    legend = plt.legend()
    legend.remove()
    plt.axis('off')
    plt.savefig('isp_count.png', bbox_inches='tight')

def plot(info: list):
    """ Plot coordinates on a world map and manipulate data to give aggregations of 
    countries and cities to put on a pie chart
    """
    geometry = []
    d = {'latitude': [], 'longitude': [], 'country': [], 'city': []}
    for coord in info:
        d['latitude'].append(coord[0])
        d['longitude'].append(coord[1])
        d['country'].append(coord[2])
        d['city'].append(coord[3])
        geometry.append(Point(coord[1], coord[0]))
    df = pd.DataFrame(data=d)
    df.set_index('country')

    country_df = df.groupby('country', as_index=False)['country'].agg({'country_count':'count'}).set_index('country')
    country_df = country_df.sort_values(by='country_count', ascending=False) 
    country_df_final = country_df[:9].copy() # Take the top 10 countries
    new_row = pd.DataFrame(data={
        'country': ['others'],
        'country_count': [country_df['country_count'][9:].sum()]
    }).set_index('country')
    country_df_final = pd.concat([country_df_final, new_row])

    city_df = df.groupby('city', as_index=False)['city'].agg({'city_count':'count'}).set_index('city')
    city_df = city_df.sort_values(by='city_count', ascending=False)
    city_df_final = city_df[:12].copy()
    new_row = pd.DataFrame(data ={
        'city': ['others'],
        'city_count': [city_df['city_count'][12:].sum()]
    }).set_index('city')
    city_df_final = pd.concat([city_df_final, new_row])

    gdf = GeoDataFrame(df, geometry=geometry)
    print(country_df_final.values.tolist())
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    gdf.plot(ax=world.plot(figsize=(10, 6)), marker='x', color='red', markersize=15)
    plt.savefig('worldmap.png', bbox_inches='tight')

    country_df_final.plot.pie(y='country_count', pctdistance=0.90, autopct=format_pct(country_df_final['country_count']), colors=plt.cm.tab20.colors)
    legend = plt.legend()
    legend.remove()
    plt.axis('off')
    plt.savefig('country_img.png')
    
    city_df_final.plot.pie(y='city_count', autopct=format_pct(city_df_final['city_count']), colors=plt.cm.tab20.colors)
    legend = plt.legend()
    legend.remove()
    plt.axis('off')
    plt.savefig('city_img.png')


if __name__ == '__main__':
    print('### Starting ###')
    ips = get_ips(FILENAME)
    #info = fetch_locations(ips)
    info = load_from_file(RESPONSE_FILE)
    plot(info) # Plotting the world map and pie chart breakdowns of nodes by country and city
    breakdown_isp(info)
    breakdown_isp_countries(info, ['amazon.com, Inc',                       \
        'Digitalocean LLC',                                            \
        'Chinanet',                                                    \
        'Hetzner Online Gmbh',                                         \
        'amazon.com Inc.',                                             \
        'Contabo Gmbh',                                                \
        'Alibaba (Us) Technology Co. Ltd.',                            \
        'China Unicom china169 Backbone',                              \
        'Ovh Sas',                                                     \
        'Shenzhen Tencent Computer Systems Company Limited',           \
        'Google LLC',                                                  \
        'Hangzhou Alibaba Advertising Co. Ltd.',                       \
        'Choopa LLC',                                                  \
        'Microsoft Corporation'                                        \
    ])
    country_breakdown(info, ['United States', 
        'China', 
        'Germany', 
        'Hong Kong SAR China',
        'Singapore',
        'Russia',
        ])
    breakdown_isp_alt(info)
    breakdown_isp_cities(info, ['Ashburn'])
    print('### Done ###')