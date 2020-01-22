import geojson
from shapely.geometry import mapping

def osmObjectsToGeoJSON(osmObjects):
    """given a list osm-objects as json (! in geom out-format!)"""
    features = []
    for object in osmObjects:
        type = object["type"]
        properties = object["tags"]
        if type == "relation":
            relMembers = object["members"]
            memberGeometries = [osmToGeoJsonGeometry(m) for m in relMembers]
            geometry = geojson.MultiLineString(coordinates=memberGeometries)
        else:
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
    if "geometry" in object:
        points = [[pos["lon"], pos["lat"]] for pos in object["geometry"]]
    elif "lon" in object and "lat" in object:
        points = [[object["lon"], object["lat"]]]
    else:
        raise ValueError("{} contains no geometry or lon/lat data".format(object))
    if points is None:
        raise ValueError('osm object has no geometry key {}'.format(object))
    if len(points) > 1:
        polygonKeys = ["building", "landuse", "area"]
        if(set(object.get("tags",{}).keys()).intersection(polygonKeys)):
            polygon = geojson.Polygon([points])
            if polygon.errors():
                print("Could not convert to a polygon {}".format(object))
                return geojson.LineString(points, validate=True)
            else:
                return polygon
        else:
            return geojson.LineString(points, validate=True)
    else:
        assert(len(points) == 1)
        return geojson.Point(points[0], validate=True)

def shapeGeomToGeoJson(shape, properties = None):
    geometry = mapping(shape)
    return geojson.Feature(geometry=geometry, properties=properties)