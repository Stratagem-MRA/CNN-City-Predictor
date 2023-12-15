import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import StreetAPI as SAPI
import shapefile
import json


from urllib.request import urlretrieve
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.plotting import plot_polygon
from os.path import isfile, isdir
from os import mkdir
from ast import literal_eval
from multiprocessing import Pool

def create_top10_boundaries():
	if not isfile('shapefiles/USTop10.shp'):
		#Data was from 2010 census so manually select top 10 US cities by 2020 population with the added restriction only one city is allowed per state.
		cities = [('New York', 'NY'), ('Los Angeles', 'CA'), ('Chicago', 'IL'), ('Houston', 'TX'), ('Phoenix', 'AZ'), ('Philadelphia', 'PA'), ('Jacksonville', 'FL'), ('Columbus', 'OH'), ('Charlotte', 'NC'), ('Indianapolis', 'IN')]
		
		#https://catalog.data.gov/dataset/500-cities-city-boundaries
		gdf = gpd.read_file("City_Bounds/CityBoundaries.shp")
		gdf = gdf[gdf[['NAME','ST']].apply(tuple, axis=1).isin(cities)]
		gdf = gdf.to_crs("epsg:4326")
		gdf.to_file('shapefiles/USTop10.shp')
		print('Created shapefiles/USTop10.shp')
	print("Loaded shapefiles/USTop10.shp\n")
	return gpd.read_file("shapefiles/USTop10.shp")
	
def plot_points(points, poly):
	base = points.plot(markersize=4)
	plot_polygon(poly, ax=base, add_points=False)
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
	
#get_n_points courtesy of https://www.matecdev.com/posts/random-points-in-polygon.html
def get_n_points(gdf_poly, n):
	"""
	Given a GeoDataFrame row returns a GeoDataFrame containing the points and a GeoDataFrame containing the polygon
	The number of returned points will be in the range [0,n]
	"""
	x,y = Random_Points_in_Bounds(gdf_poly['geometry'],n)
	df = pd.DataFrame()
	df['points'] = list(zip(x,y))
	df['points'] = df['points'].apply(Point)
	gdf_points = gpd.GeoDataFrame(df,columns=['points'], geometry='points', crs="epsg:4326")
	gdf_points['NAME'] = gdf_poly['NAME'][0]
	Sjoin = gpd.tools.sjoin(gdf_points, gdf_poly, predicate="within", how='left')
	return gdf_points[Sjoin.index_right==0]

def create_points():
	gdf = gpd.read_file("shapefiles/USTop10.shp")
	result = []
	for i in range(len(gdf)):
		if not isfile(f"shapefiles/{gdf.iloc[i]['NAME']}.shp"):
			poly = get_polys(gdf.iloc[i])
			points = get_n_points(poly,10000)
			points.to_file(f"shapefiles/{gdf.iloc[i]['NAME']}.shp")
			print(f"Created shapefiles/{gdf.iloc[i]['NAME']}.shp")
		result.append(gpd.read_file(f"shapefiles/{gdf.iloc[i]['NAME']}.shp"))
		print(f"Loaded shapefiles/{gdf.iloc[i]['NAME']}.shp")
	print()
	return result
	
def get_points_metadata(points):
	path = f"metadata/{points.iloc[0]['NAME']}.csv"
	if not isfile(path):
		print(f"Creating {path}")
		length = len(points)
		print(f'0/{length}\t0.00%')
		hit = 0
		miss = 0
		i = 0
		dct = {}
		for point in points['geometry']:
			lat = point.y
			lng = point.x
			url = SAPI.meta_url_builder((lat,lng))
			body = json.loads(SAPI.url_open(url))
			status = body['status']
			if status == 'OK':
				hit = hit + 1
				dct[body['pano_id']] = body
			else:
				miss = miss + 1
			i = i+1
			if(i%int(length/20)==0):
				print(f'{i}/{length}\t{i/length*100:.2f}%')
				
		print(f'hits:{hit}\tmisses:{miss}\thit percent:{hit/(hit+miss)*100:.2f}%\tduplicates:{hit-len(dct)}\n')
		df = pd.DataFrame(dct.values())
		df.to_csv(path, index=False)
	else:
		print(f"Loading {path}")
		df = pd.read_csv(path)
	return df

def create_output_dir(name):
	if not isdir("Images/"):
		mkdir("Images/")
	if not isdir(f"Images/{name}/"):
		mkdir(f"Images/{name}/")

def get_image_from_metadata(df_row_tuple):
	idx = df_row_tuple[0]
	df_row = df_row_tuple[1]
	location = literal_eval(df_row['location'])
	fov = 120
	heading = [0,120,240]
	path = [f"Images/{df_row['name']}/{df_row['pano_id']}___{fov}___{head}___{df_row['name']}.jpg" for head in heading]
	print(f"{df_row['name']} {idx}")
	for i in range(len(heading)):
		if not isfile(path[i]):
			url = SAPI.url_builder((location['lat'],location['lng']), fov=fov, heading=heading[i])
			if url is not None:
				urlretrieve(url,path[i])

def get_all_images_from_metadata(metadata_df):
	print(f"Getting images for {metadata_df.iloc[0]['name']}")
	#limiting df to 1000 results in roughly 60000 api calls, 30k of which are charged at 0.007$ for a total of $210 
	df = metadata_df.iloc[0:1000]
	with Pool(8) as p:
		p.map(get_image_from_metadata, df.iterrows())
	

if __name__ == "__main__":		
	bounds = create_top10_boundaries()
	points = create_points()
	for p in points:
		get_points_metadata(p)
	for name in bounds['NAME']:
		df = pd.read_csv(f"metadata/{name}.csv")
		df['name'] = name
		create_output_dir(name)
		get_all_images_from_metadata(df)
		
#plot_points(points[0],bounds.iloc[0]['geometry'])