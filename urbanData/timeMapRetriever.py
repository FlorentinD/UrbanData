import logging
import requests
import geojson
import time
from datetime import datetime
from dvbRetriever import getPublicStops

logging.basicConfig(level=logging.INFO)

def transformStop(stop, walkingtime):
    """osm stop to departure_search point for time-map API"""
    assert(stop["geometry"]["type"] == "Point")

    pointCoords = stop["geometry"]["coordinates"]
    return {
                "id": stop["properties"]["name"],
                "coords": {
                    "lng": pointCoords[0],
                    "lat": pointCoords[1]
                },
                "transportation": {
                    "type": "walking"
                },
                "travel_time": 300,
                "departure_time": datetime.now().isoformat()
            }


def retrieveTimeMaps(stops, walkingtime = 300):
    api_url = 'https://api.traveltimeapp.com/v4/time-map'
    api_token = None
    app_id = '13de259b'
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Application-Id': app_id,
    'X-Api-Key': api_token}

    timeMaps = []
    for progressIndex, stop in enumerate(stops):
        if (progressIndex) % 10 == 0:
            logging.info("Fetched {}/{}".format(progressIndex + 1, len(stops)))
        time.sleep(8)
        departureSearchEntry = transformStop(stop, walkingtime)
        # up to 10 searches per request / minute and 5000 calls per month
        requestBody = {
            "departure_searches": [departureSearchEntry]
        }
        response = requests.post(api_url, headers=headers,  json=requestBody)

        
        if response.status_code == 200:
            responseContent = response.json()["results"][0]
            #search_id = stop["properties"]["name"]
            mapShapes = responseContent["shapes"]
            shapeCount = len(mapShapes)
            for index, mapShape in enumerate(mapShapes):
                properties = stop["properties"]
                if shapeCount > 1:
                    properties["timeMapPart"] = index
                # TODO: use holes
                if mapShape["holes"]:
                    logging.warn("Holes in timemap are not yet propageted to geojson geometry")
                geometry = geojson.Polygon(coordinates= [[[point["lng"], point["lat"]] for point in mapShape["shell"]]], validate=True)
                timeMap = geojson.Feature(geometry=geometry, properties=properties)
                
                timeMaps.append(timeMap)
        else:
            logging.error(response.reason())

    return geojson.FeatureCollection(timeMaps)

if __name__ == "__main__":
    stopsByName = getPublicStops()
    logging.info("Retrieve time maps for each stop")
    timeMaps = retrieveTimeMaps(stopsByName)
    fileName = "out/data/timeMapsPerStop.json"
    with open(fileName, 'w', encoding='UTF-8') as outfile:
        logging.info("Saving at {}".format(fileName))
        geojson.dump(timeMaps, outfile)
