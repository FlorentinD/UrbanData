import json
from OSMPythonTools.nominatim import Nominatim
import folium
from folium.plugins.measure_control import MeasureControl
from matplotlib import cm

import sys
sys.path.insert(0, './helper')
from geoJsonHelper import groupBy
from geoJsonToFolium import generateFeatureCollection, styleFunction, cmMapColorToHex
from overPassHelper import OverPassHelper

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

for i, osmQuery in enumerate(osmDataFiles):
    file = open(osmQuery.filePath, encoding='UTF-8')
    allObjects = json.load(file)
    objectGroups = groupBy(allObjects, osmQuery.groupByProperty)

    objectMap = generateFeatureCollection(objectGroups, colormaps[i % len(colormaps)], osmQuery.name)
    objectMap.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/maps/map_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
