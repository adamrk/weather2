import unittest
import datetime
import pickle
import pdb
import xml.etree.ElementTree

from db import Crag
import extract

class TestExtract(unittest.TestCase):
	def setUp(self):
		filename = 'sample_data/gunks_temp_rain.pickle'
		with open(filename, 'r') as f:
			self.expected_tr = pickle.load(f)

		self.crags = Crag.query.all()
		self.locations = []

		for crag in self.crags:
			self.locations.append({
	            'lat' : crag.lat / 100.0,
	            'lng' : crag.lng / 100.0,
	            'wu_name' : crag.wu_name })
		
	def testCalcTempRain(self):
		data = extract.get_data(
			location = 
				{'lat': 41.74, 'lng': -74.08, 'wu_name': 'NY/New_Paltz'},
			offline=True)

		tr = extract.get_temp_rain(data)
		self.assertEqual(tr, self.expected_tr)

	def testNOAADataFormat(self):
		for location in self.locations:
			xmldat = extract.get_noaa_xml(location, offline=False)

			# check the time layouts can be found
			self.assertNotEqual(xmldat.findall('.//time-layout'), [])
			
			# check highs exist and we can find time-layout
			highs = [x for x in xmldat.findall('.//temperature') if 
				x.get('type') == 'maximum']
			self.assertNotEqual(highs, [])
			self.assertNotEqual(highs[0].get('time-layout', False), False)
			time_layouts = xmldat.findall('.//time-layout')
			layouts = [x.find('layout-key').text for x in time_layouts]
			self.assertTrue(highs[0].get('time-layout') in layouts)
			self.assertNotEqual(highs[0].findall('value'), [])
			for x in highs[0].findall('value'):
				try:
					int(x.text)
				except:
					self.fail("NOAA temp values not all ints")

			# start-valid-times is in the time layouts
			for x in time_layouts:
				self.assertNotEqual(x.findall('start-valid-time'), [])

			# rain element works
			rain_el = xmldat.find('.//probability-of-precipitation')
			self.assertNotEqual(rain_el, None)
			time_layout_rain = rain_el.get('time-layout')
			self.assertNotEqual(time_layout_rain, None)
			self.assertTrue(time_layout_rain in 
				[x.find('layout-key').text for x in time_layouts])
			for x in rain_el.findall('value'):
				if not ('true' == x.get('{http://www.w3.org/2001/XMLSchema-instance}nil')):
					try:
						int(x.text)
					except:
						self.fail("NOAA rain values not all ints")

	def testWUFormat(self):
		for location in self.locations:
			jsondata = extract.get_wu_json(location, offline=False)
			forecasts = jsondata.get('forecast').get('simpleforecast').get('forecastday')
			self.assertNotEqual(forecasts, None)
			for x in forecasts:
				self.assertNotEqual(x.get('date').get('weekday'), None)
				self.assertNotEqual(x.get('high').get('fahrenheit'), None)
				self.assertNotEqual(x.get('pop'), None)
				self.assertNotEqual(x.get('date').get('year'), None)
				self.assertNotEqual(x.get('date').get('month'), None)
				self.assertNotEqual(x.get('date').get('day'), None)
				try:
					int(x.get('high').get('fahrenheit'))
				except:
					self.fail("WU temp value not int")
				try:
					int(x.get('pop'))
				except:
					self.fail("WU pop value not int")

	def testDarkSkyFormat(self):
		for location in self.locations:
			jsondata = extract.get_fore_json(location, offline=False)
			forecasts = jsondata.get('daily').get('data')
			self.assertNotEqual(forecasts, None)
			for x in forecasts:
				self.assertNotEqual(x.get('time'), None)
				self.assertNotEqual(x.get('temperatureMax'), None)
				self.assertNotEqual(x.get('precipProbability'), None)
				try:
					int(x.get('temperatureMax'))
				except:
					self.fail('Dark Sky temp value not int')
				try:
					int(x.get('precipProbability'))
				except:
					self.fail('Dark Sky rain value not int')


if __name__=='__main__':
	crags = Crag.query.all()

	print "testing crags: "
	for crag in crags:
		print crag

	unittest.main()