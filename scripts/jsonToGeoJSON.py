import geojson

# given a list osm-objects as json (! in geom out-format!)
def osmWaysToGeoJSON(osmObject):
    features = []
    for object in osmObject:
        geometry = osmToGeoJsonGeometry(object)
        feature = geojson.Feature(id=object["id"], geometry=geometry, properties=object["tags"])
        features.append(feature)
    result = geojson.FeatureCollection(features)
    for error in result.errors():
        raise ValueError("Error converting osm object to geojson: {}".format(error))
    return result 

# TODO: polygon? (building)
def osmToGeoJsonGeometry(object):
    type = object["type"]
    points = [[pos["lon"],pos["lat"]] for pos in object["geometry"]]
    if points is None:
        raise ValueError('osm object has no geometry key {}'.format(object))
    if type == "way":
            return geojson.LineString(points, validate=True)
    elif type == "node":
            assert(len(points) == 1)
            return geojson.Point(points[0], validate=True)
    else:
        raise ValueError('osm object {} not supported yet'.format(type))

    