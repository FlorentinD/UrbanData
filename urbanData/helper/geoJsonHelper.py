import geojson

# TODO: wrapper methods access on geojson objects (avoid direct dict access via "arbitrary keys" in other files)

def groupBy(featureCollection, properties):
    """ groups geoJson featureCollection by given properties """
    if not "features" in featureCollection.keys():
        raise ValueError('features key needs to be defined {}')
    features = featureCollection["features"]
    groups = {}
    if isinstance(properties, str):
        properties = [properties]
    for row in features:
        groupByValue = []
        [groupByValue.append(row["properties"].get(prop,"")) for prop in properties]
        groupByValue = "|".join(groupByValue)
        if not groupByValue in groups:
            groups[groupByValue] = [row]
        else:
            groups[groupByValue].append(row)
    return {key: geojson.FeatureCollection(group) for key, group in groups.items()}

def centerPoint(featureCollection):
    """returns the center for a group of points"""
    features = featureCollection["features"]
    center = [0, 0]
    for feature in features:
        geometry = feature["geometry"]
        if geometry["type"] == "Point":
            point = feature["geometry"]["coordinates"]
            center[0] += point[0]
            center[1] += point[1]
        else:
            raise ValueError("expected a point but got a {}".format(geometry["type"]))
    center[0] /= len(features) 
    center[1] /= len(features) 

    return geojson.Point(coordinates=center)


def unionFeatureCollections(*collections):
    features = []
    for collection in collections:
        if collection["type"] == "FeatureCollection":
            collectionFeatures = collection["features"]
            features.extend(collectionFeatures)
        if collection["type"] == "Feature":
            features.append(collection)
    return geojson.FeatureCollection(features)


# TODO: distinct feature union (by osm id)

def getSchema(featureCollection, amount:int=10):
    """retrieve the top X properties used in given gejson feature collection"""
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
