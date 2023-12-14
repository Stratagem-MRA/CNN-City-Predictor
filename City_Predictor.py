import shapefile
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.plotting import plot_polygon
from os.path import isfile

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
	print("Loaded shapefiles/USTop10.shp")
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
	return result

if __name__ == "__main__":		
	bounds = create_top10_boundaries()
	points = create_points()
	#plot_points(points[0],bounds.iloc[0]['geometry'])