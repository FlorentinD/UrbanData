import geojson
from shapely.geometry import mapping

def osmObjectsToGeoJSON(osmObjects):
    """given a list osm-objects as json (! in geom out-format!)"""
    features = []
    for object in osmObjects:
        geometry = osmToGeoJsonGeometry(object)
        properties = object["tags"]
        if object["type"] == "way":
            properties["__nodeIds"] = object["nodes"]
        elif object["type"] == "node":
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
        if(set(object["tags"].keys()).intersection(polygonKeys)):
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

def unionFeatureCollections(*collections):
    features = []
    for collection in collections:
        if collection["type"] == "FeatureCollection":
            collectionFeatures = collection["features"]
            features.extend(collectionFeatures)
        if collection["type"] == "Feature":
            features.append(collection)
    return geojson.FeatureCollection(features)
    
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
