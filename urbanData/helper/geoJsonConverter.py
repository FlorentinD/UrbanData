import geojson
import logging
from shapely.geometry import mapping

POLYGON_TAGS = ["building", "landuse", "area"]
LINESTRING_TAGS = ["boundary"]

def osmObjectsToGeoJSON(osmObjects):
    """given a list osm-objects as json (! in geom out-format!)"""
    features = []
    for object in osmObjects:
        type = object["type"]
        properties = object["tags"]
        geometry = osmToGeoJsonGeometry(object)
        if type == "way":
            properties["__nodeIds"] = object["nodes"]
        elif type == "node":
            properties["__nodeId"] = object["id"]
        feature = geojson.Feature(
            id=object["id"], geometry=geometry, properties=properties)
        features.append(feature)
    result = geojson.FeatureCollection(features, validate=True)
    for error in result.errors():
        raise ValueError(
            "Error converting osm object to geojson: {}".format(error))
    return result


def osmToGeoJsonGeometry(object):
    if object["type"] == "relation":
            # Todo tag based
            # TODO: use type:multipolygon
            relMembers = object["members"]
            outerGeometries = [osmToGeoJsonGeometry(m) for m in relMembers if m['role'] in ["outer",'']]
            innerGeometries = [osmToGeoJsonGeometry(m) for m in relMembers if m['role'] == "inner"]    
            coordinates = outerGeometries + innerGeometries
            # TODO: Order members (as they can be unsorted) probably inverted index usabel for order? 
            # (or graph algo ... longest path probably / try finding a euler-zug)
            return tryToConvertToPolygon(object.get("tags",{}), coordinates)
    elif "geometry" in object:
        points = [[pos["lon"], pos["lat"]] for pos in object["geometry"]]
    elif "lon" in object and "lat" in object:
        points = [[object["lon"], object["lat"]]]
    else:
        raise ValueError("{} contains no geometry or lon/lat data".format(object))
    if points is None:
        raise ValueError('osm object has no geometry key {}'.format(object))
    if len(points) > 1:
        return tryToConvertToPolygon(object.get("tags",{}), points)
    else:
        assert(len(points) == 1)
        return geojson.Point(points[0], validate=True)

def tryToConvertToPolygon(tags, points):
    tagsKeys = set(tags.keys())
    # osm-multipolygon: means just as complex area ... but geojson polygons can also handle holes
    if tagsKeys.intersection(POLYGON_TAGS) or tags.get("type") == "multipolygon":
        if tags.get("type") == "multipolygon":
            # due to coming already in right format
            polygon = geojson.Polygon(points)
        else:
            # [points] as this is the outer linestring of the polygon (no holes in osm, if not specified) 
            polygon = geojson.Polygon([points])
        if not polygon.errors():
            return polygon
        else:
            logging.debug("Could not be converted to a polygon with tags {}".format(tags))
    line = geojson.LineString(points)
    if not line.errors():
        return line
    else:
        if tagsKeys.intersection(LINESTRING_TAGS):
            logging.debug("Could not be converted to a linestring with tags {}".format(tags))
        return geojson.MultiLineString(points, validate=True)

def shapeGeomToGeoJson(shape, properties = None):
    geometry = mapping(shape)
    return geojson.Feature(geometry=geometry, properties=properties)
