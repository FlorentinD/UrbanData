from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from shapely.strtree import STRtree
from shapely.geometry import shape, mapping, Point as sPoint, MultiPoint as sMultiPoint
import networkx as nx
import geojson
import logging

from helper.coordSystemHelper import distance, wgsToUtm, utmToWgs
from helper.geoJsonHelper import lineToPolygon


def getCrossRoads(streets, groupingRadius = 15):
    """  
    Excludes crossRoads between service roads and ones with only one street name.
    Groups nearby crossRoads given by groupingRadius.
    """
    streetNodeIndex = defaultdict(lambda: CrossRoadProperties())
    streets = streets["features"]
    
    for street in streets:
        name = street["properties"].get(
            "name", 
            street["properties"].get(
                "ref", 
                "osm-id: {}".format(street["id"])
                )
            )
        streetType = street["properties"].get("highway")
        geomType = street["geometry"]["type"]
        if not geomType == "LineString":
            # as https://www.openstreetmap.org/way/309830643 would lead to falsely huge crossRoads
            logging.debug(
                "Skipped {} as it is not a way but a {}".format(name, geomType))
            continue

        points = street["geometry"]["coordinates"]
        startPoint = wgsToUtm(*points[0])
        endPoint = wgsToUtm(*points[-1])

        for point in points:
            point = tuple(point)
            streetNodeIndex[point].streetNames.add(name)
            streetNodeIndex[point].streetTypes.add(streetType)

            # TODO: crossRoad edge count still not correct every time (https://www.openstreetmap.org/node/3866701865)
            # 2x same street (name wise) from one direction but extra streets as both one-way
            # could use tag: oneway=yes

            # points are crosspoints but not exactly the end of the street segment ...
            # 3 meter distance is arbitrary and hopefully works for most of the cases
            pointInUtm = wgsToUtm(*point)
            if pointInUtm == startPoint or pointInUtm == endPoint or distance(pointInUtm, startPoint) < 3 or distance(pointInUtm, endPoint) < 3:
                streetNodeIndex[point].edgeCount += 1
                streetNodeIndex[point].endingStreets += [name]
            else:
                # as street continues after this point, thus two edges for this crossRoad
                streetNodeIndex[point].edgeCount += 2
                streetNodeIndex[point].continuingStreets += [name]
    crossRoads = {point: properties for point, properties in streetNodeIndex.items() 
                    if not (properties.edgeCount <= 2 or properties.streetTypes == {"service"} or len(properties.streetNames) == 1)}
    
    roundabouts = [street for street in streets if street["properties"].get("junction") == "roundabout"]
    crossRoads = regardRoundabouts(crossRoads, roundabouts)

    normalCrossRoads = {c: prop for c, prop in crossRoads.items() if not prop.junctionType == JunctionType.ROUNDABOUT}
    roundAboutCrossRoads = {c: prop for c, prop in crossRoads.items() if prop.junctionType == JunctionType.ROUNDABOUT}

    normalCrossRoads = groupNearbyCrossRoads(normalCrossRoads, groupingRadius)
    # as roundAbouts can have quite a large radius
    roundAboutCrossRoads = groupNearbyCrossRoads(roundAboutCrossRoads, 30) 

    return crossRoadsToFeatures(normalCrossRoads), crossRoadsToFeatures(roundAboutCrossRoads)

def crossRoadsToFeatures(crossRoads):
    geoJsonFeatures = []
    for location, properties in crossRoads.items():
        geoJsonFeatures.append(geojson.Feature(
            geometry=geojson.Point(coordinates=location),
            properties=properties.asdict()
        ))
    return geojson.FeatureCollection(geoJsonFeatures)

def regardRoundabouts(crossRoads, roundAboutStreets):
    """removes crossRoads in round abouts and add one crossRoad per roundabout street"""
    result = crossRoads.copy()

    for street in roundAboutStreets:
        roundAboutCenter = tuple(shape(street["geometry"]).centroid.coords[0])
        assert(not roundAboutCenter in result.keys())
        properties = CrossRoadProperties(junctionType=JunctionType.ROUNDABOUT)
        for point in street["geometry"]["coordinates"]:
            point = tuple(point)
            otherProperties = result.pop(point, None)
            if otherProperties:
                properties.union(otherProperties)
                properties.edgeCount += otherProperties.edgeCount
        result[roundAboutCenter] = properties
            
    # as this mutates the input
    return result

def groupNearbyCrossRoads(crossRoads, radius):
    """ using UTM coords for metric distance """

    # TODO: combine with streetName based approach maybe? (bigger junctions not working properly)
    #       higher radius and then combine with streetName based approach at component lvl ?

    shapelyPoints = []
    graph = nx.Graph()

    for location, newProperties in crossRoads.items():
        point = sPoint(wgsToUtm(*location))
        point.id = location
        graph.add_node(location)
        shapelyPoints.append(point)
    
    index = STRtree(shapelyPoints)

    for point in shapelyPoints:
        searchArea = point.buffer(radius)
        crossRoadPoints = [p for p in index.query(searchArea) if not p == point] 
        for otherPoint in crossRoadPoints:
            graph.add_edge(otherPoint.id, point.id)

    result = crossRoads.copy()

    components = [component for component in nx.connected_components(graph) if not len(component) == 1]
    for crossRoadLocations in components:
        nearbyCrossRoads = {loc: result.pop(loc) for loc in crossRoadLocations}

        center = tuple(sMultiPoint(list(crossRoadLocations)).centroid.coords[0])
        newProperties = CrossRoadProperties()
        junctionTypes = set([props.junctionType for props in nearbyCrossRoads.values()])
        for oldProp in nearbyCrossRoads.values():
            # TODO: do not union different crossRoad Types!
            # TODO: fix round about edge Count (+ edgeCount - common streets)
            # edgeCount -> roundabout (+ 1 for each crossRoad if edgeCount > 2)
            # using continuing streets
            newProperties.union(oldProp)
            commonStreets = len(oldProp.streetNames.intersection(newProperties.streetNames))
            if JunctionType.ROUNDABOUT in junctionTypes:
                # ensure to only include exit-point of round-about
                if oldProp.edgeCount > 2:
                    # each crossRoad is an exit of the whole round about
                    newProperties.edgeCount += 1
            else:
                # approximate edgeCount, can lead to overestimations (street segments between crossRoad points of a bigger junction)
                newProperties.edgeCount = newProperties.edgeCount + oldProp.edgeCount - commonStreets
        if not JunctionType.ROUNDABOUT in junctionTypes:
            if newProperties.edgeCount <= 2:
                newProperties.edgeCount = len([name for name in newProperties.streetNames if not name.startswith("osm-id:")]) * 2
            else:
                newProperties.edgeCount = min(newProperties.edgeCount, len(newProperties.streetNames) * 2)
        else:
            newProperties.junctionType = JunctionType.ROUNDABOUT
        result[center] = newProperties
    return result


class JunctionType(Enum):
    ROUNDABOUT = "roundabout"
    NORMAL = "normal"


@dataclass
class CrossRoadProperties:
    streetNames: dict = field(default_factory=set)
    streetTypes: dict = field(default_factory=set)
    edgeCount: int = 0
    junctionType: JunctionType = JunctionType.NORMAL
    # for debugging purpose
    endingStreets: list =  field(default_factory=list)
    continuingStreets: list =  field(default_factory=list)

    def asdict(self):
        return {k:v
                for k,v in self.__dict__.items() if not k in ["endingStreets", "continuingStreets"]}
    
    def union(self, properties):
        if not isinstance(properties, CrossRoadProperties):
            raise ValueError("expected a CrossRoadProperties object but was {}".format(type(properties)))
        self.streetNames.update(properties.streetNames)
        self.streetTypes.update(properties.streetTypes)

        return None