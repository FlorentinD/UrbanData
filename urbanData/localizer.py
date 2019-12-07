from collections import defaultdict
import re
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from shapely.geometry import mapping, shape

import sys
sys.path.insert(0, './helper')
from geoJsonConverter import osmObjectsToGeoJSON
from OsmObjectType import OsmObjectType

# TODO: rewrite into annotater (AddressAnnotator, CompanyAnnotator)
class Localizer():
    locations = None
    DEFAULT_POSTALCODE = "-1"
    DEFAULT_STREET = "-1"
    DEFAULT_HOUSENUMBER = "-1"

    def __init__(self, areaName: str, elementsToUse: OsmObjectType = OsmObjectType.NODE):
        areaId = Nominatim().query(areaName).areaId()
        query = overpassQueryBuilder(
            area=areaId, elementType=elementsToUse.value, selector=['"addr:street"', '"addr:housenumber"'], out='geom')
        osmObjects = Overpass().query(query).toJSON()["elements"]
        for element in osmObjects:
            element["tags"] = {key: value for (key, value) in element["tags"].items() if key.startswith("addr:")}
        # TODO: Performance: use R-tree for location based search?
        self.locations = osmObjectsToGeoJSON(osmObjects)["features"]
        # !!! geometry in shapely form
        for loc in self.locations:  
            loc["geometry"] = shape(loc["geometry"])

    # TODO: init based on regions as geojson to annotate objects inside region (possible extraClass)

    def locateAddress(self, street, postalCode, housenumber = None):
        """f.i. for geocoding companies onto buildings instead of streets"""
        street = street.replace("str.", "straße").replace("Str.","Straße")
        if not housenumber:
            match = re.match(r"[^0-9]*(\d.*)", street)
            if match:
                # TODO: also handle 8a-10e and 9/10 and 9,10
                street, housenumber = match.group(0), match.group(1)
                street = street.rstrip()
                # lowercase 3A to 3a and remove whitespaces between in housenumbers
                housenumber = housenumber.lower().strip()
            else:
                raise ValueError("Could not find housenumber in {}".format(street)) 
        for location in self.locations:
            locationStreet = location["properties"].get("addr:street", None)
            locationHousenumber = location["properties"].get("addr:housenumber", None)
            locationPostalCode = location["properties"].get("addr:postcode", None)
            if postalCode == locationPostalCode and locationStreet == street and locationHousenumber == housenumber:
                return location["geometry"]
        return None
    
    def annotateWithAddresses(self, building):
        """based on building geometry searches the address"""
        buildingGeometry = shape(building["geometry"])
        containsAddress = [key for key in building["properties"].keys() if key.startswith("addr:")]
        if containsAddress:
            postalCode = building["properties"].get("addr:postcode", self.DEFAULT_POSTALCODE)
            street = building["properties"].get("addr:street", self.DEFAULT_STREET)
            houseNumber = building["properties"].get("addr:housenumber", self.DEFAULT_HOUSENUMBER)
            key = self.__generateStreetsKey(postalCode, street)
            addresses = {key: [houseNumber]}
        else:
            if(building["properties"]["__nodeIds"]):
                addresses = self.addressesBasedOnOsmIds(buildingGeometry, building["properties"]["__nodeIds"])
            else:
                addresses = defaultdict(list)
                for location in self.locations:
                    # contains not enough for polygons having points on edges 
                    if buildingGeometry.intersects(location["geometry"]):
                        postalCode = location["properties"].get("addr:postcode", self.DEFAULT_POSTALCODE)
                        street = location["properties"].get("addr:street", self.DEFAULT_STREET)
                        houseNumber = location["properties"].get("addr:housenumber", self.DEFAULT_HOUSENUMBER)
                        key = self.__generateStreetsKey(postalCode, street)
                        addresses[key].append(houseNumber)
                # convert back to normal dic (otherwise not hashable)
        # ! can still be empty (f.i. https://www.openstreetmap.org/way/35540321 or https://www.openstreetmap.org/way/32610207) could only be solved by taking nearest element with address 
        building["properties"]["addresses"] = addresses
        return building

    def addressesBasedOnOsmIds(self, buildingGeometry, nodeIds):
        matchingLocations = [loc for loc in self.locations if loc["properties"]["__nodeId"] in nodeIds]
        addresses = defaultdict(list)
        for location in matchingLocations:
            postalCode = location["properties"].get("addr:postcode", self.DEFAULT_POSTALCODE)
            street = location["properties"].get("addr:street", self.DEFAULT_STREET)
            houseNumber = location["properties"].get("addr:housenumber", self.DEFAULT_HOUSENUMBER)
            key = self.__generateStreetsKey(postalCode, street)
            addresses[key].append(houseNumber)
        return addresses
    
    def __generateStreetsKey(self, postalCode, street):
        return "{}, {}".format(postalCode, street)

#print(Localizer("Pieschen, Dresden").locateAddress(street="Kötzschenbroder Str. 193A", postalCode="01139"))
