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
from localizer import Localizer


# find building complexes by union geometry of buildings with >1 common point
# use unary_union from shapely.ops to merge complexes to one

# TODO: also use "flurstuecke" from openDataDresden ?

# TODO: take all buildings for regions and per region count number of living apartment, companies, ... (for showing percentage)
# TODO: add properties to regions (f.i. addresses ! nearly always stored inside nodes, not in the building)

def getCoordinates(building):
    """extracts coordinates from a geojson object"""
    if "geometry" in building:
        return building["geometry"]["coordinates"]
    else:
        raise ValueError(building + " has no geometry")


homesSelector = ['building~"apartments|terrace|house"', 'abandoned!~"yes"']
homesQuery = OsmDataQuery("homes", OsmObjectType.WAY, ['building~"apartments|terrace|house"', 'abandoned!~"yes"'])

addressSelector = ['addr:housenumber','addr:street', '!building']

pieschen = Nominatim().query('Pieschen, Dresden, Germany')
osmQueries = [ homesQuery,
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"']),
            OsmDataQuery("borders_railway", OsmObjectType.WAY, ["'railway'~'rail'"])]

osmData = OverPassHelper().directFetch(pieschen.areaId(), "pieschen", osmQueries)

allHomes = next(osmData)
localizer = Localizer('Pieschen, Dresden, Germany')
# TODO check if not already annotaded file exists 
[localizer.annotateWithAddresses(home) for home in allHomes["features"]]

print("Annoted buildings with addresses")

allApartmentsCoordinates = list(enumerate([getCoordinates(apartment) for apartment in allHomes["features"]]))
objectGraph = nx.Graph()

# TODO: only do this if specified (only useful if area contains many blocks)
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
for indexes in apartmentComponents:
    apartments = [Polygon(allApartmentsCoordinates[index][1]) for index in indexes]
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
edges = folium.FeatureGroup("edges between home-groups")

for index, center1 in apartmentGroupCenters:
    if(index % 50 == 0):
        print("Progress: {}/{} ; {} edges added".format(index + 1, len(apartmentGroupCenters), added_edges))
        added_edges = 0
    aparmentGroupGraph.add_node(index)
    
    for otherIndex, center2 in apartmentGroupCenters[index+1:]:
        # more than 80 meters inbetween -> very likely something in between
        if distance(center1, center2).meters < 120:
            connection = LineString(coordinates=[center1, center2])
            crossesStreet = True in [street.crosses(
                connection) for street in bordersShapelyLines]
            # TODO: only do this if f.i. visualize checked connections flag is set
            folium.vector_layers.PolyLine([(center1[1], center1[0]), (center2[1], center2[0])]).add_to(edges)
            if not crossesStreet:
                added_edges += 1
                aparmentGroupGraph.add_edge(index, otherIndex)

groupExpansionComponents = nx.connected_components(aparmentGroupGraph)

apartmentRegions = []
for component in groupExpansionComponents:
    apartmentGroupsForRegion = [apartmentGroups[index] for index in component]
    apartmentGroupForRegionGeometries = [geom for (indexes, geom) in apartmentGroupsForRegion] 
    apartmentRegion = unary_union(apartmentGroupForRegionGeometries).convex_hull
    homeIndexesForRegion = []
    [homeIndexesForRegion.extend(indexes) for (indexes, geom) in apartmentGroupsForRegion]
    apartmentRegions.append((homeIndexesForRegion, apartmentRegion))

print("ApartmentRegions: {}".format(len(apartmentRegions)))

# TODO: refactor into extra function

geoJsonApartmentGroups = []
for (indexes, shape) in apartmentGroups:
    # TODO: properly analyse properties (propably only addresses and names, buildinglvls?)
    streets = [allHomes[index]["properties"].get("addresses", None) for index in indexes]
    feature = shapeGeomToGeoJson(shape, properties={"streets": streets})
    geoJsonApartmentGroups.append(feature)
geoJsonApartmentGroups = geojson.FeatureCollection(geoJsonApartmentGroups)

geoJsonApartmentRegions = []
for (indexes, shape) in apartmentRegions:
    # TODO: properly analyse properties (propably only addresses and names?)
    streets = [allHomes[index]["properties"].get("addresses", None) for index in indexes]
    feature = shapeGeomToGeoJson(shape, properties={"streets": streets})
    geoJsonApartmentRegions.append(feature)
geoJsonApartmentRegions = geojson.FeatureCollection(geoJsonApartmentRegions)


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

edges.add_to(map)

geoFeatureCollectionToFoliumFeatureGroup(allHomes, "black", name="Single apartments").add_to(map)

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
