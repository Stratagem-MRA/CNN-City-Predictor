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
from os.path import isfile

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
	if not isfile('shapefiles/USTop10.shp'):
		#Data was from 2010 census so manually select top 10 US cities by 2020 population with the added restriction only one city is allowed per state.
		cities = [('New York', 'NY'), ('Los Angeles', 'CA'), ('Chicago', 'IL'), ('Houston', 'TX'), ('Phoenix', 'AZ'), ('Philadelphia', 'PA'), ('Jacksonville', 'FL'), ('Columbus', 'OH'), ('Charlotte', 'NC'), ('Indianapolis', 'IN')]
		
		#https://catalog.data.gov/dataset/500-cities-city-boundaries
		gdf = gpd.read_file("City_Bounds/CityBoundaries.shp")
		gdf = gdf[gdf[['NAME','ST']].apply(tuple, axis=1).isin(cities)]
		gdf = gdf.to_crs("epsg:4326")
		gdf.to_file('shapefiles/USTop10.shp')
		print('Saved shapefiles/USTop10.shp')

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
	
def plot_points(points, poly):
	base = poly.boundary.plot(linewidth=1, edgecolor='black')
	points.plot(ax=base, markersize=4)
	plt.show()
	
#Random_Points_in_Bounds courtesy of https://www.matecdev.com/posts/random-points-in-polygon.html
def Random_Points_in_Bounds(polygon, number):
	minx, miny, maxx, maxy = polygon[0].bounds
	x = np.random.uniform( minx, maxx, number )
	y = np.random.uniform( miny, maxy, number )
	return x, y
	
def get_polys(gdf_row):
	gdf = gpd.GeoDataFrame(geometry=[gdf_row['geometry']], crs="epsg:4326")
	gdf['NAME'] = gdf_row['NAME']
	return gdf
	
def get_n_points(gdf_poly, n):
	"""
	Given a GeoDataFrame row returns a GeoDataFrame containing the points and a GeoDataFrame containing the polygon
	The number of returned points will be in the range [0,n]
	"""

	#Following portion of get_n_points courtesy of https://www.matecdev.com/posts/random-points-in-polygon.html
	x,y = Random_Points_in_Bounds(gdf_poly['geometry'],n)
	df = pd.DataFrame()
	df['points'] = list(zip(x,y))
	df['points'] = df['points'].apply(Point)
	gdf_points = gpd.GeoDataFrame(df,columns=['points'], geometry='points', crs="epsg:4326")
	gdf_points['NAME'] = gdf_poly['NAME'][0]
	Sjoin = gpd.tools.sjoin(gdf_points, gdf_poly, predicate="within", how='left')
	return gdf_points[Sjoin.index_right==0]

#create_top10_boundaries()
def create_points():
	gdf = gpd.read_file("shapefiles/USTop10.shp")
	result = []
	for i in range(len(gdf)):
		if not isfile(f"shapefiles/{gdf.iloc[i]['NAME']}.shp"):
			poly = get_polys(gdf.iloc[i])
			points = get_n_points(poly,10000)
			print(f"Saved shapefiles/{gdf.iloc[i]['NAME']}.shp")
			points.to_file(f"shapefiles/{gdf.iloc[i]['NAME']}.shp")
			result.append(points)
		else:
			result.append(gpd.read_file(f"shapefiles/{gdf.iloc[i]['NAME']}.shp"))
	return result

if __name__ == "__main__":		
	create_top10_boundaries()
	create_points()
	
#TODO we may want to split this in two files since API stuff seems pretty unrelated to the rest