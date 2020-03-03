import re
import geojson
import logging

from collections import defaultdict
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from shapely.geometry import mapping, shape
from shapely.strtree import STRtree
from annotater.baseAnnotator import BaseAnnotator


from helper.geoJsonConverter import osmObjectsToGeoJSON
from helper.OsmObjectType import OsmObjectType

class OsmAnnotator(BaseAnnotator):
    """
    Base class for annotaters using osm data
    """
    osmSelector = None 
    shapeIndex = None 
    def __init__(self, areaName: str, elementsToUse: OsmObjectType = OsmObjectType.NODE):
        assert(self.osmSelector)

        areaId = Nominatim().query(areaName).areaId()
        query = overpassQueryBuilder(
            area=areaId, elementType=elementsToUse.value, selector= self.osmSelector, out='geom')
        osmObjects = Overpass().query(query).toJSON()["elements"]
        
        self.dataSource = osmObjectsToGeoJSON(osmObjects, polygonize = True)["features"]

        shapeGeoms = []
        for loc in self.dataSource:
            shapeGeom = shape(loc["geometry"])
            shapeGeom.properties = loc["properties"]  
            shapeGeoms.append(shapeGeom)
          
        self.shapeIndex = STRtree(shapeGeoms)
        

class AddressAnnotator(OsmAnnotator):
    """Annotates an object with addresses of contained objects
        f.i. buildings gets addresses of all entrances"""

    writeProperty = "addresses"
    # TODO: allow addresses only with HouseNumber and fill in the missing details like PostalCode and street from surrounding (at buildingGroup level)
    # or use STR tree to find nearest street
    osmSelector = ['"addr:street"', '"addr:housenumber"']
    
    @staticmethod
    def generateAddressKey(postalCode, street):
        return "{}, {}".format(postalCode, street)

    def annotate(self, object):
        """based on geojson-object geometry or osm node-ids searches the address"""
        objectGeometry = shape(object["geometry"])
        containsAddress = [key for key in object["properties"].keys() if key.startswith("addr:housenumber")]
        addresses = {}
        if containsAddress:
            postalCode = object["properties"].get("addr:postcode")
            street = object["properties"].get("addr:street")
            houseNumber = object["properties"].get("addr:housenumber")
            key = self.generateAddressKey(postalCode, street)
            addresses = {key: [houseNumber]}
        else:
            if(object["properties"].get("__nodeIds")):
                # there could be no address info in the nodes
                addresses = self.addressesBasedOnOsmIds(object["properties"]["__nodeIds"])
            if not addresses:
                addresses = defaultdict(list)
                nearbyLocations = self.shapeIndex.query(objectGeometry)
                for location in nearbyLocations:
                    # 'contains' not enough for polygons having points on its edges 
                    if objectGeometry.intersects(location):
                        properties = location.properties
                        postalCode = properties.get("addr:postcode")
                        street = properties.get("addr:street")
                        houseNumber = properties.get("addr:housenumber")
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
        """
            unions multiple addresses 
            ! just counts the houseNumbers in regions and groups
        """
        union = defaultdict(int)
        for dic in addresses:
            for key, value in dic.items():
                if isinstance(value, list):
                    union[key] += len(value)
                else:
                    union[key] += value
        return union


def aggregateCategoryProperties(buildingProperties):
    """list of entries (name, type, entrances)"""
    namesPerBranch = defaultdict(set)
    for companiesPerBuilding in buildingProperties:
        if companiesPerBuilding:
            for name, branch, _ in companiesPerBuilding:
                namesPerBranch[branch].add(name)

    return {branch: len(names) for branch, names in namesPerBranch.items()}

def aggregateCategoryGroupProperties(properties):
    """like companies, education, ..."""
    entrancesPerBranch = defaultdict(int)
    for groupDic in properties:
        for branch, entrances in groupDic.items():
            entrancesPerBranch[branch] += entrances
    return entrancesPerBranch


class OsmCompaniesAnnotator(OsmAnnotator):
    """adds shops stores in openstreetmap"""
    # TODO: allow to also use crafts tag
    osmSelector = ['"shop"', '"name"']
    writeProperty = "companies"

    def annotate(self, object):
        """based on geojson-object geometry checks if shop are inside of the building"""
        objectGeometry = shape(object["geometry"])
        nearbyGeoms = self.shapeIndex.query(objectGeometry)
        for shopGeom in nearbyGeoms:
            # assume shops just have one entry ?? 
            properties = shopGeom.properties
            companyEntry = (properties.get("name"), properties.get("shop"), 1)
            if objectGeometry.intersects(shopGeom):
                # insert into companies
                if self.writeProperty in object["properties"].keys():
                    object["properties"][self.writeProperty].append(companyEntry)
                else:
                    object["properties"][self.writeProperty] = [companyEntry]
        return object

    def aggregateProperties(self, buildingProperties):
        return aggregateCategoryProperties(buildingProperties)
    
    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", aggregateCategoryGroupProperties)


class AmentiyAnnotator(OsmAnnotator):
    osmSelector = ["amenity",'"amenity"!~"vending_machine|parking|atm"', 'leisure!~"."', "name"]
    writeProperty = "amenities"
    # TODO health and food also in extra category?

    def annotate(self, object):
        """based on geojson-object geometry checks if shop are inside of the building"""
        objectGeometry = shape(object["geometry"])

        object["properties"][self.writeProperty] = []
        nearbyGeoms = self.shapeIndex.query(objectGeometry)
        for amenityGeom in nearbyGeoms:
            properties = amenityGeom.properties
            amenityType = properties.get("amenity")
            if objectGeometry.intersects(amenityGeom):
                entry = (properties.get("name"), amenityType, 1)

                if amenityType in ["police", "fire_station"]:
                    if "safety" in object["properties"].keys():
                        object["properties"]["safety"].append(entry)
                    else:
                        object["properties"]["safety"] = [entry]
                elif amenityType in ["school", "kindergarten", "university", "libary"]:
                    if "education" in object["properties"].keys():
                        object["properties"]["education"].append(entry)
                    else:
                        object["properties"]["education"] = [entry]
                elif amenityType:
                    object["properties"][self.writeProperty].append(entry)

        # areas containing the object, the index won't work
        amentyAreas = [s for s in self.dataSource if not (s["properties"].get("building") or s["geometry"]["type"] == "Point")]
        types = set()

        for area in amentyAreas:
            amenityType = area["properties"].get("amenity")
            if shape(area["geometry"]).contains(objectGeometry):
                types.add(amenityType)
        if types:
            object["properties"]["__amenityTypes"] = list(types)
        return object

    def aggregateProperties(self, amenities):
        return aggregateCategoryProperties(amenities)
    
    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", aggregateCategoryGroupProperties)


class LeisureAnnotator(OsmAnnotator):
    osmSelector = ["leisure", 'amenity!~"."', "name"]
    writeProperty = "leisures"

    def annotate(self, object):
        """based on geojson-object geometry checks if shop are inside of the building"""
        objectGeometry = shape(object["geometry"])

        object["properties"][self.writeProperty] = []
        nearbyGeoms = self.shapeIndex.query(objectGeometry)
        for leisure in nearbyGeoms:
            if objectGeometry.intersects(leisure):
                properties = leisure.properties
                leisureEntry = (properties.get("name"), properties.get("leisure"), 1)
                # insert into companies
                if self.writeProperty in object["properties"].keys():
                    object["properties"][self.writeProperty].append(leisureEntry)
        return object

    def aggregateProperties(self, leisures):
        return aggregateCategoryProperties(leisures)

    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", aggregateCategoryGroupProperties)

class EducationAggregator(BaseAnnotator):

    def __init__(self):
        self.writeProperty = "education"

    def annotate(self, object):
        properties = object["properties"]
        buildingType = properties.get("building")
        # could already be annotated via amenity tag
        if buildingType in ["school", "kindergarten", "university", "libary"] and not properties.get("amenity"):
            entry = (properties.get("name", "Not named"), buildingType, 1)
            if "education" in properties.keys():
                existingEntries = properties.get("education")
                # preventing to have ("XY", kindergarten, 1) and ("Not named", kindergarten, 1)
                for existingName, existingType, _ in existingEntries:
                    if existingType == buildingType and entry[1] in ["Not named", existingName]:
                        return object
                object["properties"]["education"].append(entry)
            else:
                object["properties"]["education"] = [entry]
        return object
    
    def aggregateProperties(self, leisures):
        return aggregateCategoryProperties(leisures)

    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", aggregateCategoryGroupProperties)

class SafetyAggregator(BaseAnnotator):

    def __init__(self):
        self.writeProperty = "safety"
    
    def annotate(self, object):
        properties = object["properties"]
        buildingType = properties.get("building")
        # could already be annotated via amenity tag
        if buildingType in ["police", "fire_station"] and not properties.get("amenity"):
            entry = (properties.get("name", "Not named"), buildingType, 1)
            if "safety" in properties.keys():
                existingEntries = properties.get("safety")
                # preventing to have ("XY", police, 1) and ("Not named", police, 1)
                for existingName, existingType, _ in existingEntries:
                    if existingType == buildingType and entry._1 in ["Not named", existingName]:
                        return object
                object["properties"]["safety"].append(entry)
            else:
                object["properties"]["safety"] = [entry]
        return object
    
    def aggregateProperties(self, leisures):
        return aggregateCategoryProperties(leisures)

    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", aggregateCategoryGroupProperties)


# TODO: better osmSelector ... not only building specific?