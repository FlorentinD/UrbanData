# from https://github.com/mocnik-science/osm-python-tools (adapted example 3)
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from pathlib import Path
from jsonToGeoJSON import osmWaysToGeoJSON
import geojson

class OverPassHelper:
    fileName = "{objectType}_{area}.json"
    filePath = None
    selectors = {"streets": ['"highway"'], "buildings": ['"building"'], "landuse": ['"landuse"']}

    def __init__(self, outPath='out/'):
        # TODO: Validate path is directory
        self.filePath = outPath + self.fileName

    def getAreaId(self, locationName):
        # TODO: check if its a place (otherwise following queries won't work)
        nominatim = Nominatim()
        return nominatim.query(locationName).areaId()

    def getOsmGeoObjects(self, areaId, selector):
        overpass = Overpass()
        # out='geom' also leads to geometry key (list of coordinates for each object)
        query = overpassQueryBuilder(
            area=areaId, elementType='way', selector=selector, out='geom')
        return overpass.query(query).toJSON()["elements"]


    def saveGeoJson(self, file, data):
        with open(file, 'w', encoding='UTF-8') as outfile:
            #geojson.dump(data, outfile, ensure_ascii=False)
            geojson.dump(data, outfile)


    def fetch(self, areaId, areaName, overrideFiles=True):
        """ fetch area data via overpassAPI and saves them as geojson """
        for name, selector in self.selectors.items():
            file = self.filePath.format(objectType = name, area = areaName)
            if Path(file).is_file() and not overrideFiles:
                print("creation skipped, {} exists already".format(file))
            else:
                osmObjects = self.getOsmGeoObjects(areaId, selector)
                print("Loaded {} {} for {}".format(
                    len(osmObjects), name, areaName))
                geoJsonObjects = osmWaysToGeoJSON(osmObjects)
                self.saveGeoJson(file, geoJsonObjects)


    def main(self):
        dresdenArea = self.getAreaId('Dresden, Germany')
        self.fetch(dresdenArea, "dresden")