import json
import folium
from matplotlib import cm
from jsonToGeoJSON import groupBy
from foliumHelper import generateFeatureCollection, styleFunction, cmMapColorToHex
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl
from overpassHelper import OverPassHelper

# postfix for f.i. file_names
areaName = "pieschen" 
# area to query
pieschen = Nominatim().query('Pieschen, Dresden, Germany')
OverPassHelper().fetch(pieschen.areaId(), areaName, overrideFiles=True)

pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[pieschenCoord["lat"], pieschenCoord["lon"]], tiles='Stamen Toner', zoom_start=15)


file = open("out/streets_{}.json".format(areaName), encoding='UTF-8')
all_streets = json.load(file)
streetGroups = groupBy(all_streets, ["highway"])

streetsMap = generateFeatureCollection(
    streetGroups, "Streets", "BrBG", "highway")

streetsMap.add_to(map)

# colormap = cm.get_cmap(name="BrBG", lut=len(streetGroups))
# streetColors = {key: colormap(i) for i, key in enumerate(streetGroups.keys())}

file = open("out/buildings_{}.json".format(areaName), encoding='UTF-8')
all_buildings = json.load(file)
buildingGroups = groupBy(all_buildings, ["building"])

buildingsMap = generateFeatureCollection(
    buildingGroups, "Buildings", "coolwarm", "building")

buildingsMap.add_to(map)


file = open("out/landuse_{}.json".format(areaName), encoding='UTF-8')
all_landuse = json.load(file)
landUseGroups = groupBy(all_landuse, ["landuse"])

landUseMap = generateFeatureCollection(
    landUseGroups, "LandUse", "hsv", "landuse")

landUseMap.add_to(map)
folium.LayerControl().add_to(map)

fileName = "out/map_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))