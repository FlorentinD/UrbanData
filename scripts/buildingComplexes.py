import matplotlib.pyplot as plt
import json
import geojson
import folium
from shapely.geometry import Polygon, LineString, mapping
from shapely.ops import unary_union
from geopy.distance import distance
import networkx as nx
from OSMPythonTools.nominatim import Nominatim
from overpassHelper import OverPassHelper
from OsmDataQuery import OsmDataQuery
from OsmObjectType import OsmObjectType


# find building complexes by union geometry of buildings with >1 common point
# use unary_union from shapely.ops to merge complexes to one

def overlap(b1, b2) -> bool:
    """ find out if 2 buildings overlap """


def getCoordinates(building):
    if "geometry" in building:
        return building["geometry"]["coordinates"]
    else:
        raise ValueError(building + " has no geometry")


pieschen = Nominatim().query('Pieschen, Dresden, Germany')
osmQuery = [OsmDataQuery("homes", OsmObjectType.WAY, [
                         'building~"apartments|terrace|house"', 'abandoned!~"yes"'])]
osmResolvedDataQueries = OverPassHelper().fetch(
    pieschen.areaId(), "pieschen", osmQuery)

resolvedQuery = osmResolvedDataQueries[0]
file = open(resolvedQuery.filePath, encoding='UTF-8')
allApartments = json.load(file)

allApartmentsCoordinates = list(enumerate([getCoordinates(apartment) for apartment in allApartments["features"]]))
objectGraph = nx.Graph()

for index, ap1Coord in allApartmentsCoordinates:
        # check if one of these point already in the apartmentGroups
        # else start new group
        # at the end need to try merging these groups (transitive) (if sets are not disjoint)
        # finally use unary_union for one object per group

    objectGraph.add_node(index)
    
    for otherIndex, ap2Coord in allApartmentsCoordinates[index+1:]: 
        # set & intersection would mess up ordering of points
        if [point for point in ap1Coord if point in ap2Coord]:
            objectGraph.add_edge(index, otherIndex)
   
print("Building Intersections: {}".format(len(objectGraph.edges)))

apartmentComponents = nx.connected_components(objectGraph)
"test"

apartmentGroups = []
for component in apartmentComponents:
    apartments = [Polygon(allApartmentsCoordinates[index][1]) for index in component]
    apartmentComplex = unary_union(apartments)
    apartmentGroups.append(apartmentComplex)



areaName = "pieschen"
pieschen = Nominatim().query('Pieschen, Dresden, Germany')
pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[51.088534,13.723315], tiles='Open Street Map', zoom_start=15)

buildingComplexFeature = folium.FeatureGroup(name="apartment Complexes")
for group in apartmentGroups:
    allLines = mapping(group)
    points = []
    if allLines["type"] in ['MultiLineString', "Polygon"]:
        for lines in allLines["coordinates"]:
            for lon, lat in lines:
                # !! switch lat and lon for correct representation
                points.append((lat, lon))
    # elif allLines["type"] == 'LineString':
    #     for lon, lat in allLines["coordinates"]:
    #         points.append((lat, lon))
    elif allLines["type"] == "MultiPolygon":
        for polygon in allLines["coordinates"]:
            for i in polygon:
                for lon, lat in i:
                    points.append((lat, lon))
    else:
        raise ValueError("Expected unexpected shaply geometry: {}".format(allLines["type"]))
    folium.vector_layers.Polygon(points, color="red", fill_color="red").add_to(buildingComplexFeature)


folium.GeoJson(allApartments, name="Single apartments", show=True).add_to(map)
buildingComplexFeature.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/buildingComplexes_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))