import sys
import bs4
import re
import requests
import os
import json
from urllib2 import urlopen
from datetime import date, datetime, timedelta

"""
TODO:

    Take care of NOAA on holidays - e.g. They will say 'Labor Day' instead of 'Monday'
    Make API calls on different threads
    Add more locations
"""

def previous_day(day):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    inx = days.index(day)
    return days[(inx - 1) % 7]

############## NOAA ####################
## Should probably use the API, but scraping for fun

# To extract the temp in two steps
regex_temp_sentence = re.compile('(H|h)igh near -?\d{1,3}')
regex_temp_digits = re.compile('-?\d{1,3}')

def get_temp(string):
    temp_sen_match = re.search(regex_temp_sentence, string)
    if temp_sen_match == None:
        result = None
    else:
        result = re.search(regex_temp_digits, temp_sen_match.group()).group()
    return result

# To extract chance of rain in two steps
regex_rain_sentence = re.compile('Chance of precipitation is \d{2}%')
regex_rain_digits = re.compile('\d{2}')

def get_rain(string):
    rain_sen_match = re.search(regex_rain_sentence, string)
    if rain_sen_match == None:
        result = 0
    else:
        result = re.search(regex_rain_digits, rain_sen_match.group()).group()
    return result


def get_noaa_soup(location, offline = False):
    if offline:
        file = open('sample_data/sample_noaa_fake.html', 'r')
        result = bs4.BeautifulSoup(file, 'html.parser')
    else:
        string = "http://forecast.weather.gov/MapClick.php?lat=%0.6f&lon=%0.6f" % (location['lat'], location['lng'])
        html = urlopen(string)
        result = bs4.BeautifulSoup(html, 'html.parser')
    return result


def get_noaa_temp_rain(soup):
    """ Return an array of dicts with attributes 'date', 'day', 'temp', 'rain' """

    body = soup.find(id='detailed-forecast-body')
    daily_forecasts = map(lambda x: {'day' : unicode(x.div.b.string), 'forecast' : unicode(x.find_all('div')[1].string)}, body.contents[1:-1])
    daily_forecasts = filter(lambda x: x['day'].find('Night') < 0 and x['day'].find('Tonight') < 0 and x['day'].find('night') < 0, daily_forecasts)
    daily_high_rain = map(lambda x: {'day': x['day'], 'temp': int(get_temp(x['forecast'])), 'rain': int(get_rain(x['forecast']))}, daily_forecasts)
    # sometimes current day is listed as today or this afternoon. change based on later dates.
    last_day = daily_high_rain[1]['day']
    daily_high_rain[0]['day'] = previous_day(last_day)
    # find if first day is today or tomorrow. Then assign a date to each element
    date_string = unicode(soup.find(id='about_forecast').find_all(attrs={'class':'fullRow'})[1].find(attrs={'class':'right'}).string)
    try:
        curr_date = datetime.strptime(date_string, '%I:%M %p EDT %b %d, %Y').date()
    except:
        curr_date = datetime.strptime(date_string, '%I:%M %p PDT %b %d, %Y').date()
    one_day = timedelta(days=1)
    if daily_high_rain[0]['day'] == curr_date.strftime('%A'):
        first_date = curr_date
    else:
        first_date = curr_date + one_day

    for i in range(len(daily_high_rain)):
        daily_high_rain[i]['date'] = first_date + (one_day*i)

    return daily_high_rain[:9]

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
    soup = get_noaa_soup(**kwargs)
    json1 = get_wu_json(**kwargs)
    json2 = get_fore_json(**kwargs)
    return {'noaa': soup, 'wu': json1, 'fore': json2}

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
    soup = get_noaa_soup(**kwargs)
    noaa_data = get_noaa_temp_rain(soup)
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