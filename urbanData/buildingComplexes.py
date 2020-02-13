from collections import defaultdict
import matplotlib.pyplot as plt
import logging
import json
import geojson
import folium
import networkx as nx
from funcy import log_durations


from shapely.geometry import Polygon, LineString, mapping, shape
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from OSMPythonTools.nominatim import Nominatim

from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup
from helper.geoJsonConverter import shapeGeomToGeoJson
from helper.geoJsonHelper import unionFeatureCollections
from helper.coordSystemHelper import transformWgsToUtm as withUTMCoord

from annotater.osmAnnotater import AddressAnnotator, OsmCompaniesAnnotator, AmentiyAnnotator, LeisureAnnotator, EducationAggregator, SafetyAggregator
from annotater.companyAnnotator import CompanyAnnotator
from annotater.buildingClassifier import BuildingTypeClassifier
from annotater.buildingLvlAnnotator import BuildingLvlAnnotator

# TODO: also use "flurstuecke" from openDataDresden ?

# TODO: take all buildings for regions and per region count number of living apartment, companies, ... (for showing percentage)
# cannot use geopandas as pandas does not support list and dictonary as datatypes


# TODO: function to map region id based for an object (based on address or just geometry)
# tag order to analyse: public, leisure, amenity, buldings, landuse, office ? ... check if company?

@log_durations(logging.info)
def buildGroups(buildings):
    """groups buildings together, with at least one common point returns a geo-json featurecollections
        buildings: geojson featureCollection
    """
    objectGraph = nx.Graph()
    allBuildingsShapeGeom = [shape(building["geometry"]) for building in buildings["features"]]
    for id, buildingShape in enumerate(allBuildingsShapeGeom):
        buildingShape.id = id
        objectGraph.add_node(id)

    buildingIndex = STRtree(allBuildingsShapeGeom)

    for buildingShape in allBuildingsShapeGeom:
        nearBuildings = buildingIndex.query(buildingShape)
        for otherBuildingShape in nearBuildings: 
            if buildingShape.touches(otherBuildingShape):
                objectGraph.add_edge(buildingShape.id, otherBuildingShape.id)
   
    buildingComponents = nx.connected_components(objectGraph)

    # building geojson features
    buildingGroups = []
    for id, indexes in enumerate(buildingComponents):
        buildingGeometries = [allBuildingsShapeGeom[index] for index in indexes]
        groupShape = unary_union(buildingGeometries)
        buildingIds = list(indexes)

        buildingGroup = shapeGeomToGeoJson(groupShape, properties={
            "groupId": id, 
            "__buildings": buildingIds
        })
        buildingGroups.append(buildingGroup)

        for bId in buildingIds:
            buildings["features"][bId]["properties"]["groupId"] = id

    logging.info("BuildingGroups: {}".format(len(buildingGroups)))

    return geojson.FeatureCollection(buildingGroups)

def buildRegions(buildingGroups, borders):
    """buildingGroup expansion (if no borders inbetween -> union)"""

    buildingGroupGeoShapes = list(enumerate([withUTMCoord(shape(building["geometry"])) for building in buildingGroups["features"]]))

    # borders between building-groups ! also need to be in UTM !
    bordersShapelyLines = [withUTMCoord(shape(street["geometry"])) for street in borders["features"]] 

    buildingGroupGraph = nx.Graph()
    # init graph 
    for index, _ in buildingGroupGeoShapes:
        buildingGroupGraph.add_node(index, borders = set())

    #visualize_edges = True
    #if visualize_edges:
    #    edges = folium.FeatureGroup("edges between home-groups")

    added_edges = 0
    for index, bShape in buildingGroupGeoShapes:
        if((index + 1) % 50 == 0 and not index == 0):
            logging.info("Progress: {}/{} ; {} edges added".format(index + 1, len(buildingGroupGeoShapes), added_edges))
            added_edges = 0
    
        for otherIndex, otherBShape in buildingGroupGeoShapes[index+1:]:
            # TODO: Performance ? use shapely STRTree for querying this (need to set index attr in geometry for this! https://github.com/Toblerity/Shapely/issues/618)
            # more than 120 meters inbetween -> very likely something in between
            MAX_GROUP_DISTANCE = 120
            distance = bShape.distance(otherBShape)
            if distance < MAX_GROUP_DISTANCE:
                center = bShape.centroid.coords[0]
                otherCenter = otherBShape.centroid.coords[0]
                connection = LineString(coordinates=[center, otherCenter])

                crossesStreet = -1
                for streetIndex, street in enumerate(bordersShapelyLines):
                    if street.crosses(connection):
                        crossesStreet = streetIndex
                        break

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
        # remove duplicate street names (as streets often secmented by crossings)
        regionBorders = list(set(regionBorders))
        groupIds = [group["properties"]["groupId"] for group in groupsForRegion]

        region = shapeGeomToGeoJson(regionShape, properties={
            "regionId": id, 
            "__buildingGroups": groupIds, 
            "regionBorders": regionBorders
        })
        buildingRegions.append(region)

        for group in groupsForRegion:
            group["properties"]["regionId"] = id 

    logging.info("Building Regions: {}".format(len(buildingRegions)))
    return geojson.FeatureCollection(buildingRegions)

def buildGroupsAndRegions(buildings, borders):
    groups = buildGroups(buildings)
    regions = buildRegions(groups, borders)
    return (groups, regions)

def getPolygonArea(building):
    """transforms coordinates to utm and returns area in m²"""
    buildingWithUTM = withUTMCoord(building)
    return round(buildingWithUTM.area)

def annotateArea(buildings, groups, regions):
    """based on number of levels of buildings"""
    BUILDINGAREA_KEY = "buildingArea"
    # TODO: rewrite as annotater
    logging.info("Starting area annotation")
    for building in buildings["features"]:
        buildingLevels = building["properties"].get("levels")
        groundArea = getPolygonArea(shape(building["geometry"]))
        building["properties"][BUILDINGAREA_KEY] = {"ground in m2": groundArea}
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
        building["properties"][BUILDINGAREA_KEY]["total in m2"] = buildingLevels *  groundArea
    
    for group in groups["features"]:
        group["properties"][BUILDINGAREA_KEY] = {
            "ground in m2": sum(
                [buildings["features"][buildingId]["properties"][BUILDINGAREA_KEY]["ground in m2"] for buildingId in group["properties"]["__buildings"]]),
            "total in m2": sum(
                [buildings["features"][buildingId]["properties"][BUILDINGAREA_KEY]["total in m2"] for buildingId in group["properties"]["__buildings"]]),

            "companyCount": sum([entries for type, entries in group["properties"]["companies"].items()]),
            "leisureCount": sum([entries for type, entries in group["properties"]["leisures"].items()]),
            "amenityCount": sum([entries for type, entries in group["properties"]["amenities"].items()]),
            "educationCount": sum([entries for type, entries in group["properties"].get("education", {}).items()]),
            "safetyCount": sum([entries for type, entries in group["properties"].get("safety", {}).items()])
        }
    
    # very alike to above loop
    for region in regions["features"]:
        region["properties"][BUILDINGAREA_KEY] = {
            "ground in m2": sum(
                [groups["features"][groupId]["properties"][BUILDINGAREA_KEY]["ground in m2"] for groupId in region["properties"]["__buildingGroups"]]),
            "total in m2": sum(
                [groups["features"][groupId]["properties"][BUILDINGAREA_KEY]["total in m2"] for groupId in region["properties"]["__buildingGroups"]]),
            
            "companyCount": sum([entries for type, entries in region["properties"]["companies"].items()]),
            "leisureCount": sum([entries for type, entries in region["properties"]["leisures"].items()]),
            "amenityCount": sum([entries for type, entries in region["properties"]["amenities"].items()]),
            "educationCount": sum([entries for type, entries in region["properties"]["education"].items()]),
            "safetyCount": sum([entries for type, entries in region["properties"]["safety"].items()])
        }
    return (buildings, groups, regions)


logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    areaOfInterest = 'Pieschen, Dresden, Germany'

    pieschen = Nominatim().query(areaOfInterest)
    allBuildingsQuery = OsmDataQuery("homes", OsmObjectType.WAY, ['"building"', 'abandoned!~"yes"'])
    osmQueries = [ allBuildingsQuery,
            OsmDataQuery("borders", OsmObjectType.WAY,  
            ['highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|motorway|unclassified"']),
            OsmDataQuery("borders_railway", OsmObjectType.WAY, ["'railway'~'rail'"])]

    # https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#By_polygon_.28poly.29 for filtering based on polygon (if borough based on openDataDresden)
    osmData = OverPassHelper().directFetch(pieschen.areaId(), osmQueries)

    buildings = next(osmData)
    borders = unionFeatureCollections(*list(osmData))

    alreadyBuiltRegions = False
    if not alreadyBuiltRegions:

        # Poor Mans Testing
        #buildings = geojson.FeatureCollection(buildings["features"][:200])

        logging.info("Fetched {} buildings".format(len(buildings["features"])))
        groups, regions = buildGroupsAndRegions(buildings, borders)
    else:
        logging.info("Loading buildings, groups and regions")
        # TODO: index seems to be messed up when loading?
        with open("out/data/buildings_pieschen.json", encoding='UTF-8') as file:
            buildings = json.load(file)
        with open("out/data/buildingGroups_pieschen.json", encoding='UTF-8') as file:
            groups = json.load(file)
        with open("out/data/buildingRegions_pieschen.json", encoding='UTF-8') as file:
            regions = json.load(file)

    
    # TODO: boroughs (including parks, forest, allointments and sport centers?)
  

    # TODO: buildings with yes often lay inside f.i. hospital (amenity = hospital | healthcare = hospital) or landuse = police
    
    # TODO: clarify dependencies between them
    annotater = [AddressAnnotator(areaOfInterest), BuildingLvlAnnotator(), CompanyAnnotator(),
                 BuildingTypeClassifier(), OsmCompaniesAnnotator(
                     areaOfInterest, OsmObjectType.WAYANDNODE),
                 LeisureAnnotator(areaOfInterest, OsmObjectType.WAYANDNODE), AmentiyAnnotator(areaOfInterest, OsmObjectType.WAYANDNODE), 
                 SafetyAggregator(), EducationAggregator()]

    for annotator in annotater:
        logging.info("Starting {}".format(annotator.__class__.__name__))
        buildings = annotator.annotateAll(buildings)
        groups = annotator.aggregateToGroups(buildings, groups)
        regions = annotator.aggregateToRegions(groups, regions)
    
    annotateArea(buildings, groups, regions)

    logging.info("save complexes and regions")

    with open("out/data/buildings_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(buildings, outfile)
    with open("out/data/buildingGroups_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(groups, outfile)
    with open("out/data/buildingRegions_pieschen.json", 'w', encoding='UTF-8') as outfile:
            geojson.dump(regions, outfile)


    ######### Visual 
    areaName = "pieschen"
    pieschen = Nominatim().query(areaOfInterest)
    pieschenCoord = pieschen.toJSON()[0]
    map = folium.Map(
        location=[51.078875, 13.728524], tiles='Open Street Map', zoom_start=15)

    geoFeatureCollectionToFoliumFeatureGroup(buildings, "black", name="Single buildings").add_to(map)

    bordersFeature = geoFeatureCollectionToFoliumFeatureGroup(borders, "red", "borders")
    bordersFeature.add_to(map)

    buildingGroupsFeature = geoFeatureCollectionToFoliumFeatureGroup(groups, "blue", "building groups")
    buildingGroupsFeature.add_to(map)

    buildingRegionsFeature = geoFeatureCollectionToFoliumFeatureGroup(regions, "green", "building regions")
    buildingRegionsFeature.add_to(map)

    folium.LayerControl().add_to(map)

    fileName = "out/maps/buildingComplexes_{}.html".format(areaName)
    map.save(fileName)
    logging.info("Map saved in {}".format(fileName))
