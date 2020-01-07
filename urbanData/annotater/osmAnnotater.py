import re
import geojson
import statistics
from collections import defaultdict
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from shapely.geometry import mapping, shape

from annotater.baseAnnotator import BaseAnnotator

from helper.geoJsonConverter import osmObjectsToGeoJSON
from helper.OsmObjectType import OsmObjectType

class OsmAnnotator(BaseAnnotator):
    osmSelector = None 

    def __init__(self, areaName: str, elementsToUse: OsmObjectType = OsmObjectType.NODE):
        assert(self.osmSelector)

        areaId = Nominatim().query(areaName).areaId()
        query = overpassQueryBuilder(
            area=areaId, elementType=elementsToUse.value, selector= self.osmSelector, out='geom')
        osmObjects = Overpass().query(query).toJSON()["elements"]
        # TODO: Performance ? use shapely STRTree for querying this (need to set index attr in geometry for this! https://github.com/Toblerity/Shapely/issues/618)
        self.dataSource = osmObjectsToGeoJSON(osmObjects)["features"]
        # !!! geometry in shapely form
        for loc in self.dataSource:  
            loc["geometry"] = shape(loc["geometry"])

class AddressAnnotator(OsmAnnotator):
    """Annotates an object with addresses of contained objects
        f.i. buildings gets addresses of all entrances"""

    writeProperty = "addresses"
    # TODO: allow addresses only with HouseNumber and fill in the missing details like PostalCode and street from surrounding (at buildingGroup level)
    osmSelector = ['"addr:street"', '"addr:housenumber"']
    
    @staticmethod
    def generateAddressKey(postalCode, street):
        return "{}, {}".format(postalCode, street)
    
    def annotate(self, object):
        """based on geojson-object geometry or osm node-ids searches the address"""
        objectGeometry = shape(object["geometry"])
        containsAddress = [key for key in object["properties"].keys() if key.startswith("addr:housenumber")]
        if containsAddress:
            postalCode = object["properties"].get("addr:postcode")
            street = object["properties"].get("addr:street")
            houseNumber = object["properties"].get("addr:housenumber")
            key = self.generateAddressKey(postalCode, street)
            addresses = {key: [houseNumber]}
        else:
            if(object["properties"]["__nodeIds"]):
                addresses = self.addressesBasedOnOsmIds(object["properties"]["__nodeIds"])
            else:
                addresses = defaultdict(list)
                for location in self.dataSource:
                    # 'contains' not enough for polygons having points on its edges 
                    if objectGeometry.intersects(location["geometry"]):
                        postalCode = location["properties"].get("addr:postcode")
                        street = location["properties"].get("addr:street")
                        houseNumber = location["properties"].get("addr:housenumber")
                        key = self.generateAddressKey(postalCode, street)
                        addresses[key].append(houseNumber)
        # ! can still be empty (f.i. https://www.openstreetmap.org/way/35540321 or https://www.openstreetmap.org/way/32610207) could only be solved by taking nearest element with address 
        object["properties"][self.writeProperty] = addresses
        return object
    
    def addressesBasedOnOsmIds(self, nodeIds):
        matchingLocations = [loc for loc in self.dataSource if loc["properties"]["__nodeId"] in nodeIds]
        addresses = defaultdict(list)
        for location in matchingLocations:
            postalCode = location["properties"].get("addr:postcode")
            street = location["properties"].get("addr:street")
            houseNumber = location["properties"].get("addr:housenumber")
            key = self.generateAddressKey(postalCode, street)
            addresses[key].append(houseNumber)
        return addresses
    
    @staticmethod
    def aggregateProperties(addresses):
        """unions multiple addresses"""
        union = defaultdict(list)
        for dic in addresses:
            for key, value in dic.items():
                if value:
                    union[key].extend(value)
        return union

class OsmCompaniesAnnotator(OsmAnnotator):
    """adds shops stores in openstreetmap"""
    # TODO: allow use crafts and companies tags
    osmSelector = ['"shop"']
    writeProperty = "companies"

    def annotate(self, object):
        """based on geojson-object geometry checks if shop are inside of the building"""
        objectGeometry = shape(object["geometry"])
        for shop in self.dataSource:
            # assume shops just have one entry ?? 
            properties = shop["properties"]
            companyEntry = (properties.get("name", "No name"), properties.get("shop"), 1)
            if objectGeometry.intersects(shop["geometry"]):
                # insert into companies
                if self.writeProperty in object["properties"].keys():
                    object["properties"][self.writeProperty].append(companyEntry)
                else:
                    object["properties"][self.writeProperty] = [companyEntry]
        return object

    def aggregateProperties(self, buildingProperties):
        # TODO: Duplicate from companyAnnotator and only needed if not companyAnnotator used
        entrancesPerBranch = defaultdict(int)
        for companiesPerBuilding in buildingProperties:
            if companiesPerBuilding:
                for _, branch, entrances in companiesPerBuilding:
                    entrancesPerBranch[branch] += entrances
            return entrancesPerBranch
    
    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", self.aggregateGroupProperties)

    def aggregateGroupProperties(self, properties):
        entrancesPerBranch = defaultdict(int)
        for groupDic in properties:
            for branch, entrances in groupDic.items():
                entrancesPerBranch[branch] += entrances
        return entrancesPerBranch


class AmentiyAnnotator(OsmAnnotator):
    osmSelector = ["amenity",'"amenity"!~"vending_machine|parking|atm"', 'leisure!~"."']
    writeProperty = "amenity"
    # TODO split amenity into more like security and education

    def annotate(self, object):
        """based on geojson-object geometry checks if shop are inside of the building"""
        objectGeometry = shape(object["geometry"])

        # as OSM also uses this property, but it gets reannotated
        object["properties"][self.writeProperty] = []
        for amenity in self.dataSource:
            properties = amenity["properties"]
            amenityEntry = (properties.get("name", "Not named"), properties.get("amenity"), 1)
            if objectGeometry.intersects(amenity["geometry"]):
                # insert into companies
                if self.writeProperty in object["properties"].keys():
                    object["properties"][self.writeProperty].append(amenityEntry)
        return object

     # Duplicate from companyAnnotator
    def aggregateProperties(self, amenities):
        entrancesPerType = defaultdict(int)
        for amenitiesPerBuilding in amenities:
            if amenitiesPerBuilding:
                for _, type, entrances in amenitiesPerBuilding:
                    entrancesPerType[type] += entrances
            return entrancesPerType
    
    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", self.aggregateGroupProperties)

    def aggregateGroupProperties(self, properties):
        """aggregating per type of leisure"""
        entrancesPerType = defaultdict(int)
        for groupDic in properties:
            for type, entrances in groupDic.items():
                entrancesPerType[type] += entrances
        return entrancesPerType


class LeisureAnnotator(OsmAnnotator):
    osmSelector = ["leisure", 'amenity!~"."']
    writeProperty = "leisure"

    def annotate(self, object):
        """based on geojson-object geometry checks if shop are inside of the building"""
        objectGeometry = shape(object["geometry"])

        # as OSM also uses this property, but it gets reannotated
        object["properties"][self.writeProperty] = []
        for leisure in self.dataSource:
            if objectGeometry.intersects(leisure["geometry"]):
                properties = leisure["properties"]
                leisureEntry = (properties.get("name", "Not named"), properties.get("leisure"), 1)
                # insert into companies
                if self.writeProperty in object["properties"].keys():
                    object["properties"][self.writeProperty].append(leisureEntry)
        return object

    # Duplicate from companyAnnotator
    def aggregateProperties(self, leisures):
        entrancesPerType = defaultdict(int)
        for leisuresPerBuilding in leisures:
            # as None is not iterable
            if leisuresPerBuilding:
                for _, type, entrances in leisuresPerBuilding:
                    entrancesPerType[type] += entrances
            return entrancesPerType

    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", self.aggregateGroupProperties)

    def aggregateGroupProperties(self, properties):
        """aggregating per type of leisure"""
        entrancesPerType = defaultdict(int)
        for groupDic in properties:
            for type, entrances in groupDic.items():
                entrancesPerType[type] += entrances
        return entrancesPerType


# TODO: better osmSelector ... not only building specific?