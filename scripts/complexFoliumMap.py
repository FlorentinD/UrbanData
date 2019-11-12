import json
import folium
from matplotlib import cm
from jsonToGeoJSON import groupBy
from foliumHelper import generateFeatureCollection, styleFunction, cmMapColorToHex
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl
from overpassHelper import OverPassHelper

# TODO: adapt to new API 

# postfix for f.i. file_names
areaName = "pieschen" 
# area to query
pieschen = Nominatim().query('Pieschen, Dresden, Germany')
osmDataFiles = OverPassHelper().fetch(pieschen.areaId(), areaName, overrideFiles=False)

pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[pieschenCoord["lat"], pieschenCoord["lon"]], tiles='Stamen Toner', zoom_start=15)

# matplotlib colormap names
colormaps = ["hsv", "BrBG", "coolwarm"]

objectTypeTagMapping = {"streets": "highway", "buildings": "building", "landuse": "landuse"}

for i, (objectType, featureFile) in enumerate(osmDataFiles.items()):
    file = open(featureFile, encoding='UTF-8')
    allObjects = json.load(file)
    osmTag = objectTypeTagMapping[objectType]
    objectGroups = groupBy(allObjects, osmTag)

    objectMap = generateFeatureCollection(
    objectGroups, objectType, colormaps[i % len(colormaps)], osmTag)
    objectMap.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/map_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
