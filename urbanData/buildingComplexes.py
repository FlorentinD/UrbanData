from collections import defaultdict
import matplotlib.pyplot as plt
import logging
import json
import geojson
import folium
import networkx as nx
from shapely.geometry import Polygon, LineString, mapping, shape
from shapely.ops import unary_union
from geopy.distance import distance
from OSMPythonTools.nominatim import Nominatim

from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup
from helper.geoJsonConverter import shapeGeomToGeoJson
from helper.geoJsonHelper import unionFeatureCollections

from annotater.osmAnnotater import AddressAnnotator, BuildingLvlAnnotator, BuildingTypeClassifier
from annotater.companyAnnotator import CompanyAnnotator

# TODO: also use "flurstuecke" from openDataDresden ?

# TODO: take all buildings for regions and per region count number of living apartment, companies, ... (for showing percentage)
# cannot use geopandas as pandas does not support list and dictonary datatypes)


# TODO: function to map region id based for an object (based on address or just geometry)
# tag order to analyse: public, leisure, amenity, buldings, landuse, office ? ... check if company?
# house : assume one level ? (if none given)
# terrace: sequence of houses -> count addresses contained (implicit number of entrances) (assume 1 lvl per house?)

def buildGroups(buildings):
    """groups buildings together, with at least one common point returns a geo-json featurecollections
        buildings: geojson featureCollection
        """

    allBuildingsShapeGeom = list(enumerate([shape(building["geometry"]) for building in buildings["features"]]))
    objectGraph = nx.Graph()
    for index, shape1 in allBuildingsShapeGeom:
        objectGraph.add_node(index)
        # as touches is symmetric looking at elements after current one is enough
        for otherIndex, shape2 in allBuildingsShapeGeom[index+1:]: 
            if shape1.touches(shape2):
                objectGraph.add_edge(index, otherIndex)
   
    buildingComponents = nx.connected_components(objectGraph)

    # building geojson features
    buildingGroups = []
    for id, indexes in enumerate(buildingComponents):
        buildingGeometries = [allBuildingsShapeGeom[index][1] for index in indexes]
        groupShape = unary_union(buildingGeometries)
        buildingIds = list(indexes)

        buildingGroup = shapeGeomToGeoJson(groupShape, properties={"groupId": id, "buildings": buildingIds })
        buildingGroups.append(buildingGroup)

    logger.info("BuildingGroups: {}".format(len(buildingGroups)))

    return geojson.FeatureCollection(buildingGroups)


def buildRegions(buildingGroups, borders):
    """buildingGroup expansion (if no borders inbetween -> union)"""

    # center coordinates for each buildingGroup
    # TODO: if group is To large ... use multiple points ?!
    buildingGroupCenters = list(enumerate([shape(building["geometry"]).centroid.coords[0] for building in buildingGroups["features"]]))
    # borders between building-groups
    bordersShapelyLines = [shape(street["geometry"]) for street in borders["features"]] 

    buildingGroupGraph = nx.Graph()
    #visualize_edges = True
    #if visualize_edges:
    #    edges = folium.FeatureGroup("edges between home-groups")

    added_edges = 0

    for index, center1 in buildingGroupCenters:
        if(index % 50 == 0):
            print("Progress: {}/{} ; {} edges added".format(index + 1, len(buildingGroupCenters), added_edges))
            added_edges = 0
        buildingGroupGraph.add_node(index)
    
        for otherIndex, center2 in buildingGroupCenters[index+1:]:
            # TODO: Performance ? use shapely STRTree for querying this (need to set index attr in geometry for this! https://github.com/Toblerity/Shapely/issues/618)
            # more than 120 meters inbetween -> very likely something in between
            if distance(center1, center2).meters < 120:
                connection = LineString(coordinates=[center1, center2])
                crossesStreet = True in [street.crosses(connection) for street in bordersShapelyLines]
                #if VISUALIZE_EDGES:
                #    folium.vector_layers.PolyLine([(center1[1], center1[0]), (center2[1], center2[0])]).add_to(edges)
                if not crossesStreet:
                    added_edges += 1
                    buildingGroupGraph.add_edge(index, otherIndex)
                else:
                    "filler"
                    #buildingGroupGraph.node[index].get('borders', {}).add()
                    #buildingGroupGraph.node[otherIndex].get('borders', {}).add()
                    #TODO: street as border of group (then propagate to region)
                    # TODO: save as node property via buildingGroupGraph.node[index]['borders'] 

    regionComponents = nx.connected_components(buildingGroupGraph)

    buildingRegions = []
    for id, indexes in enumerate(regionComponents):
        groupsForRegion = [buildingGroups["features"][index] for index in indexes]
        groupForRegionGeometries = [shape(group["geometry"]) for group in groupsForRegion] 
        # TODO: use saved streets for this regions (for refining geometry) (find method for refinement)
        regionShape = unary_union(groupForRegionGeometries).convex_hull
        groupIds = [group["properties"]["groupId"] for group in groupsForRegion]

        region = shapeGeomToGeoJson(regionShape, properties={"regionId": id, "buildingGroups": groupIds})
        buildingRegions.append(region)

    logger.info("ApartmentRegions: {}".format(len(buildingRegions)))
    return geojson.FeatureCollection(buildingRegions)


logger = logging.getLogger('')
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    #homesSelector = ['building~"apartments|terrace|house"', 'abandoned!~"yes"']
    #homesQuery = OsmDataQuery("homes", OsmObjectType.WAY, homesSelector)


    allBuildingsQuery = OsmDataQuery("homes", OsmObjectType.WAY, ['"building"', 'abandoned!~"yes"'])

    pieschen = Nominatim().query('Pieschen, Dresden, Germany')
    osmQueries = [ allBuildingsQuery,
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"']),
            OsmDataQuery("borders_railway", OsmObjectType.WAY, ["'railway'~'rail'"])]

    # https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#By_polygon_.28poly.29 for filtering based on polygon (if borough based on openDataDresden)
    osmData = OverPassHelper().directFetch(pieschen.areaId(), osmQueries)

    buildings = next(osmData)

    logger.info("Loaded {} buildings".format(len(buildings["features"])))
    # Poor Mans Testing
    buildings = geojson.FeatureCollection(buildings["features"][:200])

    annotater = [AddressAnnotator('Pieschen, Dresden, Germany'), BuildingLvlAnnotator(), CompanyAnnotator(), BuildingTypeClassifier()]

    for annotator in annotater:
        buildings = annotator.annotateAll(buildings)

    logger.info("Annotated {} buildings".format(len(buildings["features"])))

    groups = buildGroups(buildings)
    # Todo: to this for all annotater
    groups = AddressAnnotator.aggregateToGroup(buildings, groups)

    borders = unionFeatureCollections(*list(osmData))

    # TODO: add landuse ways to regions (could be also seperate regions) f.i. police, forest, grass
    #           allointments (kleingaerten) 
    #           leisure like sports_centre, park
    regions = buildRegions(groups, borders)
    # TODO: do this for all annotater
    regions = AddressAnnotator.aggregateToRegions(groups, regions)

    # TODO: probably calls aggregate on all Annotaters (building -> group) and aggregate (group -> region)
    logger.info("save complexes and regions")

    with open("out/data/apartmentGroups_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(groups, outfile)
    with open("out/data/apartmentRegions_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(regions, outfile)


    ######### Visual 
    areaName = "pieschen"
    pieschen = Nominatim().query('Pieschen, Dresden, Germany')
    pieschenCoord = pieschen.toJSON()[0]
    map = folium.Map(
        location=[51.088534,13.723315], tiles='Open Street Map', zoom_start=15)

    #if VISUALIZE_EDGES:
    #    edges.add_to(map)

    geoFeatureCollectionToFoliumFeatureGroup(buildings, "black", name="Single apartments").add_to(map)

    bordersFeature = geoFeatureCollectionToFoliumFeatureGroup(borders, "red", "borders")
    bordersFeature.add_to(map)

    buildingGroupsFeature = geoFeatureCollectionToFoliumFeatureGroup(groups, "blue", "apartment groups")
    buildingGroupsFeature.add_to(map)

    buildingRegionsFeature = geoFeatureCollectionToFoliumFeatureGroup(regions, "green", "apartment regions")
    buildingRegionsFeature.add_to(map)

    folium.LayerControl().add_to(map)

    fileName = "out/maps/buildingComplexes_{}.html".format(areaName)
    map.save(fileName)
    logger.info("Map saved in {}".format(fileName))
