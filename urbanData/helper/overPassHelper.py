from typing import Dict, List
from pathlib import Path
import geojson
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from OSMPythonTools.nominatim import Nominatim

from helper.OsmObjectType import OsmObjectType as OsmType
from helper.OsmDataQuery import OsmDataQuery
from helper.geoJsonConverter import osmObjectsToGeoJSON


class OverPassHelper:
    fileName = "{objectType}_{area}.json"
    filePath = None
    defaultSelectors = [OsmDataQuery("streets", OsmType.WAY, ['"highway"'], "highway"),
                        OsmDataQuery("buildings", OsmType.WAY, ['"building"'], "building"),
                        OsmDataQuery("landuse", OsmType.WAY, ['"landuse"'], "landuse")]

    def __init__(self, outPath='out/data/'):
        # TODO: Validate path is directory
        self.filePath = outPath + self.fileName

    def getAreaId(self, locationName):
        # TODO: check if its a place (otherwise following queries won't work)
        nominatim = Nominatim()
        return nominatim.query(locationName).areaId()

    def getOsmGeoObjects(self, areaId, selector, elementType:OsmType):
        """
        sends overpass-query and return the elements from the json response
        """
        overpass = Overpass()
        # out='geom' also leads to geometry key (list of coordinates for each object)

        query = overpassQueryBuilder(
            area=areaId, elementType=elementType.value, selector=selector, out='geom')
        return overpass.query(query).toJSON()["elements"]

    def saveGeoJson(self, file, data):
        with open(file, 'w', encoding='UTF-8') as outfile:
            # geojson.dump(data, outfile, ensure_ascii=False)
            geojson.dump(data, outfile)

    def fetch(self, areaId, areaName, osmQueries: List[OsmDataQuery] = None, overrideFiles=True) -> List[OsmDataQuery]:
        """ fetch area data via overpassAPI and saves them as geojson
            return a list of osmDataQuery where the filePath is set """
        if not osmQueries:
            osmQueries = self.defaultSelectors
            
        for query in osmQueries:
            file = self.filePath.format(objectType=query.name, area=areaName)
            query.filePath = file
            if Path(file).is_file() and not overrideFiles:
                print("creation skipped, {} exists already".format(file))
            else:
                osmObjects = self.getOsmGeoObjects(areaId, query.osmSelector, query.osmObject)
                print("Loaded {} {} for {}".format(
                    len(osmObjects), query.name, areaName))
                geoJsonObjects = osmObjectsToGeoJSON(osmObjects)
                self.saveGeoJson(file, geoJsonObjects)
        return osmQueries
    
    def directFetch(self, areaId, osmQueries = None) -> List:
        """returns list of geojson featurecollections"""
        if isinstance(osmQueries, OsmDataQuery):
            osmQueries = [osmQueries]
        for query in osmQueries:
          osmObjects = self.getOsmGeoObjects(areaId, query.osmSelector, query.osmObject)  
          yield osmObjectsToGeoJSON(osmObjects)