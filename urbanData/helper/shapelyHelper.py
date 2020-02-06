from shapely.strtree import STRtree
from shapely.geometry import shape as shapeFunc
from helper.geoJsonConverter import shapeGeomToGeoJson
from helper.geoJsonHelper import groupBy
import geojson
import logging

def intersections(geoJsonFeatureCollection, idProperty = "name"):
    """
        calculates every intersection of the geometries ...
    """
    features = geoJsonFeatureCollection["features"]
    shapeMapping = { id: shapeFunc(feature["geometry"]) for id, feature in enumerate(features)}

    # add id attribute to shapes (for later reference when retrieved from index)
    for id, currentShape in shapeMapping.items():
        currentShape.ids = set([id])

    newIntersectionsFound = True
    shapes = shapeMapping.values()

    foundIntersections = set()
    result = list(shapes)

    while newIntersectionsFound:
        index = STRtree(shapes)
        newShapes = []
        for currentShape in shapes:
            foundShapes = index.query(currentShape)
            # removes false positive from STRtree retrieval
            intersectionShapes= [s for s in foundShapes if s.overlaps(currentShape) and not s == currentShape]
            for otherShape in intersectionShapes:
                unionedIds = currentShape.ids.union(otherShape.ids)
                intersectionKey = tuple(sorted(list(unionedIds)))
                if intersectionKey in foundIntersections:
                     # skipping intersection is not order specific, therefore intersection can be skipped
                    continue
                else:
                    foundIntersections.add(intersectionKey)

                newShape = currentShape.intersection(otherShape)
                if newShape.geometryType() == "Polygon":
                    newShape.ids = unionedIds
                    newShapes.append(newShape)
                elif newShape.geometryType() == 'GeometryCollection' or newShape.geometryType() == 'MultiPolygon':
                    newShapeList = [s for s in newShape if s.geometryType() == 'Polygon' and not s.is_empty]
                    for s in newShapeList:
                        s.ids = unionedIds
                    newShapes += newShapeList

        if not newShapes:
            newIntersectionsFound = False
        else:
            logging.debug("Found {} intersections".format(len(newShapes)))
            shapes = newShapes
            # TODO: simplify newShapes (connected components base on ids for edges)
            result += newShapes

    resultFeatures = []
    for shape in result:
        stations = {features[id]["properties"][idProperty] for id in shape.ids}
        properties = {
            "stations": len(stations),
            "stationNames": stations
        }
        resultFeatures.append(shapeGeomToGeoJson(shape, properties=properties))
        
    return groupBy(geojson.FeatureCollection(resultFeatures), "stations")
