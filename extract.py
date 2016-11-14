import sys
import requests
import os
import json
from datetime import date, datetime
import xml.etree.ElementTree as xml

"""
TODO:

    Make API calls on different threads
    Add more locations
"""

################## NOAA API ######################

def get_noaa_xml(location, offline=False):
    response = requests.get('http://graphical.weather.gov/xml/sample_products/browser_interface/ndfdBrowserClientByDay.php?lat=%0.2f&lon=%0.2f&format=24+hourly'
                                % (location['lat'], location['lng']))
    result = xml.XML(response.text)
    return result

def get_noaa_temp_rain(xmldata):
    # these describe the time formats
    time_layouts = xmldata.findall('.//time-layout')

    # the element containing highs
    temp_elem = [x for x in xmldata.findall('.//temperature') 
                if x.get('type') == 'maximum'][0]
    temp_time_layout = temp_elem.get('time-layout')
    temp_time_elem = [x for x in time_layouts if 
        x.find('layout-key').text == temp_time_layout][0]
    # zip it with the associated times
    temps = zip([x.text for x in temp_elem.findall('value')],
                [x.text for x in temp_time_elem.findall('start-valid-time')])
    
    # the element containing chance of rain
    rain_elem = xmldata.find('.//probability-of-precipitation')
    rain_time_layout = rain_elem.get('time-layout')
    rain_time_elem = [x for x in time_layouts if
        x.find('layout-key').text == rain_time_layout][0]
    # zip with times
    rains = zip([x.text for x in rain_elem.findall('value')],
                [x.text for x in rain_time_elem.findall('start-valid-time')])
    alls = []
    for t in temps:
        for r in rains:
            if t[1] == r[1]:
                thedate = datetime.strptime(t[1][:10], '%Y-%m-%d').date()
                alls.append({'date': thedate,
                             'day': thedate.strftime('%A'),
                             'temp': int(t[0]),
                             'rain': int(r[0])
                              })
    return alls

################## WUnderground ##################
try:
    api_key = os.environ['API_KEY']
except KeyError:
    print "please set the API_KEY to for wunderground."
    exit()

def get_wu_json(location, offline = False):
    if offline:
        file = open('sample_data/sample_wu.json', 'r')
        result = json.load(file)
    else:
        response = requests.get('http://api.wunderground.com/api/%s/forecast10day/q/%s.json' % 
                (api_key, location['wu_name']))
        result = response.json()
    return result

def get_wu_temp_rain(json):
    daily_forecasts = json['forecast']['simpleforecast']['forecastday']
    daily_high_rain = map(lambda x: {
        'day': x['date']['weekday'], 
        'temp': int(x['high']['fahrenheit']), 
        'rain': int(x['pop']),
        'date': date(x['date']['year'], x['date']['month'], x['date']['day'])}, daily_forecasts)
    return daily_high_rain[:9]


###################### Forecast.ai ###########################
##### Did they just change their name to DarkSky.net ???? ####
try:
    fore_api_key = os.environ['FORE_API_KEY']
except KeyError:
    print "please set the FORE_API_KEY for forecast.ai"
    exit()

def get_fore_json(location, offline = False):
    if offline:
        file = open('sample_data/sample_fore.json', 'r')
        result = json.load(file)
    else:
        response = requests.get('https://api.darksky.net/forecast/%s/%0.6f,%0.6f' % 
            (fore_api_key, location['lat'], location['lng'] ) )
        result = response.json()
    return result

def get_fore_temp_rain(json):
    daily_forecasts = json['daily']['data']
    daily_high_rain = map(lambda x: {
        'day': date.fromtimestamp(x['time']).strftime('%A'), 
        'temp': int(x['temperatureMax']), 
        'rain': int(float(x['precipProbability'])*100),
        'date': date.fromtimestamp(x['time']) }, daily_forecasts)
    return daily_high_rain[:9]


######################## Collecting and Aggregating ###########################
def get_data(**kwargs):
    xmldata = get_noaa_xml(**kwargs)
    json1 = get_wu_json(**kwargs)
    json2 = get_fore_json(**kwargs)
    return {'noaa': xmldata, 'wu': json1, 'fore': json2}

def get_temp_rain(data):
    noaa_tr = get_noaa_temp_rain(data['noaa'])
    wu_tr = get_wu_temp_rain(data['wu'])
    fore_tr = get_fore_temp_rain(data['fore'])
    return {'noaa': noaa_tr, 'wu': wu_tr, 'fore': fore_tr}

def agg_data(data, date, temp_or_rain):
    values = []
    num_values = 0
    for x in data.values():
        for y in x:
            if y['date'] == date:
                values.append(y[temp_or_rain])
                num_values += 1
    mean = float(sum(values)) / num_values
    dev = pow(sum(map(lambda x: pow(x - mean, 2), values)) / (num_values - 1), 0.5)
    return {'mean': mean, 'dev': dev}

def print_data(**kwargs):
    xmldata = get_noaa_xml(**kwargs)
    noaa_data = get_noaa_temp_rain(xmldata)
    print 'data from NOAA:'
    for x in noaa_data:
        print 'on %s (%s) the temp is %d and rain is %d' % (x['day'], x['date'].strftime('%a, %b, %d'), x['temp'], x['rain'])

    json = get_wu_json(**kwargs)
    wu_data = get_wu_temp_rain(json)
    print 'data from WUnderground:'
    for x in wu_data:
        print 'on %s (%s) the temp is %d and rain is %d' % (x['day'], x['date'].strftime('%a, %b, %d'), x['temp'], x['rain'])

    json2 = get_fore_json(**kwargs)
    fore_data = get_fore_temp_rain(json2)
    print 'data from Forecast.ai:'
    for x in fore_data:
        print 'on %s (%s) the temp is %d and rain is %d' % (x['day'], x['date'].strftime('%a, %b, %d'), x['temp'], x['rain'])

########### Dark Sky for Actual Historical ##############
def get_actual_json(location, time):
    string = ("https://api.darksky.net/forecast/%s/%0.4f,%0.4f,%s"
              "?exclude=currently,minutely,hourly,alerts,flags"
              % (fore_api_key, location['lat'], location['lng'],
                 time.strftime("%s") ) )
    raw = requests.get(string)
    json = raw.json()
    return json

def get_actual_temp_rain(json):
    temp = json['daily']['data'][0]['apparentTemperatureMax']
    rain = json['daily']['data'][0].get('precipIntensityMax', 0)
    return {'temp':temp, 'rain':rain}

if  __name__ == "__main__":
    offline = len(sys.argv) == 2 and sys.argv[1] == 'offline'
    location = {'lat': 41.74, 'lng': -74.08, 'wu_name': 'NY/New_Paltz'}
    print_data(location = location, offline = offline)