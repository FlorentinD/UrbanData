import re
import logging
from enum import Enum
from shapely.geometry import shape
from annotater.baseAnnotator import BaseAnnotator
from annotater.osmAnnotater import OsmAnnotator

class BuildingType(Enum):
    # TODO: whats with restaurants/pubs ? (leisure?)
    RESIDENTIAL = "residential"
    INDUSTRIAL = "industrial"
    COMMERCIAL = "commercial"
    PUBLIC = "public"
    EDUCATION = "education"
    HEALTH = "health"
    ABANDONED = "abandoned"
    HOLY = "holy"
    PUBLIC_ADMIN = "public admin"
    LEISURE = "leisure"
    SAFETY = "safety"
    UTILITY = "utility"
    STORAGE = "storage"

class BuildingTypeClassifier(BaseAnnotator):
    def __init__(self):
        self.writeProperty = "type"

    def annotate(self, object):
        object["properties"][self.writeProperty] = self.classify(object)
        return object

    def classify(self, object):
        types : set = set()
        properties = object["properties"]
        buildingType = properties.get("building")

        if object.get("abandoned") == "yes":
            types.add(BuildingType.ABANDONED)
        else:
            if buildingType:
                if re.match("apartments|terrace|house|residental|dormitory|bungalow", buildingType):
                    types.add(BuildingType.RESIDENTIAL.value)
                elif re.match("industrial|manufacture|warehouse|greenhouse", buildingType):
                    types.add(BuildingType.INDUSTRIAL.value)
                elif re.match("retail|shop|supermarket|service|commercial|office|kiosk", buildingType):
                    types.add(BuildingType.COMMERCIAL.value)
                elif buildingType == "public":
                    types.add(BuildingType.PUBLIC.value)
                elif buildingType == "collapsed":
                    types.add(BuildingType.ABANDONED.value)
                elif re.match("kindergarten|school|universitary|college", buildingType):
                    types.add(BuildingType.EDUCATION.value)
                elif re.match("hospital|ambulance_station", buildingType):
                    types.add(BuildingType.HEALTH.value)
                elif buildingType == "church":
                    types.add(BuildingType.HOLY.value)
                elif buildingType in ["garage", "roof", "shed", "hangar", "container", "hud"]:
                    types.add(BuildingType.STORAGE.value)
                elif buildingType == "power":
                    types.add(BuildingType.UTILITY.value)

            leisures = [type for _, type, _ in properties.get("leisures")]
            if not leisures:
                # if leisureAnnotater was not used
                leisures = properties.get("leisure", [])  
            if leisures:
                types.add(BuildingType.LEISURE.value)
            
            # if companyAnnotater has been used
            if properties.get("companies"):
                types.add(BuildingType.COMMERCIAL.value)
            if properties.get("power"):
                types.add(BuildingType.UTILITY.value)

            if properties.get("office") == "government" or properties.get("government") == "register_office":
                types.add(BuildingType.PUBLIC_ADMIN.value)


            amenties = set([type for _, type, _ in properties.get("amenities")])
            if not amenties:
                # if amenityAnnotater was not used
                amenties = set([properties.get("amenity")])
            # add estimated building types
            amenties.update(properties.get("__amenityType", []))

            if set(["kindergarten", "school", "universitary", "college"]).intersection(properties.get("education", amenties)):
                types.add(BuildingType.EDUCATION.value)
            if properties.get("healthcare") or set(["pharmacy", "doctor", "doctors", "dentist", "hospital"]).intersection(amenties):
                types.add(BuildingType.HEALTH.value)
            if "place of worship" in amenties or properties.get("religion"):
                types.add(BuildingType.HOLY.value)
            if properties.get("police") or set(["police", "fire_station"]).intersection(properties.get("safety", amenties)):
                types.add(BuildingType.SAFETY.value)
            
        # try to estimate building type from landuse if not anything else is given
        if not types:
            landUse = properties.get("__landUseType")
            if landUse:
                types.add(landUse)

        return list(types)

    @staticmethod
    def aggregateProperties(types):
        """distinct union of types"""
        return list(set().union(*types))

class LandUseAnnotator(OsmAnnotator):
    """try to fill missing type info based on landuse"""
    osmSelector = ["landuse"]
    writeProperty = "__landUseType"

    def annotate(self, object):
        type = "" 
        objectGeom = shape(object["geometry"])

        landsObjectContainedIn = [land for land in self.shapeIndex.query(objectGeom) if land.contains(objectGeom)]
        
        if landsObjectContainedIn:
             # f.i. garages areas are defined inside residential areas --> just use smallest area
            correspondingLand = min(landsObjectContainedIn, key= lambda x: x.area)
            landUsage = correspondingLand.properties.get('landuse')
            if landUsage == "residential":
                type = BuildingType.RESIDENTIAL.value
            elif landUsage == "commercial":
                type = BuildingType.COMMERCIAL.value
            elif landUsage == "industrial":
                type = BuildingType.INDUSTRIAL.value
            elif landUsage == "retail":
                type = BuildingType.COMMERCIAL.value
            elif landUsage == "garages":
                type = BuildingType.STORAGE.value
            elif landUsage == "religious":
                type = BuildingType.HOLY.value
        if type:
            object["properties"][self.writeProperty] = type
        return object

    def aggregateProperties(self, types):
        # as property only used on building level
        return None