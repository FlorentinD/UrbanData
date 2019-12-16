import sys, os
from collections import defaultdict
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from shapely.geometry import mapping, shape

from annotater.annotator import Annotator

from helper.geoJsonConverter import osmObjectsToGeoJSON
from helper.OsmObjectType import OsmObjectType

class OsmAnnotator(Annotator):
    osmSelector = None 

    def __init__(self, areaName: str, elementsToUse: OsmObjectType = OsmObjectType.NODE):
        areaId = Nominatim().query(areaName).areaId()
        query = overpassQueryBuilder(
            area=areaId, elementType=elementsToUse.value, selector= self.osmSelector, out='geom')
        osmObjects = Overpass().query(query).toJSON()["elements"]
        #for element in osmObjects:
        #    element["tags"] = {key: value for (key, value) in element["tags"].items() if key.startswith("addr:")}
        # TODO: Performance ? use shapely STRTree for querying this (need to set index attr in geometry for this! https://github.com/Toblerity/Shapely/issues/618)
        self.dataSource = osmObjectsToGeoJSON(osmObjects)["features"]
        # !!! geometry in shapely form
        for loc in self.dataSource:  
            loc["geometry"] = shape(loc["geometry"])

class AddressAnnotator(OsmAnnotator):
    """Annotates an object with addresses of contained objects
        f.i. buildings gets addresses of all entrances"""

    writeProperty = "addresses"
    osmSelector = ['"addr:street"', '"addr:housenumber"']
    
    def __generateStreetsKey(self, postalCode, street):
        return "{}, {}".format(postalCode, street)
    
    def annotate(self, object):
        """based on geojson-object geometry or osm node-ids searches the address"""
        objectGeometry = shape(object["geometry"])
        containsAddress = [key for key in object["properties"].keys() if key.startswith("addr:housenumber")]
        if containsAddress:
            postalCode = object["properties"].get("addr:postcode", None)
            street = object["properties"].get("addr:street", None)
            houseNumber = object["properties"].get("addr:housenumber", None)
            key = self.__generateStreetsKey(postalCode, street)
            addresses = {key: [houseNumber]}
        else:
            if(object["properties"]["__nodeIds"]):
                addresses = self.addressesBasedOnOsmIds(object["properties"]["__nodeIds"])
            else:
                addresses = defaultdict(list)
                for location in self.dataSource:
                    # 'contains' not enough for polygons having points on its edges 
                    if objectGeometry.intersects(location["geometry"]):
                        postalCode = location["properties"].get("addr:postcode", None)
                        street = location["properties"].get("addr:street", None)
                        houseNumber = location["properties"].get("addr:housenumber", None)
                        key = self.__generateStreetsKey(postalCode, street)
                        addresses[key].append(houseNumber)
        # ! can still be empty (f.i. https://www.openstreetmap.org/way/35540321 or https://www.openstreetmap.org/way/32610207) could only be solved by taking nearest element with address 
        object["properties"][self.writeProperty] = addresses
        return object
    
    def addressesBasedOnOsmIds(self, nodeIds):
        matchingLocations = [loc for loc in self.dataSource if loc["properties"]["__nodeId"] in nodeIds]
        addresses = defaultdict(list)
        for location in matchingLocations:
            postalCode = location["properties"].get("addr:postcode", None)
            street = location["properties"].get("addr:street", None)
            houseNumber = location["properties"].get("addr:housenumber", None)
            key = self.__generateStreetsKey(postalCode, street)
            addresses[key].append(houseNumber)
        return addresses

    @staticmethod
    def unionAddresses(addresses):
        """unions multiple addresses"""
        union = defaultdict(list)
        for dic in addresses:
            for key, value in dic.items():
                if value:
                    union[key].extend(value)
        return union



class BuildingLvlAnnotator(Annotator):
    """combines building:levels - building:min_level  + roof:levels into new property 'levels'
    based on: https://wiki.openstreetmap.org/wiki/Key:building:levels"""
    osmSelector = ['"addr:street"', '"addr:housenumber"']
    writeProperty = "levels"

    def __init__(self):
        pass

    def annotate(self, object):
        """ assumes 0 levels means, it is not defined"""
        properties : dict = object["properties"]
        buildingLevels = int(properties.get("building:levels", 0))
        buildingMinLevels = int(properties.get("building:min_level", 0))
        roofLevels = int(properties.get("roof:levels", 0))
        object["properties"][self.writeProperty] = buildingLevels - buildingMinLevels + roofLevels
        return object



class BuildingTypeClassifier(Annotator):
    # depends on properties: "buildings", "companies"
    # f.i. living, education, ... 
    # TODO
    # could be list of types per building?
    def __init__():
        pass