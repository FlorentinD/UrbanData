from annotater.baseAnnotator import BaseAnnotator
import re

class BuildingTypeClassifier(BaseAnnotator):
    # depends on properties: "buildings", "companies"
    # f.i. living, education, ... 


    def __init__(self):
        self.writeProperty = "type"

    def annotate(self, object):
        object["properties"][self.writeProperty] = self.classify(object)
        return object

    def classify(self, object):
        types : set = set()
        buildingType = object["properties"].get("building")
        # TODO: extract types in enum with matching regexps
        if object.get("abandoned") == "yes":
            types.add("abandoned")
        elif buildingType:
            if re.match("yes", buildingType):
                # TODO needed here?
                 types.add("unclassified")
            elif re.match("apartments|terrace|house|residental|dormitory", buildingType):
                types.add("residential")
            elif re.match("hospital|ambulance_station", buildingType):
                types.add("health")
            elif re.match("kindergarten|school|universitary", buildingType):
                types.add("education")
            elif re.match("industrial|manufacture|warehouse|greenhouse", buildingType):
                types.add("industrial")
            elif re.match("retail|shop|supermarket|service|commercial|office", buildingType):
                types.add("commercial")
            elif re.match("public", buildingType):
                types.add("public admin")
            elif re.match("collapsed", buildingType):
                types.add("abandoned")
            elif re.match("church", buildingType):
                types.add("holy")
        # TODO: try to companies property
        #TODO: leisure, shop, amenity , ... 
        #       depends on companies/restaurants being already mapped onto building
            # TODO: health, public, food/restaurant, commerce, education, safety, public admin, ... 
        return list(types)

    @staticmethod
    def aggregateProperties(types):
        """distinct union of types"""
        return list(set().union(*types))