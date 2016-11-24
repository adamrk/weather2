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
					self.fail("temp values not all ints")

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
						self.fail("rain values not all ints")


if __name__=='__main__':
	unittest.main()