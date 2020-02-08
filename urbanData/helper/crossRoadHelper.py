from collections import defaultdict
from dataclasses import dataclass, field

from shapely.strtree import STRtree
from shapely.geometry import shape, mapping, Point as sPoint
import networkx as nx
import geojson
import logging

from helper.coordSystemHelper import distance, wgsToUtm, utmToWgs
from helper.geoJsonHelper import lineToPolygon


def getCrossRoads(streets):
    # TODO: introduce dataclass and use own asdict
    # using x: list = field(default_factory=list)
    invertedStreetIndex = defaultdict(lambda: {
        "streetNames": set(),
        "streetTypes": set(),
        "edgeCount": 0,
        "junctionType": "normal",
        # for debugging
        "ending streets": [],
        "continuing streets": []
    })
    for street in streets["features"]:
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
        Point(startPoint).distance
        for point in points:
            point = tuple(point)
            invertedStreetIndex[point]["streetNames"].add(name)
            invertedStreetIndex[point]["streetTypes"].add(streetType)

            # TODO: crossRoad edge count still not correct every time (https://www.openstreetmap.org/node/3866701865)
            # 2x same street (name wise) from one direction but extra streets as both one-way
            # could use tag: oneway=yes

            # points are crosspoints but not exactly the end of the street segment ...
            # 3 meter distance is arbitrary and hopefully works for most of the cases
            pointInUtm = wgsToUtm(*point)
            if pointInUtm == startPoint or pointInUtm == endPoint or distance(pointInUtm, startPoint) < 3 or distance(pointInUtm, endPoint) < 3:
                invertedStreetIndex[point]["edgeCount"] += 1
                invertedStreetIndex[point]["ending streets"] += [name]
            else:
                # as street continues after this point, thus two edges for this crossRoad
                invertedStreetIndex[point]["edgeCount"] += 2
                invertedStreetIndex[point]["continuing streets"] += [name]
    crossRoads = {point: properties for point, properties in invertedStreetIndex.items() 
                    if properties["edgeCount"] > 2 and not properties["streetTypes"] == {"service"}}

    geoJsonFeatures = []
    for location, properties in crossRoads.items():
        geoJsonFeatures.append(geojson.Feature(
            geometry=geojson.Point(coordinates=location),
            properties=properties
        ))
    return geojson.FeatureCollection(geoJsonFeatures)

# TODO: include into above function
def regardRoundabouts(crossRoads, roundaboutStreets):
    """removes crossRoads in round abouts and add one crossRoad per roundabout"""
    for street in roundaboutStreets:
        roundAboutCenter = tuple(shape(street["geometry"]).centroid.coords[0])
        assert(not roundAboutCenter in crossRoads.keys())
        crossRoads[roundAboutCenter]["junctionType"] = "round-about"
        for point in street["geometry"]["coordinates"]:
            point = tuple(point)
            crossPoint = crossRoads.pop(point)
            crossRoads[roundAboutCenter]["streetNames"].update(crossPoint["streetNames"])
            crossRoads[roundAboutCenter]["streetTypes"].update(crossPoint["streetTypes"])
            
    # TODO: test this function
    return crossRoads

# TODO: unify crossPoints with distance > 2m ?
def groupNearbyCrossRoads(crossRoads):
    # using UTM coords for 2m distance
    crossRoadRadius = 2.0
    shapelyPoints = []
    graph = nx.Graph()

    for location, properties in crossRoads.items():
        point = sPoint(wgsToUtm(*location))
        graph.add_node(point, properties = properties)
        shapelyPoints.append(point)
    
    index = STRtree(shapelyPoints)

    for point in shapelyPoints:
        radius = point.buffer(crossRoadRadius)
        crossRoadPoints = index.query(radius)
        for otherPoint in crossRoadPoints:
            graph.add_edge(otherPoint, point)

    components = nx.connected_components(graph)
    for nodes in components:
        logging.debug(nodes)
        # TODO: unify crossRoadPoints as Polygon? 
        # TODO: convert back into WGS
    result = []
    return result

@dataclass
class CrossRoad:
    streetNames: dict = field(default_factory=set)
    streetTypes: dict = field(default_factory=set)
    edgeCount: int = 0
    junctionType: str = "normal"
    # for debugging purpose
    # TODO: write own asdict method that leaves asside 
    endingStreets: list =  field(default_factory=list)
    continuingStreets: list =  field(default_factory=list)

    def asdict(self):
        return {k:v
                for k,v in self.__dict__.items() if not k in ["endingStreets", "continuingStreets"]}
