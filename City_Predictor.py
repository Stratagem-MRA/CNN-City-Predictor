import json
import shapefile
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from shapely.geometry import Point, Polygon, MultiPolygon
from urllib.parse import urlencode
from urllib.request import urlopen, urlretrieve
from sign_url import sign_url

try:
	from config import api_key
	from config import secret
except:
	print('You must provide your own api_key and secret in a file named config.py\nPlease reference sample_config.py to view the correct format')
	raise
	
#https://maps.googleapis.com/maps/api/streetview?parameters
#parameters
	#location - a latitude and longitude coordinates pair ex: (40.457375,-80.009353)
	#size - output size of the image in pixels. Size is specified as {width}x{height} [0,640]x[0,640]
	#key - API Key
	#heading - indicates the compass heading of the camera [0,360] 0=North
	#fov - determines the horizontal field of view of the image [0-120]
		#When dealing with a Street View image of a set size, field of view in essence represents zoom, with smaller numbers indicating a higher level of zoom.
	#pitch - specifies the up or down angle of the camera relative to the Street View vehicle [-90,90] 0=flat
	#radius - sets a radius, specified in meters, in which to search for a panorama [0,inf)
def input_url_builder(location, size=[640,640], key=api_key(), heading=None, fov=None, pitch=None, radius=None):
	GMAPS_URL = 'https://maps.googleapis.com/maps/api/streetview?'
	
	params = {
		'location': f'{location[0]},{location[1]}',
		'size': f'{size[0]}x{size[1]}',
		'key': key
	}
		
	if heading is not None:
		params['heading'] = heading
		
	if fov is not None:
		params['fov'] = fov
		
	if pitch is not None:
		params['pitch'] = pitch
		
	if radius is not None:
		params['radius'] = radius
	
	return sign_url(GMAPS_URL + urlencode(params),secret())
	
def meta_url_builder(location, size=[640,640], key=api_key(), heading=None, fov=None, pitch=None, radius=None):
	GMAPS_URL = 'https://maps.googleapis.com/maps/api/streetview/metadata?'
	
	params = {
		'location': f'{location[0]},{location[1]}',
		'size': f'{size[0]}x{size[1]}',
		'key': key
	}
	
	if heading is not None:
		params['heading'] = heading
		
	if fov is not None:
		params['fov'] = fov
		
	if pitch is not None:
		params['pitch'] = pitch
		
	if radius is not None:
		params['radius'] = radius
	
	return sign_url(GMAPS_URL + urlencode(params),secret())

def url_builder(location, size=[640,640], key=api_key(), heading=None, fov=None, pitch=None, radius=None):
	meta_url = meta_url_builder(location, size=size, key=key, heading=heading, fov=fov, pitch=pitch, radius=radius)
	
	with urlopen(meta_url) as response:
		body = response.read()

	meta_status = json.loads(body)['status']
	if meta_status == 'ZERO_RESULTS' or meta_status == 'NOT_FOUND':
		print(f'invalid location with status: {meta_status}')
		return None
	elif meta_status != 'OK':
		raise RuntimeError(f'unexpected response from meta_url: {meta_status}')
		
	return input_url_builder(location, size=size, key=key, heading=heading, fov=fov, pitch=pitch, radius=radius)
	
#urlretrieve(url,'temp.jpeg')

def create_top10_boundaries():
	#https://catalog.data.gov/dataset/500-cities-city-boundaries
	sf = shapefile.Reader("City_Bounds/CityBoundaries.shp")

	#Above data was from 2010 census so manually select top 10 US cities by 2020 population
	cities = [('New York', 'NY'), ('Los Angeles', 'CA'), ('Chicago', 'IL'), ('Houston', 'TX'), ('Phoenix', 'AZ'), ('Philadelphia', 'PA'), ('Jacksonville', 'FL'), ('Columbus', 'OH'), ('Charlotte', 'NC'), ('Indianapolis', 'IN')]

	w = shapefile.Writer('shapefiles/USTop10')
	w.fields = sf.fields[1:]
	for shaperec in sf.iterShapeRecords():
		if (shaperec.record[0],shaperec.record[2]) in cities:
			w.record(*shaperec.record)
			w.shape(shaperec.shape)
	w.close()
	
def get_multipolygon(shape):
	return MultiPolygon([Polygon(p[0],p[1:]) for p in shape.__geo_interface__['coordinates']])

def get_polygon(shape):
	return Polygon(shape.__geo_interface__['coordinates'][0],shape.__geo_interface__['coordinates'][1:])

def plot_multipolygon(mp):
	for p in mp.geoms:
		plt.plot(*p.exterior.xy)
		for hole in p.interiors:
			plt.plot(*hole.xy)
	plt.show()
	
def plot_polygon(p):
	plt.plot(*p.exterior.xy)
	for hole in p.interiors:
		plt.plot(*hole.xy)
	plt.show()
#Random_Points_in_Bounds courtesy of https://www.matecdev.com/posts/random-points-in-polygon.html
def Random_Points_in_Bounds(polygon, number):   
    minx, miny, maxx, maxy = polygon.bounds
    x = np.random.uniform( minx, maxx, number )
    y = np.random.uniform( miny, maxy, number )
    return x, y
	
def get_n_points(n, shape):
	"""
	Given a shape returns a GeoDataFrame containing the points and a GeoDataFrame containing the polygon
	The number of returned points will be in the range [0,n]
	"""
	bbox = shape.bbox
	type = shape.__geo_interface__['type']
	if type == 'MultiPolygon':
		p = get_multipolygon(shape)
	elif type == 'Polygon':
		p = get_polygon(shape)
	else:
		raise(RuntimeError(f'unexpected type from shape: {type}'))
		
	#Following portion of get_n_points courtesy of https://www.matecdev.com/posts/random-points-in-polygon.html
	gdf_poly = gpd.GeoDataFrame(index=['myPoly'], geometry=[p])
	x,y = Random_Points_in_Bounds(p,n)
	df = pd.DataFrame()
	df['points'] = list(zip(x,y))
	df['points'] = df['points'].apply(Point)
	gdf_points = gpd.GeoDataFrame(df, geometry='points')
	Sjoin = gpd.tools.sjoin(gdf_points, gdf_poly, predicate="within", how='left')
	return gdf_points[Sjoin.index_right=='myPoly'], gdf_poly
	
sf = shapefile.Reader("shapefiles/USTop10.shp")

#'Houston', 'Jacksonville', 'New York', 'Philadelphia', 'Charlotte', 'Columbus', 'Indianapolis', 'Chicago', 'Phoenix', 'Los Angeles'
shape_dct = {}
for shaperec in sf.iterShapeRecords():
	shape_dct[shaperec.record[0]] = shaperec.shape
	
points, base = get_n_points(10000, shape_dct['Houston'])