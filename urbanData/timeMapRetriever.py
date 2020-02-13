import logging
import requests
import geojson
import time
from datetime import datetime
from dvbRetriever import getPublicStops

from cityPatterns import getOpenAtMidnightThings

from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.shapelyHelper import geomCenter

logging.basicConfig(level=logging.INFO)

dresdenAreaId = OverPassHelper().getAreaId("Dresden, Germany")

def transformStop(poI, travelTime, transportation):
    """generate departure_search point for time-map API based on point of interest (with name property)"""
    if not poI["geometry"]["type"] == "Point":
        pointCoords = geomCenter(poI["geometry"])
    else:
        pointCoords = poI["geometry"]["coordinates"]
    return {
                "id": poI["properties"].get("name", "osm-id:{}".format(poI["id"])),
                "coords": {
                    "lng": pointCoords[0],
                    "lat": pointCoords[1]
                },
                "transportation": {
                    "type": transportation
                },
                "travel_time": travelTime,
                "departure_time": datetime.now().isoformat()
            }


def retrieveTimeMaps(pointsOfInterest, travelTime = 300, transportation = "walking"):
    api_url = 'https://api.traveltimeapp.com/v4/time-map'
    api_token = None
    app_id = '13de259b'
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Application-Id': app_id,
    'X-Api-Key': api_token}

    timeMaps = []

    if not api_token or not app_id:
        raise ValueError("Missing credentials for using timeMapAPI")

    if isinstance(pointsOfInterest, dict) and pointsOfInterest.get("type") == "FeatureCollection":
        pointsOfInterest = pointsOfInterest["features"]

    for progressIndex, poI in enumerate(pointsOfInterest):
        departureSearchEntry = transformStop(poI, travelTime, transportation)
        requestBody = {
            "departure_searches": [departureSearchEntry]
        }
        #continue
        if (progressIndex) % 10 == 0:
            logging.info("Fetched {}/{}".format(progressIndex + 1, len(pointsOfInterest)))
        time.sleep(8)
        # up to 10 searches per request / minute and 5000 calls per month
        response = requests.post(api_url, headers=headers,  json=requestBody)
        
        if response.status_code == 200:
            responseContent = response.json()["results"][0]
            #search_id = stop["properties"]["name"]
            mapShapes = responseContent["shapes"]
            shapeCount = len(mapShapes)
            for index, mapShape in enumerate(mapShapes):
                properties = poI["properties"].copy()
                if shapeCount > 1:
                    properties["timeMapPart"] = index
                exterior = [[point["lng"], point["lat"]] for point in mapShape["shell"]]
                polygonLines = [exterior]
                if mapShape["holes"]:
                    for hole in mapShape["holes"]:
                        interiorLine = [[point["lng"], point["lat"]] for point in hole]
                        polygonLines.append(interiorLine)
                geometry = geojson.Polygon(coordinates= polygonLines, validate=True)
                timeMap = geojson.Feature(geometry=geometry, properties=properties)
                timeMaps.append(timeMap)
        else:
            logging.error(response.reason())

    return geojson.FeatureCollection(timeMaps)


def timeMapsForStops():
    stopsByName = getPublicStops()
    logging.info("Retrieve time maps for each stop")
    timeMaps = retrieveTimeMaps(stopsByName, travelTime=300)
    fileName = "out/data/timeMapsPerStop.json"
    with open(fileName, 'w', encoding='UTF-8') as outfile:
        logging.info("Saving at {}".format(fileName))
        geojson.dump(timeMaps, outfile)

def timeMapsForCityHalls():
    townHalls = next(OverPassHelper().directFetch(dresdenAreaId, [OsmDataQuery("Town Halls", OsmObjectType.ALL, ['"amenity"="townhall"'])]))
    # "driving+train" got many shapes (heatmap function could not handle them) .. trying "public_transport"
    timeMaps = retrieveTimeMaps(townHalls["features"], travelTime=1800, transportation="public_transport")
    fileName = "out/data/timeMapsPerCityHall.json"
    with open(fileName, 'w', encoding='UTF-8') as outfile:
        logging.info("Saving at {}".format(fileName))
        geojson.dump(timeMaps, outfile)

def timeMapsForPharmacies():
    pharmacies = next(OverPassHelper().directFetch(dresdenAreaId, [OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"pharmacy"'])]))
    timeMaps = retrieveTimeMaps(pharmacies["features"], travelTime=900, transportation="walking")
    fileName = "out/data/timeMapsPerPharmacy.json"
    with open(fileName, 'w', encoding='UTF-8') as outfile:
        logging.info("Saving at {}".format(fileName))
        geojson.dump(timeMaps, outfile)

def timeMapsForMidnightThings(): 
    openAtMidnight = getOpenAtMidnightThings()
    openEndtimeMaps = retrieveTimeMaps(openAtMidnight["Open end"]["features"], travelTime=300, transportation="walking")
    fileName = "out/data/timeMapsPerMidnightThingOpenEnd.json"
    with open(fileName, 'w', encoding='UTF-8') as outfile:
        logging.info("Saving at {}".format(fileName))
        geojson.dump(openEndtimeMaps, outfile)

    opentimeMaps = retrieveTimeMaps(openAtMidnight["True"]["features"], travelTime=300, transportation="walking")
    fileName = "out/data/timeMapsPerMidnightThing.json"
    with open(fileName, 'w', encoding='UTF-8') as outfile:
        logging.info("Saving at {}".format(fileName))
        geojson.dump(opentimeMaps, outfile)

if __name__ == "__main__":
    #timeMapsForStops()
    #timeMapsForPharmacies()
    #timeMapsForCityHalls()
    timeMapsForMidnightThings()
