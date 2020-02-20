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
    Groups roundAbout crossRoads by a fixed radius currently.
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

            # points are crosspoints but not exactly the end of the street segment (only sometimes)
            # continuing and endingStreets to circumvent this problem
            # 3 meter distance is arbitrary and hopefully works for most of the cases
            pointInUtm = wgsToUtm(*point)
            if pointInUtm == startPoint or pointInUtm == endPoint or distance(pointInUtm, startPoint) < 3 or distance(pointInUtm, endPoint) < 3:
                streetNodeIndex[point].endingStreets += [name]
            else:
                streetNodeIndex[point].continuingStreets += [name]
    
    roundabouts = [street for street in streets if street["properties"].get("junction") == "roundabout"]
    crossRoads = regardRoundabouts(streetNodeIndex, roundabouts)

    for _, properties in crossRoads.items():
        properties.computeEdgeCount()
    
     # filter crossRoads for real ones (just changing street-names or a road splitting into 2 lanes does not count)
    normalCrossRoads = {c: props for c, props in crossRoads.items() if props.junctionType == JunctionType.NORMAL and not (props.edgeCount > 2 or props.streetTypes == {"service"})}

    roundAboutCrossRoads = {c: props for c, props in crossRoads.items(
    ) if props.junctionType == JunctionType.ROUNDABOUT}

    normalCrossRoads = groupNearbyCrossRoads(normalCrossRoads, groupingRadius)
   
    normalCrossRoads = {point: properties for point, properties in normalCrossRoads.items() if not len(properties.streetNames) == 1}

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
        properties.computeEdgeCount()
        result[roundAboutCenter] = properties
            
    # as this mutates the input
    return result

def groupNearbyCrossRoads(crossRoads, radius):
    """ 
    using UTM coords for metric distance 
    and also setting the edgeCount for every CrossRoad
    """

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

        for oldProp in nearbyCrossRoads.values():
            newProperties.union(oldProp)
        newProperties.computeEdgeCount()
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
    # to get how many where grouped
    osmCrossRoads: int = 1

    def asdict(self):
        return {k:v
                for k,v in self.__dict__.items() if not k in ["endingStreets", "continuingStreets", "osmCrossRoads"] or logging.getLogger().level == logging.DEBUG}
    
    def union(self, properties):
        """union all except junction type and edgeCount"""
        if not isinstance(properties, CrossRoadProperties):
            raise ValueError("expected a CrossRoadProperties object but was {}".format(type(properties)))
        self.streetNames.update(properties.streetNames)
        self.streetTypes.update(properties.streetTypes)
        self.endingStreets += properties.endingStreets
        self.continuingStreets += properties.continuingStreets
        self.osmCrossRoads += properties.osmCrossRoads

        if properties.junctionType == JunctionType.ROUNDABOUT:
            self.junctionType = JunctionType.ROUNDABOUT

        return None

    def computeEdgeCount(self):
        """computing the edgeCount based on the continuing and ending streets"""
        streets = set(self.endingStreets + self.continuingStreets)
        if self.junctionType == JunctionType.ROUNDABOUT:
            streets = [s for s in self.endingStreets if not s.startswith("osm-id:")]
        edgeCount = 0
        for street in streets:
            # TODO: how to detect some exotic crossRoads which only have one street?
            # each street can be at maximum 2 times an edge of a crossRoad
            countInEndingStreets = len([s for s in self.endingStreets if s == street])

            # for roundabouts only count ending streets (streets inside the roundabout do not count)
            if self.junctionType == JunctionType.ROUNDABOUT:
                continuingStreets = []
            else:
                continuingStreets = self.continuingStreets
            
            countInEndingStreets = len([s for s in self.endingStreets if s == street])

            if street in continuingStreets or countInEndingStreets > 1:
                edgeCount += 2
            else:
                edgeCount += 1
        
        self.edgeCount = edgeCount

        return None
