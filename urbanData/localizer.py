from collections import defaultdict
import re
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from shapely.geometry import mapping, shape

from helper.geoJsonConverter import osmObjectsToGeoJSON
from helper.OsmObjectType import OsmObjectType

# TODO: rewrite into annotater (AddressAnnotator, CompanyAnnotator)
class Localizer():
    locations = None

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

#print(Localizer("Pieschen, Dresden").locateAddress(street="Kötzschenbroder Str. 193A", postalCode="01139"))
