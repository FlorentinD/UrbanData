import matplotlib.pyplot as plt
import json
import geojson
import folium
from shapely.geometry import Polygon, LineString, mapping, shape
from shapely.ops import unary_union
from geopy.distance import distance
import networkx as nx
from OSMPythonTools.nominatim import Nominatim
from overpassHelper import OverPassHelper
from OsmDataQuery import OsmDataQuery
from OsmObjectType import OsmObjectType
from foliumHelper import geoFeatureCollectionToFoliumFeatureGroup
from geoJsonHelper import shapeGeomToGeoJson, unionFeatureCollections


# find building complexes by union geometry of buildings with >1 common point
# use unary_union from shapely.ops to merge complexes to one

def getCoordinates(building):
    if "geometry" in building:
        return building["geometry"]["coordinates"]
    else:
        raise ValueError(building + " has no geometry")

# TODO: add "railway" to borders
pieschen = Nominatim().query('Pieschen, Dresden, Germany')
osmQueries = [OsmDataQuery("homes", OsmObjectType.WAY, ['building~"apartments|terrace|house"', 'abandoned!~"yes"']),
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"']),
            OsmDataQuery("borders_railway", OsmObjectType.WAY, ["'railway'~'rail'"])]

osmData = OverPassHelper().directFetch(pieschen.areaId(), "pieschen", osmQueries)

allApartments = next(osmData)

allApartmentsCoordinates = list(enumerate([getCoordinates(apartment) for apartment in allApartments["features"]]))
objectGraph = nx.Graph()

for index, ap1Coord in allApartmentsCoordinates:
    objectGraph.add_node(index)
    # as intersection is symmetric looking at elements after current one is enough
    for otherIndex, ap2Coord in allApartmentsCoordinates[index+1:]: 
        # set & intersection would mess up ordering of points
        # TODO: allow distance < 2 meters?
        if [point for point in ap1Coord if point in ap2Coord]:
            objectGraph.add_edge(index, otherIndex)
   
apartmentComponents = nx.connected_components(objectGraph)

apartmentGroups = []
for component in apartmentComponents:
    apartments = [Polygon(allApartmentsCoordinates[index][1]) for index in component]
    apartmentComplex = unary_union(apartments)
    # TODO: aggregate Properties? (fetchable via index) (f.i. address:Street, plz)
    apartmentGroups.append(apartmentComplex)

print("ApartmentGroups: {}".format(len(apartmentGroups)))

########## ApartmentGroups expansion (if no borders inbetween -> union)

# borders between building-complexes
borders = unionFeatureCollections(*list(osmData))
bordersShapelyLines = [shape(street["geometry"]) for street in borders["features"]] 

aparmentGroupGraph = nx.Graph()
apartmentGroupCenters = list(enumerate([group.centroid for group in apartmentGroups]))

added_edges = 0

for index, center1 in apartmentGroupCenters:
    if(index % 50 == 0):
        print("Progress: {}/{} ; {} edges added".format(index +
                                                        1, len(apartmentGroupCenters), added_edges))
        added_edges = 0
    aparmentGroupGraph.add_node(index)
    
    for otherIndex, center2 in apartmentGroupCenters[index+1:]:
        # more than 50 meters inbetween -> very likely something in between
        if distance(center1.coords[0], center2.coords[0]).meters < 80:
            connection = LineString(coordinates=[center1, center2])
            crossesStreet = True in [street.crosses(
                connection) for street in bordersShapelyLines]
            if not crossesStreet:
                added_edges += 1
                aparmentGroupGraph.add_edge(index, otherIndex)

groupExpansionComponents = nx.connected_components(aparmentGroupGraph)

apartmentRegions = []
for component in groupExpansionComponents:
    apartmentGroupsForRegion = [apartmentGroups[index] for index in component if index < len(apartmentGroups)]
    errors = [index for index in component if index >= len(apartmentGroups)]
    if errors:
        print("wrong indexes {}".format(errors))
    apartmentRegion = unary_union(apartmentGroupsForRegion).convex_hull
    # TODO: aggregate Properties? (fetchable via index) (f.i. address:Street, plz)
    apartmentRegions.append(apartmentRegion)

print("ApartmentRegions: {}".format(len(apartmentRegions)))

geoJsonApartmentGroups = shapeGeomToGeoJson(apartmentGroups)
geoJsonApartmentRegions = shapeGeomToGeoJson(apartmentRegions)

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

geoFeatureCollectionToFoliumFeatureGroup(allApartments, "black", name="Single apartments").add_to(map)

bordersFeature = geoFeatureCollectionToFoliumFeatureGroup(borders, "red", "borders")
bordersFeature.add_to(map)

buildingGroupsFeature = geoFeatureCollectionToFoliumFeatureGroup(geoJsonApartmentGroups, "blue", "apartment groups")
buildingGroupsFeature.add_to(map)

buildingRegionsFeature = geoFeatureCollectionToFoliumFeatureGroup(geoJsonApartmentRegions, "green", "apartment regions")
buildingRegionsFeature.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/buildingComplexes_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
