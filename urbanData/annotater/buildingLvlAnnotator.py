from annotater.baseAnnotator import BaseAnnotator
import statistics

class BuildingLvlAnnotator(BaseAnnotator):
    """combines building:levels - building:min_level  + roof:levels into new property 'levels'
    based on: https://wiki.openstreetmap.org/wiki/Key:building:levels"""
    writeProperty = "levels"

    def __init__(self):
        pass

    def annotate(self, object):
        """ assumes 0 levels, if is not defined"""
        properties : dict = object["properties"]
        buildingLevels = int(properties.get("building:levels", 0))
        buildingMinLevels = int(properties.get("building:min_level", 0))
        roofLevels = int(properties.get("roof:levels", 0))
        object["properties"][self.writeProperty] = buildingLevels - buildingMinLevels + roofLevels
        return object

    @staticmethod
    def aggregateProperties(buildingLevels):
        """avg building level"""
        levels = [lvl for lvl in buildingLevels if not lvl == 0]
        result = 0
        if levels:
            result = statistics.mean(levels)
        return result
