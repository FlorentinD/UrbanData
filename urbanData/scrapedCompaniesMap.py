import json
from matplotlib import cm
import folium
from folium.plugins.measure_control import MeasureControl
from OSMPythonTools.nominatim import Nominatim

import sys
sys.path.insert(0, './helper')
from geoJsonHelper import groupBy, unionFeatureCollections
from geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup
from OsmObjectType import OsmObjectType as OsmObject
from overPassHelper import OverPassHelper
from OsmDataQuery import OsmDataQuery

# TODO: groupby on either amenity or building? (overlapping) (layers based on multiple tags not on single tag)
# TODO: layers Safety, Health, Leisure, Commercial (shops, craft, building manaufture, ...), Religion,

# postfix for f.i. file_names
areaName = "pieschen"
# area to query
pieschen = Nominatim().query('Pieschen, Dresden, Germany')

pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[pieschenCoord["lat"], pieschenCoord["lon"]], tiles='Open Street Map', zoom_start=15)

#yellowPages
file = open("out/data/scraper/yellowPages_Dresden_Pieschen.json", encoding='UTF-8')
yellowCompanies = json.load(file)

yellowFeature = geoFeatureCollectionToFoliumFeatureGroup(yellowCompanies, "yellow", "yellowPages", switchLatAndLong = False)
yellowFeature.add_to(map)


# handels register
file = open("out/data/scraper/handelsregister_Dresden_Pieschen.json", encoding='UTF-8')
handelsRegisterCompanies = json.load(file)

registerFeature = geoFeatureCollectionToFoliumFeatureGroup(handelsRegisterCompanies, "blue", "handelsRegister", switchLatAndLong = False)
registerFeature.add_to(map)


# osm companies: often specify a name ? (tourism for holiday apartments f.i. , ... see data to collect)
namedAmenitiesThings = OsmDataQuery("osm_named_amenities", OsmObject.WAYANDNODE, ["name", "amenity",'"amenity"!~"vending_machine|parking"'], "")
namedLeisureThings = OsmDataQuery("osm_named_leisure", OsmObject.WAYANDNODE, ["name", "leisure", 'amenity!~"."'], "")
namedShopsThings = OsmDataQuery("osm_named_shops", OsmObject.WAYANDNODE, ["name", "shop", 'amenity!~"."', 'leisure!~"."'], "")
namedCraftThings = OsmDataQuery("osm_named_crafts", OsmObject.WAYANDNODE, ["name", "craft", 'amenity!~"."','leisure!~"."', 'shop!~"."'], "")
namedCompaniesThings = OsmDataQuery("osm_named_companies", OsmObject.WAYANDNODE, ["name", "company", 'amenity!~"."','leisure!~"."', 'shop!~"."','craft!~"."'], "")
osmQueries = [namedAmenitiesThings, namedCompaniesThings, namedCraftThings, namedCompaniesThings, namedShopsThings]
osmData = OverPassHelper().directFetch(areaId=pieschen.areaId(), osmQueries=osmQueries)

unionData = unionFeatureCollections(*osmData)

osmFeature = geoFeatureCollectionToFoliumFeatureGroup(unionData, "pink", "Named amenities/leisure/shops/craft/companies in osm", switchLatAndLong = True)
osmFeature.add_to(map)

# buildingRegions
file = open("out/data/apartmentRegions_pieschen.json", encoding='UTF-8')
handelsRegisterCompanies = json.load(file)

registerFeature = geoFeatureCollectionToFoliumFeatureGroup(handelsRegisterCompanies, "green", "ApartmentRegions", switchLatAndLong = True)
registerFeature.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/scrapedCompaniesMap_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
