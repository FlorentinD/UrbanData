import logging
import geojson
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.geoJsonHelper import groupBy, centerPoint
from helper.overPassHelper import OverPassHelper
import dvb
import time
import requests

logging.basicConfig(level=logging.INFO)

overpassFetcher = OverPassHelper()
pieschenAreaId = overpassFetcher.getAreaId("Dresden, Germany")

logging.info("Get stops from openstreetmap")
stopsOsmQuery = OsmDataQuery("Public Transport stops", OsmObjectType.NODE, ['"public_transport"="stop_position"'])
stops = next(overpassFetcher.directFetch(pieschenAreaId, [stopsOsmQuery]))
stopsByName = []

logging.info("Group stops by name")
for name, group in groupBy(stops, "name").items():
    center = centerPoint(group)
    # TODO: more properties?
    # TODO: maybe draw line instead of just center point?
    properties = {
        "name": name,
        "stop_positions": len(group["features"])
    }
    stopByName = geojson.Feature(geometry=center, properties=properties)
    stopsByName.append(stopByName)


logging.info("Retrieve line info for each stop")

# Problem: stop does not have to make sense for getting a result (tried "tst")
# Problem: based on current time
# better approach: https://github.com/kiliankoe/vvo/blob/master/documentation/webapi.md#lines (but need to get stopId using the pointFinder)
changePoints = []
countUniqueStops = len(stopsByName)
for index, stop in enumerate(list(stopsByName)):
    if index % 3 == 0:
        logging.info("progress: {}/{}".format(index + 1, countUniqueStops))
        time.sleep(5)
    name = stop["properties"]["name"]
    # TODO:
    if name: 
        try:
            dvbResponse = dvb.monitor(name)
        except requests.HTTPError:
            logging.error("dvb said no for {}, timeout for 30s".format(name))
            time.sleep(10)
            try:
                # poor mans retry
                dvbResponse = dvb.monitor(name)
            except requests.HTTPError:
                continue
        if dvbResponse:
            lines = list(set([info.get("line", None) for info in dvbResponse if info]))
            stop["properties"]["lines"] = lines
            # TODO: show this based on color only? (could save lines for every stop)
            # if more than 1 line departes from this stop, it is a change point
            canChange = len(lines) > 1
            if canChange:
                changePoints.append(stop)
changePoints = geojson.FeatureCollection(changePoints)

with open("out/data/dvbChangePoints.json", 'w', encoding='UTF-8') as outfile:
    geojson.dump(changePoints, outfile)
