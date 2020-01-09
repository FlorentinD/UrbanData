from annotater.baseAnnotator import BaseAnnotator
import re

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
            types.add("abandoned")
        else:
            if buildingType:
                if re.match("apartments|terrace|house|residental|dormitory", buildingType):
                    types.add("residential")
                elif re.match("industrial|manufacture|warehouse|greenhouse", buildingType):
                    types.add("industrial")
                elif re.match("retail|shop|supermarket|service|commercial|office", buildingType):
                    types.add("commercial")
                elif buildingType == "public":
                    types.add("public")
                elif buildingType == "collapsed":
                    types.add("abandoned")
                elif re.match("kindergarten|school|universitary|college", buildingType) or properties.get("amenity") in ["kindergarten", "school", "universitary", "college"]:
                    types.add("education")
                elif re.match("hospital|ambulance_station", buildingType):
                    types.add("health")
                elif buildingType == "church":
                    types.add("holy")
            if properties.get("amenity") == "pharmacy" or properties.get("healthcare"):
                types.add("health")
            if properties.get("amenity") == "place of worship" or properties.get("religion"):
                types.add("holy")
            if properties.get("office") == "government" or properties.get("government") == "register_office":
                types.add("public admin")
            if properties.get("amenity") in ["police", "fire_station"] or properties.get("police"):
                types.add("safety")
            if properties.get("leisure"):
                types.add("leisure")

        return list(types)

    @staticmethod
    def aggregateProperties(types):
        """distinct union of types"""
        return list(set().union(*types))