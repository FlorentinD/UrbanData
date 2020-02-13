from shapely.strtree import STRtree
from shapely.geometry import shape as shapeFunc
from helper.geoJsonConverter import shapeGeomToGeoJson
from helper.geoJsonHelper import groupBy
import geojson
import logging

def intersections(geoJsonFeatureCollection, idProperty = "name", kindOfFeatures = "stations", maxIterations = None):
    """
        calculates every intersection of the geometries ...
        ! might take quite a while for geometries with many overlapping areas 
        ! not raster based

        geoJsonFeatureCollection: input features on which intersections are calculated
        idProperty: property of the feature used for intersection describtion
        kindOfObjects: describtion of the features
        maxIterations: maximum of iterations to search for new intersections (aka maximum intersection depth)
    """
    # TODO: allow alternative version based on rasters?
    # raster version: 
    #   1. convex-hull or bounding box over all geoms
    #   2. raster convex hull with given precision
    #   3. iterate through each input geom and input raster
    #   *4. union adjacent rasters if they have the same properties/geom-ids
    features = geoJsonFeatureCollection["features"]
    shapeMapping = { id: shapeFunc(feature["geometry"]) for id, feature in enumerate(features)}

    # add id attribute to shapes (for later reference when retrieved from index)
    for id, currentShape in shapeMapping.items():
        currentShape.ids = set([id])

    newIntersectionsFound = True
    shapes = shapeMapping.values()

    foundIntersections = set()
    result = list(shapes)

    iterations = 0
    while newIntersectionsFound and not maxIterations == iterations:
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
            result += newShapes
        iterations += 1

    resultFeatures = []
    for shape in result:
        featureNames = {features[id]["properties"].get(idProperty, "unnamed") for id in shape.ids}
        properties = {
            kindOfFeatures: len(featureNames),
            "names": featureNames
        }
        resultFeatures.append(shapeGeomToGeoJson(shape, properties=properties))

    resultGroups = groupBy(geojson.FeatureCollection(resultFeatures), kindOfFeatures)
    if newIntersectionsFound:
        logging.info("Terminated earlier due to set maxIterations")
        maxIntersections = max([int(k) for k in resultGroups.keys()])
        resultGroups[">=" + str(maxIntersections)] = resultGroups.pop(str(maxIntersections))
    return resultGroups


def geomCenter(geom):
    """
        returns the center point for an arbitrary geometry
    """
    return shapeFunc(geom).centroid.coords[0]