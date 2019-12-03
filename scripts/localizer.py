from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from OsmObjectType import OsmObjectType
from geoJsonHelper import osmObjectsToGeoJSON
from shapely.geometry import mapping, shape

class Localizer():
    areaObjects = None

    def __init__(self, areaName: str, elementsToUse: OsmObjectType = OsmObjectType.NODE):
        # TODO: Validate path is directory
        areaId = Nominatim().query(areaName).areaId()
        query = overpassQueryBuilder(
            area=areaId, elementType=elementsToUse.value, selector=['"addr:street"', '"addr:housenumber"'], out='geom')
        osmObjects = Overpass().query(query).toJSON()["elements"]
        for element in osmObjects:
            element["tags"] = {key: value for (key, value) in element["tags"].items() if key.startswith("addr:")}
        # TODO: use R-tree for location based search?
        self.areaObjects = osmObjectsToGeoJSON(osmObjects)["features"]


    def locateOnWeirdAddress(self, streetAndHouseNumber, postalCode):
        # TODO: split streetAndHouseNumber
        # replace "str." with "straße"
        # probably lowercase 3A to 3a? and remove whitespaces between in housenumbers
        return 0

    def locateAddress(self, street, housenumber, postalCode):
        # TODO: normalize inputs
        for location in self.areaObjects:
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
            addresses = [{
                    "addr:street": building["properties"].get("addr:street", None),
                    "addr:housenumber": building["properties"].get("addr:housenumber", None),
                    "addr:postcode": building["properties"].get("addr:postcode", None),
                }]
        else:
            addresses = []
            for location in self.areaObjects:
                # TODO: could be done in init step
                locationGeometry = shape(location["geometry"])
                if buildingGeometry.contains(locationGeometry):
                    address = {
                       "addr:street": location["properties"].get("addr:street", None),
                        "addr:housenumber": location["properties"].get("addr:housenumber", None),
                        "addr:postcode": location["properties"].get("addr:postcode", None),
                    }
                    addresses.append(address)
        # TODO: could be mapping street -> list of house number
        # ! can still be empty (f.i. https://www.openstreetmap.org/way/35540321 or https://www.openstreetmap.org/way/32610207) could only be solved by taking nearest element with address 
        building["properties"]["addresses"] = addresses
        return building




# print(Localizer("Pieschen, Dresden").locateAddress("Kötzschenbroder Straße", "193", "01139"))
