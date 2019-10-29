import geojson

# given a list osm-ways as json (in geom format)
def osmWaysToGeoJSON(ways):
    features = []
    for way in ways:
        points = [[pos["lon"],pos["lat"]] for pos in way["geometry"]]
        line = geojson.LineString(points)
        if not line.errors() is None:
            print("Error creating line: {}".format(feature.errors))
        feature = geojson.Feature(id=way["id"], geometry=line, properties=way["tags"])
        if not feature.errors() is None:
            print("Error creating feature: {}".format(feature.errors))
        features.append(feature)
    result = geojson.FeatureCollection(features)
    for error in result.errors():
        print("Error converting osm ways to geojson: {}".format(error))
    return result 