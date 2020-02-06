from collections import defaultdict
from shapely.strtree import STRtree
import geojson
from shapely.geometry import Point, mapping
import networkx as nx
import logging

from helper.coordSystemHelper import distance, wgsToUtm

from helper.coordSystemHelper import wgsToUtm, utmToWgs


def getCrossRoads(streets):
    # TODO: remove ending streets and continuing streets for final version
    invertedStreetIndex = defaultdict(lambda: {
        "streetNames": set(),
        "streetTypes": set(),
        "edgeCount": 0,
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


""" def groupNearbyCrossPoints(crossPoints):
    for location, properties in crossPoints.items():
        Point(location)
    
    rTree = STRtree() """
