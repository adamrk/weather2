import unittest
import datetime
import pickle

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
			xml = extract.get_noaa_xml(location, offline=False)
			self.assertNotEqual(xml.findall('.//time-layout'), [])
			highs = [x for x in xml.findall('.//temperature') if 
				x.get('type') == 'maximum']
			self.assertNotEqual(highs, [])
			self.assertNotEqual(highs[0].get('time-layout', False), False)
			time_layouts = xml.findall('.//time-layout')
			layouts = [x.find('layout-key').text for x in time_layouts]
			self.assertTrue(highs[0].get('time-layout') in layouts)
			


if __name__=='__main__':
	unittest.main()