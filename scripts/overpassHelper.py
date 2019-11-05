# from https://github.com/mocnik-science/osm-python-tools (adapted example 3)
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from jsonToGeoJSON import osmWaysToGeoJSON
import geojson


def getAreaId(locationName):
    # TODO: check if its a place (otherwise following queries won't work)
    nominatim = Nominatim()
    return nominatim.query(locationName).areaId()


#overpass = Overpass()
# treeQuery = overpassQueryBuilder(
#    area=getDresdenAreaId(), elementType='node', selector='"natural"="tree"', out='count')
#result = overpass.query(treeQuery)
#print("There are {} trees in Dresden".format(result.countElements()))


def getOsmGeoObjects(areaId, selector):
    overpass = Overpass()
    # out='geom' also leads to geometry key (list of coordinates for each object)
    query = overpassQueryBuilder(
        area=areaId, elementType='way', selector=selector, out='geom')
    return overpass.query(query).toJSON()["elements"]


def saveGeoJson(filename, data):
    filePath = 'out/{}.json'.format(filename)
    with open(filePath, 'w', encoding='UTF-8') as outfile:
        #geojson.dump(data, outfile, ensure_ascii=False)
        geojson.dump(data, outfile)


def fetchBuildingsAndStreets(areaId, areaName):
    """ fetch via overpassAPI and saves them as geojson """
    SELECTORS = {"streets": ['"highway"'], "buildings": ['"building"']}
    for name, selector in SELECTORS.items():
        osmObjects = getOsmGeoObjects(areaId, selector)
        print("Loaded {} {} for {}".format(len(osmObjects), name, areaName))
        geoJsonObjects = osmWaysToGeoJSON(osmObjects)
        fileName = "{}_{}".format(name, areaName)
        saveGeoJson(fileName, geoJsonObjects)


def main():
    dresdenArea = getAreaId('Dresden, Germany')
    fetchBuildingsAndStreets(dresdenArea, "dresden")


if __name__ == "__main__":
    main()
