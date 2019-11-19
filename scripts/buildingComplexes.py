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
from foliumHelper import generateFeatureCollection
from jsonToGeoJSON import shapeGeomToGeoJson


# find building complexes by union geometry of buildings with >1 common point
# use unary_union from shapely.ops to merge complexes to one

def getCoordinates(building):
    if "geometry" in building:
        return building["geometry"]["coordinates"]
    else:
        raise ValueError(building + " has no geometry")


pieschen = Nominatim().query('Pieschen, Dresden, Germany')
osmQuery = [OsmDataQuery("homes", OsmObjectType.WAY, ['building~"apartments|terrace|house"', 'abandoned!~"yes"']),
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"'])]

osmResolvedDataQueries = OverPassHelper().fetch(pieschen.areaId(), "pieschen", osmQuery)

resolvedQuery = osmResolvedDataQueries[0]
file = open(resolvedQuery.filePath, encoding='UTF-8')
allApartments = json.load(file)

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
resolvedQuery = osmResolvedDataQueries[1]
file = open(resolvedQuery.filePath, encoding='UTF-8')
bordersGeoJson = json.load(file)
bordersShapelyLines = [shape(street["geometry"]) for street in bordersGeoJson["features"]] 

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

######### Visual 

geoJsonApartmentGroups = shapeGeomToGeoJson(apartmentGroups)
geoJsonApartmentRegions = shapeGeomToGeoJson(apartmentRegions)

areaName = "pieschen"
pieschen = Nominatim().query('Pieschen, Dresden, Germany')
pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[51.088534,13.723315], tiles='Open Street Map', zoom_start=15)

buildingGroupsFeature = generateFeatureCollection({"filler" : geoJsonApartmentGroups}, "BrBG", "apartment groups")
buildingGroupsFeature.add_to(map)

buildingRegionsFeature = generateFeatureCollection({"filler" : geoJsonApartmentRegions}, "hsv", "apartment regions")
buildingRegionsFeature.add_to(map)

folium.GeoJson(allApartments, name="Single apartments", show=True).add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/buildingComplexes_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
