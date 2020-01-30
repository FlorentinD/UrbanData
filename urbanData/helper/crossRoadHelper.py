from collections import defaultdict
import logging

def getCrossRoads(streets):
    # TODO: save names as well as streettypes possible tuple
    crosspoints = defaultdict(int)
    for street in streets["features"]:
        name = street["properties"].get("name", "osm-id: {}".format(street["id"]))
        geomType = street["geometry"]["type"]
        if not geomType == "LineString":
            # as https://www.openstreetmap.org/way/309830643 would lead to falsely huge crossroads
            logging.debug("Skipped {} as it is not a way but a {}".format(name, geomType))
            continue
        for point in street["geometry"]["coordinates"]:
            point = tuple(point)
            crosspoints[point] += 1
    crosspoints = {point: streetCount for point, streetCount in crosspoints.items() if streetCount > 1}

    #TODO: convert into geojson Points with own tags
    return crosspoints