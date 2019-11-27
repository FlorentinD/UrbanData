import json
import folium
from matplotlib import cm
from geoJsonHelper import groupBy
from foliumHelper import geoFeatureCollectionToFoliumFeatureGroup
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl
from OsmObjectType import OsmObjectType as OsmObject
from overpassHelper import OverPassHelper
from OsmDataQuery import OsmDataQuery

# TODO: groupby on either amenity or building? (overlapping) (layers based on multiple tags not on single tag)
# TODO: layers Safety, Health, Leisure, Commercial (shops, craft, building manaufture, ...), Religion,

# postfix for f.i. file_names
areaName = "pieschen"
# area to query
pieschen = Nominatim().query('Pieschen, Dresden, Germany')

pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[pieschenCoord["lat"], pieschenCoord["lon"]], tiles='Stamen Toner', zoom_start=15)

# matplotlib colormap names
colormaps = ["hsv", "BrBG", "coolwarm"]

#yellowPages
file = open("out/data/scraper/yellowPages_Dresden_Pieschen.json", encoding='UTF-8')
yellowCompanies = json.load(file)

yellowFeature = geoFeatureCollectionToFoliumFeatureGroup(yellowCompanies, "pink", "yellowPages", switchLatAndLong = False)
yellowFeature.add_to(map)


# handels register
file2 = open("out/data/scraper/handelsregister_Dresden_Pieschen.json", encoding='UTF-8')
handelsRegisterCompanies = json.load(file2)

registerFeature = geoFeatureCollectionToFoliumFeatureGroup(handelsRegisterCompanies, "blue", "handelsRegister", switchLatAndLong = False)
registerFeature.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/scrapedCompaniesMap_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
