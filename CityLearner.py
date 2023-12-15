from fastai.vision.all import *
from os.path import isfile
import torch
import pathlib

import pandas as pd

def get_street_path(row):
	fov = 120
	heading = [0,120,240]
	path = [f"Images/{row['name']}/{row['pano_id']}___{fov}___{head}___{row['name']}.jpg" for head in heading]
	return [pathlib.Path(p) for p in path]
	
def get_street_images(df):
	lsts = df.apply(get_street_path, axis=1).tolist()
	#return flattened list
	return [p for lst in lsts for p in lst]
	
def get_city(pathlike):
	return x.name[:-4].split('___')[3]
#board_block = DataBlock(
#    blocks=(ImageBlock, RegressionBlock),
#    get_items=get_chess_images,
#    splitter=RandomSplitter(valid_pct=0.125, seed=42),
#    get_y=white_elo
#    )
if not isfile("metadata/allcities.csv"):
	cities = [('New York', 'NY'), ('Los Angeles', 'CA'), ('Chicago', 'IL'), ('Houston', 'TX'), ('Phoenix', 'AZ'), ('Philadelphia', 'PA'), ('Jacksonville', 'FL'), ('Columbus', 'OH'), ('Charlotte', 'NC'), ('Indianapolis', 'IN')]
	result = []
	for city in cities:
		df = pd.read_csv(f"metadata/{city[0]}.csv")
		df['name'] = city[0]
		#We limited data generation to first 1000 points. Can delete this if we gather more data later
		df = df.iloc[0:1000]
		result.append(df)
	df = pd.concat(result)
	df.to_csv('metadata/allcities.csv', index=False)
	print(df.head())
else:
	df = pd.read_csv('metadata/allcities.csv')
	print(df.head())
	
streetview_block = DataBlock(
	blocks=(ImageBlock, CategoryBlock),
	get_items=get_street_images,
	splitter=RandomSplitter(valid_pct=0.2, seed=42),
	get_y=get_city
	)
	
#TODO test out dataloaders on above block