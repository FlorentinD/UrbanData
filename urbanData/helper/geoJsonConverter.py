import geojson
import logging
from shapely.geometry import mapping
import networkx as nx

POLYGON_TAGS = set(["building", "landuse", "area"])
LINESTRING_TAGS = set(["boundary"])

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
            relMembers = object["members"]
            outerGeometries = [osmToGeoJsonGeometry(m) for m in relMembers if m['role'] in ["outer",'']]
            # members are unordered, thus for a boundary we need to order them
            exteriorLine = transformToBoundaryLine(outerGeometries)
            if exteriorLine:
                outerGeometries = [exteriorLine]
            innerGeometries = [osmToGeoJsonGeometry(m) for m in relMembers if m['role'] == "inner"]    
            coordinates = outerGeometries + innerGeometries
            return tryToConvertToPolygon(object.get("tags",{}), coordinates)
    elif object["type"] == "way":
        points = [[pos["lon"], pos["lat"]] for pos in object["geometry"]]
    elif object["type"] == "node":
        points = [[object["lon"], object["lat"]]]
    else:
        raise ValueError("{} neither node, way or rel conform geometry".format(object))
    if points is None:
        raise ValueError('osm object has no geometry {}'.format(object))
    if len(points) > 1:
        # [points] as ways can only be a simple line
        return tryToConvertToPolygon(object.get("tags",{}), [points])
    else:
        assert(len(points) == 1)
        return geojson.Point(points[0], validate=True)

def tryToConvertToPolygon(tags, lines):
    # as sometimes tags like "area":"no" exists, which are obviously no polygons
    tags = {tag: v for tag, v in tags.items() if not v == "no"}

    # osm-multipolygon: means just as complex area ... but geojson polygons can also handle holes
    if POLYGON_TAGS.intersection(tags) or tags.get("type") == "multipolygon": 
        polygon = geojson.Polygon(lines)
        if not polygon.errors():
            return polygon
        else:
            logging.debug("Could not be converted to a polygon with tags {}".format(tags))
    if len(lines) == 1:
        return geojson.LineString(lines[0], validate=True)
    else:
        if LINESTRING_TAGS.intersection(tags):
            logging.debug("To many lines for a simple line for object with tags: {}".format(tags))
        return geojson.MultiLineString(lines, validate=True)

def transformToBoundaryLine(lines):
    """
        tries to find an euler circuit based on all lines
    """
    graph = nx.Graph()
    for line in lines:
        points = [tuple(p)  for p in line["coordinates"]]
        for p in points:
            graph.add_node(p)
        for start, end in zip(points, points[1:]): 
            graph.add_edge(start, end)
    try:
        edges = list(nx.eulerian_circuit(graph))
        startpoint = edges[0][0]
        points = [start for start, end in edges]
        # add startpoint, as polygon rings have to end, where they started
        points.append(startpoint)
        return points
    except nx.NetworkXError:
        logging.debug("Boundary line was not an euler train")
        return None

def shapeGeomToGeoJson(shape, properties = None):
    geometry = mapping(shape)
    return geojson.Feature(geometry=geometry, properties=properties)
