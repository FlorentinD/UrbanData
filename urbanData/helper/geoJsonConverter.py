import geojson
import logging
from shapely.geometry import mapping
import networkx as nx

POLYGON_TAGS = set(["building", "landuse", "area"])
LINESTRING_TAGS = set(["boundary"])

def osmObjectsToGeoJSON(osmObjects, polygonize = False):
    """given a list osm-objects as json (! in geom out-format!)
        polygonize: try to convert every way to a polygon
    """
    features = []
    for object in osmObjects:
        type = object["type"]
        properties = object["tags"]
        geometry = osmToGeoJsonGeometry(object, polygonize)
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


def osmToGeoJsonGeometry(object, polygonize):
    """
        generating a geojson geometry based on the osm-object

        object: osm object (from overpass-request with out:geom)
        polygonize: boolean, whether each way should be tried to transfrom to a polygon (without regarding its tags)
    """
    if object["type"] == "relation":
            relMembers = object["members"]
            outerGeometries = [osmToGeoJsonGeometry(m, polygonize) for m in relMembers if m['role'] in ["outer",'', 'outline']]
            isMultiPolygon = False

            if outerGeometries:
                # members are unordered, thus for a boundary we need to order them
                exteriorLineCount, exteriorLines = transformToBoundaryLine(outerGeometries)
                if exteriorLines:
                    outerGeometries = exteriorLines
                if exteriorLineCount > 1:
                    isMultiPolygon = True
            innerGeometries = [osmToGeoJsonGeometry(m, polygonize) for m in relMembers if m['role'] == "inner"]

            if not isMultiPolygon:
                coordinates = outerGeometries + innerGeometries
            else:
                # TODO: if multiPolygon -> match innerGeometries ("holes") to exteriorLine
                logging.info("Leaving out holes for osm-way with id: {}".format(object["id"]))
                coordinates = outerGeometries

            if coordinates:
                return tryToConvertToPolygon(object.get("tags",{}), coordinates, polygonize, isMultiPolygon = isMultiPolygon)
            else:
                logging.error("Relationship uses exotic role types. Thus could not convert to geometry. Types: {}".format(
                    [m['role'] for m in relMembers]))
                return geojson.Point([0,0])
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
        return tryToConvertToPolygon(object.get("tags",{}), [points], polygonize)
    else:
        assert(len(points) == 1)
        return geojson.Point(points[0], validate=True)

def tryToConvertToPolygon(tags, lines, polygonize, isMultiPolygon = False):
    """
        Creates a Polygon or LineString based on the given lines
        tags: tags of the base object
        lines: coordinates (basically nested lists)
        polygonize: boolean, if True -> tries to convert every Line to Polygon
        isMultiPolygon: boolean, if each line is an extra polygon else lines = [boundary, holes..]
    """
    # as sometimes tags like "area":"no" exists, which are obviously no polygons
    tags = {tag: v for tag, v in tags.items() if not v == "no"}

    # osm-multipolygon: means just as complex area ... but geojson polygons can also handle holes
    # sometimes they are real multipolygons? (see Dresdener Heide) --> isMultiPolygon
    if POLYGON_TAGS.intersection(tags) or tags.get("type") == "multipolygon" or polygonize: 
        if isMultiPolygon:
            # creating a polygon array for each line (only exterior lines, no holes currently)
            lines = [[line] for line in lines]
            polygon = geojson.MultiPolygon(lines)
        else:
            polygon = geojson.Polygon(lines)
        if not polygon.errors():
            return polygon
        elif not polygonize:
            # with polygonize == true it is expected that this wont work every time
            logging.debug("Could not be converted to a polygon with tags {}".format(tags))
    if len(lines) == 1:
        return geojson.LineString(lines[0], validate=True)
    else:
        if LINESTRING_TAGS.intersection(tags):
            logging.debug("To many lines for a simple line for object with tags: {}".format(tags))
        return geojson.MultiLineString(lines, validate=True)

def transformToBoundaryLine(lines):
    """
        tries to find an euler circuit for each components (based on all lines/line segments)
        returns a tuple (number of boundary lines (= number of polygons), list of the boundary lines)
    """
    graph = nx.Graph()
    # init graph
    for line in lines:
        points = [tuple(p)  for p in line["coordinates"]]
        for p in points:
            graph.add_node(p)
        for start, end in zip(points, points[1:]): 
            graph.add_edge(start, end)
    
    # each subgraph is one boundary line
    subgraphs = list(nx.connected_component_subgraphs(graph))
    lines = []
    for graph in subgraphs:
        try:
            edges = list(nx.eulerian_circuit(graph))
            startpoint = edges[0][0]
            points = [start for start, end in edges]
            # add startpoint, as polygon rings have to end, where they started
            points.append(startpoint)
            lines.append(points)
        except nx.NetworkXError:
            # TODO: allow partly lines and partly polygons
            logging.debug("One of the boundary lines was not an euler train .. a very weird shape this one has")
            return 0, None
    return len(lines), lines
    

def shapeGeomToGeoJson(shape, properties = None):
    """converts a shaply geometry to a geojson Feature"""
    geometry = mapping(shape)
    return geojson.Feature(geometry=geometry, properties=properties)
