import geojson


def osmWaysToGeoJSON(osmObject):
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
    # TODO: polygon? (building)
    type = object["type"]
    points = [[pos["lon"], pos["lat"]] for pos in object["geometry"]]
    if points is None:
        raise ValueError('osm object has no geometry key {}'.format(object))
    if type == "way":
        return geojson.LineString(points, validate=True)
    elif type == "node":
        assert(len(points) == 1)
        return geojson.Point(points[0], validate=True)
    else:
        raise ValueError('osm object {} not supported yet'.format(type))


# geoJsonGroupBy TODO: also retrieve schema info?
def groupBy(featureCollection, properties):
    """ groups geoJson featureCollection by given properties """
    if not featureCollection["features"]:
        raise ValueError('FeatureCollection expected, but no features found')
    features = featureCollection["features"]
    groups = {}
    if isinstance(properties, str):
        columns = [columns]
    for row in features:
        groupByValue = []
        [groupByValue.append(row["properties"][prop]) for prop in properties]
        groupByValue = "|".join(groupByValue)
        if not groupByValue in groups:
            groups[groupByValue] = [row]
        else:
            groups[groupByValue].append(row)
    return {key: geojson.FeatureCollection(group) for key, group in groups.items()}
