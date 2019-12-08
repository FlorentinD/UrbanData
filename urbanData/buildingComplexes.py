from collections import defaultdict
import matplotlib.pyplot as plt
import json
import geojson
import folium
import networkx as nx
from shapely.geometry import Polygon, LineString, mapping, shape
from shapely.ops import unary_union
from geopy.distance import distance
from OSMPythonTools.nominatim import Nominatim

import sys
sys.path.insert(0, './helper')
from overPassHelper import OverPassHelper
from OsmDataQuery import OsmDataQuery
from OsmObjectType import OsmObjectType
from geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup
from geoJsonConverter import shapeGeomToGeoJson
from geoJsonHelper import unionFeatureCollections

from localizer import Localizer

# TODO: also use "flurstuecke" from openDataDresden ?

# TODO: take all buildings for regions and per region count number of living apartment, companies, ... (for showing percentage)
# TODO: Use geopandas ? or look for other ways to increase performance

def analyseProperties(properties):
    # ! annotate each bulding with region id and then map afterwards again ... (takes to long in one run -> harder to test)
    # TODO: function to map region id based for an object (based on address or just geometry)
    # tag order to analyse: public, leisure, amenity, buldings, landuse, office ? ... check if company?
    # apartments -> use building:levels and roof:levels for levels (assume 3-4 ?)
    #   https://wiki.openstreetmap.org/wiki/Key:building:levels
    # house : assume one level ? (if none given)
    # terrace: sequence of houses -> count addresses contained (implicit number of entrances) (assume 1 lvl per house?)
    """analyses properties of building in a building group"""
    # can be used later to aggregate towards regions
    return 0

def unionAddresses(dics):
    union = defaultdict(list)
    for dic in dics:
        for key, value in dic.items():
            if not value == Localizer.DEFAULT_HOUSENUMBER:
                union[key].extend(value)
    return dict(union)

homesSelector = ['building~"apartments|terrace|house"', 'abandoned!~"yes"']
homesQuery = OsmDataQuery("homes", OsmObjectType.WAY, homesSelector)


# later in group look for homes -> living area ; companies -> company area ; abandoned -> unused area?; .... 
allBuildingsQuery = OsmDataQuery("homes", OsmObjectType.WAY, ['"building"', 'abandoned!~"yes"'])

pieschen = Nominatim().query('Pieschen, Dresden, Germany')
osmQueries = [ homesQuery,
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"']),
            OsmDataQuery("borders_railway", OsmObjectType.WAY, ["'railway'~'rail'"])]

osmData = OverPassHelper().directFetch(pieschen.areaId(), osmQueries)

allHomes = next(osmData)

# Poor Mans Testing
# allHomes = geojson.FeatureCollection(allHomes["features"][:50])

localizer = Localizer('Pieschen, Dresden, Germany')
# TODO check if not already annotaded file exists 
[localizer.annotateWithAddresses(home) for home in allHomes["features"]]

print("Annotated {} buildings with addresses".format(len(allHomes["features"])))

allApartmentsShapeGeom = list(enumerate([shape(apartment["geometry"]) for apartment in allHomes["features"]]))
objectGraph = nx.Graph()

# TODO: only do this if specified (only useful if area contains many blocks)
for index, shape1 in allApartmentsShapeGeom:
    objectGraph.add_node(index)
    # as intersection is symmetric looking at elements after current one is enough
    for otherIndex, shape2 in allApartmentsShapeGeom[index+1:]: 
        if shape1.touches(shape2):
            objectGraph.add_edge(index, otherIndex)
   
apartmentComponents = nx.connected_components(objectGraph)

apartmentGroups = []
for indexes in apartmentComponents:
    # [1] as first one is index created by enumerate
    # TODO: also save buildingIds (extra class BuildingComplex)
    apartments = [allApartmentsShapeGeom[index][1] for index in indexes]
    # also save indexes to fetch && aggregate properties at the end 
    apartmentComplex = (list(indexes), unary_union(apartments))
    apartmentGroups.append(apartmentComplex)

print("ApartmentGroups: {}".format(len(apartmentGroups)))

########## ApartmentGroups expansion (if no borders inbetween -> union)

# borders between building-complexes
borders = unionFeatureCollections(*list(osmData))
bordersShapelyLines = [shape(street["geometry"]) for street in borders["features"]] 

aparmentGroupGraph = nx.Graph()
apartmentGroupCenters = list(enumerate([group.centroid.coords[0] for _, group in apartmentGroups]))

added_edges = 0
visualize_edges = True
if visualize_edges:
    edges = folium.FeatureGroup("edges between home-groups")

for index, center1 in apartmentGroupCenters:
    if(index % 50 == 0):
        print("Progress: {}/{} ; {} edges added".format(index + 1, len(apartmentGroupCenters), added_edges))
        added_edges = 0
    aparmentGroupGraph.add_node(index)
    
    for otherIndex, center2 in apartmentGroupCenters[index+1:]:
        # TODO: Performance ? use shapely STRTree for querying this (need to set index attr in geometry for this! https://github.com/Toblerity/Shapely/issues/618)
        # more than 120 meters inbetween -> very likely something in between
        if distance(center1, center2).meters < 120:
            connection = LineString(coordinates=[center1, center2])
            crossesStreet = True in [street.crosses(
                connection) for street in bordersShapelyLines]
            if visualize_edges:
                folium.vector_layers.PolyLine([(center1[1], center1[0]), (center2[1], center2[0])]).add_to(edges)
            if not crossesStreet:
                added_edges += 1
                aparmentGroupGraph.add_edge(index, otherIndex)

groupExpansionComponents = nx.connected_components(aparmentGroupGraph)

apartmentRegions = []
for indexes in groupExpansionComponents:
    # TODO: save as extra class BuildingRegion
    apartmentGroupsForRegion = [apartmentGroups[index] for index in indexes]
    apartmentGroupForRegionGeometries = [geom for (indexes, geom) in apartmentGroupsForRegion] 
    apartmentRegion = unary_union(apartmentGroupForRegionGeometries).convex_hull
    # TODO: find streets crossing this regions (for refining geometry)
    apartmentRegions.append((list(indexes), apartmentRegion))

print("ApartmentRegions: {}".format(len(apartmentRegions)))

# TODO: refactor into extra function

geoJsonApartmentGroups = []
for (indexes, shape) in apartmentGroups:
    # TODO: also add buildingIds
    addressDics = [allHomes["features"][index]["properties"].get("addresses", None) for index in indexes]
    addresses = unionAddresses(addressDics)
    feature = shapeGeomToGeoJson(shape, properties={"addresses": addresses})
    geoJsonApartmentGroups.append(feature)
geoJsonApartmentGroups = geojson.FeatureCollection(geoJsonApartmentGroups)

geoJsonApartmentRegions = []
for (indexes, shape) in apartmentRegions:
    # TODO: also add apartmentComplexids?
    addressDics = [geoJsonApartmentGroups["features"][index]["properties"].get("addresses", None) for index in indexes]
    addresses = unionAddresses(addressDics)
    feature = shapeGeomToGeoJson(shape, properties={"addresses": addresses})
    geoJsonApartmentRegions.append(feature)
geoJsonApartmentRegions = geojson.FeatureCollection(geoJsonApartmentRegions)


print("save complexes and regions")

with open("out/data/apartmentGroups_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(geoJsonApartmentGroups, outfile)

with open("out/data/apartmentRegions_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(geoJsonApartmentRegions, outfile)

######### Visual 

areaName = "pieschen"
pieschen = Nominatim().query('Pieschen, Dresden, Germany')
pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[51.088534,13.723315], tiles='Open Street Map', zoom_start=15)

if visualize_edges:
    edges.add_to(map)

geoFeatureCollectionToFoliumFeatureGroup(allHomes, "black", name="Single apartments").add_to(map)

bordersFeature = geoFeatureCollectionToFoliumFeatureGroup(borders, "red", "borders")
bordersFeature.add_to(map)

buildingGroupsFeature = geoFeatureCollectionToFoliumFeatureGroup(geoJsonApartmentGroups, "blue", "apartment groups")
buildingGroupsFeature.add_to(map)

buildingRegionsFeature = geoFeatureCollectionToFoliumFeatureGroup(geoJsonApartmentRegions, "green", "apartment regions")
buildingRegionsFeature.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/maps/buildingComplexes_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
