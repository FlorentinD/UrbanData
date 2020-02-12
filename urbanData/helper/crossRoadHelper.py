from collections import defaultdict
from dataclasses import dataclass, field

from shapely.strtree import STRtree
from shapely.geometry import shape, mapping, Point as sPoint, MultiPoint as sMultiPoint
import networkx as nx
import geojson
import logging

from helper.coordSystemHelper import distance, wgsToUtm, utmToWgs
from helper.geoJsonHelper import lineToPolygon


def getCrossRoads(streets):
    """
    
    excludes crossRoads only between service roads and ones with only one street name
    """
    streetNodeIndex = defaultdict(lambda: CrossRoadProperties())
    streets = streets["features"]
    
    for street in streets:
        name = street["properties"].get(
            "name", "osm-id: {}".format(street["id"]))
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
                    if not (properties.edgeCount <= 2 or properties.streetTypes == {"service"})}
    
    roundabouts = [street for street in streets if street["properties"].get("junction") == "roundabout"]
    crossRoadsWithRoundAbouts = regardRoundabouts(crossRoads, roundabouts)

    unionedCrossRoads = groupNearbyCrossRoads(crossRoadsWithRoundAbouts)

    geoJsonFeatures = []
    for location, properties in unionedCrossRoads.items():
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
        properties = CrossRoadProperties(junctionType="round-about")
        for point in street["geometry"]["coordinates"]:
            point = tuple(point)
            otherProperties = result.pop(point, None)
            if otherProperties:
                properties.union(otherProperties)
                properties.edgeCount += otherProperties.edgeCount
                # TODO: update edgeCount?
        if not properties.edgeCount == 0:
            result[roundAboutCenter] = properties
            
    # as this mutates the input
    return result

def groupNearbyCrossRoads(crossRoads):
    # using UTM coords for 20m (?) distance
    # TODO: higher radius and then combine with streetName based approach at component lvl
    # TODO: radius dependent on streetType (higher radius for round-abouts)
    crossRoadRadius = 10.0
    shapelyPoints = []
    graph = nx.Graph()

    # TODO: combine with streetName based approach maybe? (bigger junctions not working properly)

    for location, properties in crossRoads.items():
        point = sPoint(wgsToUtm(*location))
        point.id = location
        graph.add_node(location)
        shapelyPoints.append(point)
    
    index = STRtree(shapelyPoints)

    for point in shapelyPoints:
        radius = point.buffer(crossRoadRadius)
        crossRoadPoints = [p for p in index.query(radius) if not p == point] 
        for otherPoint in crossRoadPoints:
            graph.add_edge(otherPoint.id, point.id)

    result = crossRoads.copy()

    components = [component for component in nx.connected_components(graph) if not len(component) == 1]
    for nodes in components:
        closeCrossRoads = [location for location in nodes]
        center = tuple(sMultiPoint(list(closeCrossRoads)).centroid.coords[0])
        properties = CrossRoadProperties()
        junctionTypes = set()
        for location in closeCrossRoads:
            # TODO: do not union different crossRoad Types!
            # TODO: fix round about edge Count
            otherProperties = result.pop(location)
            properties.union(otherProperties)
            
            junctionTypes.add(otherProperties.junctionType)
            # approximate edgeCount
            properties.edgeCount = max(properties.edgeCount, otherProperties.edgeCount)
        
        properties.edgeCount = max(properties.edgeCount, len(properties.streetNames))
        if "round-about" in junctionTypes:
            properties.junctionType = "round-about"
        result[center] = properties
    return result

@dataclass
class CrossRoadProperties:
    streetNames: dict = field(default_factory=set)
    streetTypes: dict = field(default_factory=set)
    edgeCount: int = 0
    junctionType: str = "normal"
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
