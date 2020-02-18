import re
from enum import Enum
from shapely.geometry import shape
from annotater.baseAnnotator import BaseAnnotator
from annotater.osmAnnotater import OsmAnnotator

class BuildingType(Enum):
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
                    types.add(BuildingType.RESIDENTIAL)
                elif re.match("industrial|manufacture|warehouse|greenhouse", buildingType):
                    types.add(BuildingType.INDUSTRIAL)
                elif re.match("retail|shop|supermarket|service|commercial|office|kiosk", buildingType):
                    types.add(BuildingType.COMMERCIAL)
                elif buildingType == "public":
                    types.add(BuildingType.PUBLIC)
                elif buildingType == "collapsed":
                    types.add(BuildingType.ABANDONED)
                elif re.match("kindergarten|school|universitary|college", buildingType) or properties.get("amenity") in ["kindergarten", "school", "universitary", "college"]:
                    types.add(BuildingType.EDUCATION)
                elif re.match("hospital|ambulance_station", buildingType):
                    types.add(BuildingType.HEALTH)
                elif buildingType == "church":
                    types.add(BuildingType.HOLY)
                elif buildingType in ["garage", "roof", "shed", "hangar", "container", "hud"]:
                    types.add(BuildingType.STORAGE)
                elif buildingType == "power":
                    types.add(BuildingType.UTILITY)
            if properties.get("amenity") in ["pharmacy", "doctor", "dentist"] or properties.get("healthcare"):
                types.add(BuildingType.HEALTH)
            if properties.get("amenity") == "place of worship" or properties.get("religion"):
                types.add(BuildingType.HOLY)
            if properties.get("office") == "government" or properties.get("government") == "register_office":
                types.add(BuildingType.PUBLIC_ADMIN)
            if properties.get("amenity") in ["police", "fire_station"] or properties.get("police"):
                types.add(BuildingType.SAFETY)
            if properties.get("leisure"):
                types.add(BuildingType.LEISURE)
            if properties.get("companies"):
                types.add(BuildingType.COMMERCIAL)
            if properties.get("power"):
                types.add(BuildingType.UTILITY)

        return [type.value for type in types]

    @staticmethod
    def aggregateProperties(types):
        """distinct union of types"""
        return list(set().union(*types))

class LandUseAnnotator(OsmAnnotator):
    """try to fill missing type info based on land use"""
    osmSelector = ["landuse"]
    writeProperty = "type"

    def annotate(self, object):
        types = set(object["properties"].get(self.writeProperty, []))
        objectGeom = shape(object["geometry"])

        landsObjectContainedIn = [land for land in self.shapeIndex.query(objectGeom) if land.contains(objectGeom)]
        
        if landsObjectContainedIn and not types:
             # f.i. garages areas are defined inside residential areas --> just use smallest area
            correspondingLand = min(landsObjectContainedIn, key= lambda x: x.area)
            landUsage = correspondingLand.properties.get('landuse')
            if landUsage == "residential":
                types.add(BuildingType.RESIDENTIAL.value)
            elif landUsage == "commercial":
                types.add(BuildingType.COMMERCIAL.value)
            elif landUsage == "industrial":
                types.add(BuildingType.INDUSTRIAL.value)
            elif landUsage == "retail":
                types.add(BuildingType.COMMERCIAL.value)
            elif landUsage == "garages":
                types.add(BuildingType.STORAGE.value)
            elif landUsage == "religious":
                types.add(BuildingType.HOLY.value)
            object["properties"][self.writeProperty] = list(types)
        return object

    def aggregateProperties(self, types):
        """distinct union of types"""
        return list(set().union(*types))
