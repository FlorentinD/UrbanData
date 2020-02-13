from annotater.baseAnnotator import BaseAnnotator
import re
from enum import Enum

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
                if re.match("apartments|terrace|house|residental|dormitory", buildingType):
                    types.add(BuildingType.RESIDENTIAL)
                elif re.match("industrial|manufacture|warehouse|greenhouse", buildingType):
                    types.add(BuildingType.INDUSTRIAL)
                elif re.match("retail|shop|supermarket|service|commercial|office", buildingType):
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
            if properties.get("amenity") == "pharmacy" or properties.get("healthcare"):
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

        return list(types)

    @staticmethod
    def aggregateProperties(types):
        """distinct union of types"""
        return list(set().union(*types))