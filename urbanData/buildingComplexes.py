from collections import defaultdict
import matplotlib.pyplot as plt
import logging
import json
import geojson
import folium
import networkx as nx

import pyproj
from shapely.geometry import Polygon, LineString, mapping, shape
from shapely.ops import unary_union, transform
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

BUILDINGAREA_KEY = "buildingArea in m²"

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

        buildingGroup = shapeGeomToGeoJson(groupShape, properties={
            "groupId": id, 
            "__buildings": buildingIds, 
            BUILDINGAREA_KEY: {"ground": sum([getPolygonArea(geom) for geom in buildingGeometries])} })
        buildingGroups.append(buildingGroup)

        for bId in buildingIds:
            buildings["features"][bId]["properties"]["groupId"] = id 
            buildings["features"][bId]["properties"][BUILDINGAREA_KEY] = {"ground": getPolygonArea(allBuildingsShapeGeom[bId][1])}

    logger.info("BuildingGroups: {}".format(len(buildingGroups)))

    return geojson.FeatureCollection(buildingGroups)

def getPolygonArea(building):
    """transforms coordinates to utm and returns area in m²"""
    # TODO: derive Zone from coordinates (center)
    project = pyproj.Proj(proj='utm', zone=33, ellps='WGS84', preserve_units = False)
    buildingWithUTM = transform(project, building)
    return round(buildingWithUTM.area)


def buildRegions(buildingGroups, borders):
    """buildingGroup expansion (if no borders inbetween -> union)"""

    # TODO: if group is To large ... use multiple points ?!
    # center coordinates for each buildingGroup
    buildingGroupCenters = list(enumerate([shape(building["geometry"]).centroid.coords[0] for building in buildingGroups["features"]]))
    # borders between building-groups
    bordersShapelyLines = [shape(street["geometry"]) for street in borders["features"]] 

    buildingGroupGraph = nx.Graph()
    # init graph 
    for index, _ in buildingGroupCenters:
        buildingGroupGraph.add_node(index, borders = set())

    #visualize_edges = True
    #if visualize_edges:
    #    edges = folium.FeatureGroup("edges between home-groups")

    added_edges = 0

    for index, center1 in buildingGroupCenters:
        if((index + 1) % 50 == 0 and not index == 0):
            print("Progress: {}/{} ; {} edges added".format(index + 1, len(buildingGroupCenters), added_edges))
            added_edges = 0
    
        for otherIndex, center2 in buildingGroupCenters[index+1:]:
            # TODO: Performance ? use shapely STRTree for querying this (need to set index attr in geometry for this! https://github.com/Toblerity/Shapely/issues/618)
            # more than 120 meters inbetween -> very likely something in between
            if distance(center1, center2).meters < 120:
                connection = LineString(coordinates=[center1, center2])
    
                crossesStreet = -1
                for streetIndex, street in enumerate(bordersShapelyLines):
                    if street.crosses(connection):
                        crossesStreet = streetIndex
                        break
                
                #if VISUALIZE_EDGES:
                #    folium.vector_layers.PolyLine([(center1[1], center1[0]), (center2[1], center2[0])]).add_to(edges)
                if crossesStreet == -1:
                    added_edges += 1
                    buildingGroupGraph.add_edge(index, otherIndex)
                else:
                    buildingGroupGraph.node[index]['borders'].add(crossesStreet)
                    buildingGroupGraph.node[otherIndex]['borders'].add(crossesStreet)

    regionComponents = nx.connected_components(buildingGroupGraph)

    buildingRegions = []
    for id, indexes in enumerate(regionComponents):
        groupsForRegion = [buildingGroups["features"][index] for index in indexes]
        groupForRegionGeometries = [shape(group["geometry"]) for group in groupsForRegion] 
        # TODO: use saved streets for this regions (for refining geometry) (find method for refinement)
        regionShape = unary_union(groupForRegionGeometries).convex_hull

        borderIndexes = set.union(*[buildingGroupGraph.node[index]['borders'] for index in indexes])
        regionBorders = [borders["features"][index]["properties"].get("name", "border{}".format(index)) for index in borderIndexes]
        groupIds = [group["properties"]["groupId"] for group in groupsForRegion]

        region = shapeGeomToGeoJson(regionShape, properties={
            "regionId": id, 
            "__buildingGroups": groupIds, 
            "regionBorders": regionBorders,
            BUILDINGAREA_KEY: {"ground": sum([getPolygonArea(geom) for geom in groupForRegionGeometries])}})
        buildingRegions.append(region)

        for group in groupsForRegion:
            group["properties"]["regionId"] = id 

    logger.info("ApartmentRegions: {}".format(len(buildingRegions)))
    return geojson.FeatureCollection(buildingRegions)

def buildGroupsAndRegions(buildings, borders):
    groups = buildGroups(buildings)
    regions = buildRegions(groups, borders)
    return (groups, regions)

def annotateTotalArea(buildings, groups, regions):
    """based on number of levels and ground area of buildings"""
    # TODO: rewrite as annotater
    logger.info("Computing total area of buildings")
    for building in buildings["features"]:
        buildingLevels = building["properties"].get("levels")
        groundArea = building["properties"][BUILDINGAREA_KEY]["ground"]
        if not buildingLevels:
            groupId = building["properties"]["groupId"]
            avgGroupLevel = groups["features"][groupId]["properties"]["levels"]
            buildingLevels = round(avgGroupLevel)
            if not avgGroupLevel:
                regionId = groups["features"][groupId]["properties"]["regionId"]
                avgRegionLevel = regions["features"][regionId]["properties"]["levels"]
                buildingLevels = round(avgRegionLevel)
                if not avgRegionLevel:
                    # could be finally borough avg maybe
                    buildingLevels = 1
            building["properties"]["estimatedLevels"] = buildingLevels
        building["properties"][BUILDINGAREA_KEY]["total"] = buildingLevels *  groundArea
    
    for group in groups["features"]:
        group["properties"][BUILDINGAREA_KEY]["ground"] = sum(
            [buildings["features"][buildingId]["properties"][BUILDINGAREA_KEY]["ground"] for buildingId in group["properties"]["__buildings"]])
        group["properties"][BUILDINGAREA_KEY]["total"] = sum(
            [buildings["features"][buildingId]["properties"][BUILDINGAREA_KEY]["total"] for buildingId in group["properties"]["__buildings"]])
    
    for region in regions["features"]:
        region["properties"][BUILDINGAREA_KEY]["ground"] = sum(
            [groups["features"][groupId]["properties"][BUILDINGAREA_KEY]["ground"] for groupId in region["properties"]["__buildingGroups"]])
        region["properties"][BUILDINGAREA_KEY]["total"] = sum(
            [groups["features"][groupId]["properties"][BUILDINGAREA_KEY]["total"] for groupId in region["properties"]["__buildingGroups"]])
    return (buildings, groups, regions)



logger = logging.getLogger('')
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    allBuildingsQuery = OsmDataQuery("homes", OsmObjectType.WAY, ['"building"', 'abandoned!~"yes"'])

    pieschen = Nominatim().query('Pieschen, Dresden, Germany')
    osmQueries = [ allBuildingsQuery,
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"']),
            OsmDataQuery("borders_railway", OsmObjectType.WAY, ["'railway'~'rail'"])]

    # https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#By_polygon_.28poly.29 for filtering based on polygon (if borough based on openDataDresden)
    osmData = OverPassHelper().directFetch(pieschen.areaId(), osmQueries)

    buildings = next(osmData)
    borders = unionFeatureCollections(*list(osmData))

    logger.info("Loaded {} buildings".format(len(buildings["features"])))
    # Poor Mans Testing
    buildings = geojson.FeatureCollection(buildings["features"][:200])

    alreadyBuiltRegions = False
    if not alreadyBuiltRegions:
        groups, regions = buildGroupsAndRegions(buildings, borders)
    else:
        logger.info("Loading groups and regions")
        with open("out/data/buildingGroups_pieschen.json", encoding='UTF-8') as file:
            groups = json.load(file)
        with open("out/data/buildingRegions_pieschen.json", encoding='UTF-8') as file:
            regions = json.load(file)

    # TODO: boroughs (including parks, forest, allointments and sport centers?)
  

    # TODO: buildings with yes often lay inside f.i. hospital (amenity = hospital | healthcare = hospital) or landuse = police
    annotater = [AddressAnnotator('Pieschen, Dresden, Germany'), BuildingLvlAnnotator(), CompanyAnnotator(), BuildingTypeClassifier()]
    
    logger.info("Annotating buldings, groups and regions".format(len(buildings["features"])))
    for annotator in annotater:
        buildings = annotator.annotateAll(buildings)
        groups = annotator.aggregateToGroups(buildings, groups)
        regions = annotator.aggregateToRegions(groups, regions)
    
    annotateTotalArea(buildings, groups, regions)

    logger.info("save complexes and regions")

    with open("out/data/buildingGroups_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(groups, outfile)
    with open("out/data/buildingRegions_pieschen.json", 'w', encoding='UTF-8') as outfile:
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
