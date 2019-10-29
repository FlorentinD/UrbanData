# from https://github.com/mocnik-science/osm-python-tools (adapted example 3)
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from jsonToGeoJSON import osmWaysToGeoJSON 
import geojson

def getDresdenAreaId():
    nominatim = Nominatim()
    return nominatim.query('Dresden, Germany').areaId()


#overpass = Overpass()
#treeQuery = overpassQueryBuilder(
#    area=getDresdenAreaId(), elementType='node', selector='"natural"="tree"', out='count')
#result = overpass.query(treeQuery)
#print("There are {} trees in Dresden".format(result.countElements()))


def getDresdenHighways():
    overpass = Overpass()
    # out='geom' also leads to geometry key (list of coordinates for each object)
    houseQuery = overpassQueryBuilder(
        area=getDresdenAreaId(), elementType='way', selector=['"highway"'], out='geom')
    return overpass.query(houseQuery)

highways = getDresdenHighways().toJSON()["elements"]
highways = osmWaysToGeoJSON(highways)





# TODO: add encoding='UTF-8'
with open('out/highways.json', 'w', encoding='UTF-8') as outfile:
    #geojson.dump(highways, outfile, ensure_ascii=False)
    geojson.dump(highways, outfile)
