import geojson
from shapely.geometry import mapping

def osmObjectsToGeoJSON(osmObject):
    """given a list osm-objects as json (! in geom out-format!)"""
    features = []
    for object in osmObject:
        geometry = osmToGeoJsonGeometry(object)
        feature = geojson.Feature(
            id=object["id"], geometry=geometry, properties=object["tags"])
        features.append(feature)
    result = geojson.FeatureCollection(features)
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
          # TODO: polygon for f.i. landuse
        return geojson.LineString(points, validate=True)
    else:
        assert(len(points) == 1)
        return geojson.Point(points[0], validate=True)


# TODO: extend with properties
def shapeGeomToGeoJson(shapes):
    features = []
    for id, shape in enumerate(shapes):
        geometry = mapping(shape)
        features.append(geojson.Feature(id=id, geometry=geometry, properties=[]))
    return geojson.FeatureCollection(features)

# geoJsonGroupBy TODO: also retrieve schema info?
def groupBy(featureCollection, properties):
    """ groups geoJson featureCollection by given properties """
    if not featureCollection["features"]:
        raise ValueError('FeatureCollection expected, but no features found')
    features = featureCollection["features"]
    groups = {}
    if isinstance(properties, str):
        properties = [properties]
    for row in features:
        groupByValue = []
        [groupByValue.append(row["properties"][prop]) for prop in properties]
        groupByValue = "|".join(groupByValue)
        if not groupByValue in groups:
            groups[groupByValue] = [row]
        else:
            groups[groupByValue].append(row)
    return {key: geojson.FeatureCollection(group) for key, group in groups.items()}


def getSchema(featureCollection, amount:int=10):
    properties = {}
    for feature in featureCollection["features"]:
        for property in feature["properties"].keys():
            if property in properties:
                properties[property] += 1
            else:
                properties[property] = 0
    properties = list(properties.items())
    properties.sort(key=lambda tup: tup[1], reverse=True)

    if amount > len(properties):
        amount = len(properties)
    return [name for name, count in properties[:amount]]