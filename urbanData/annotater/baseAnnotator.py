from abc import abstractmethod
from geojson import FeatureCollection
import logging
from funcy import log_durations

class BaseAnnotator():
    """Base Class for annotaters of geojson-objects
    Attributes:
        writeProperty   property which will be added to the objects by annotate()
        dataSource      data source used for annotation (f.i. company data)
    """

    writeProperty = None
    dataSource = None
    logger = logging.getLogger('')

    def __init__(self, dataSource, writeProperty):
        self.dataSource = dataSource
        self.writeProperty = writeProperty
        
    @log_durations(logging.debug)
    def annotateAll(self, objects):
        """annotate() for every feature of the objects geojson-featureCollection"""
        annotatedFeatures = [self.annotate(object) for object in objects["features"]]
        return FeatureCollection(annotatedFeatures)

    @abstractmethod
    def annotate(self, object):
        """
            annotating an object (normally with the self.writeProperty)
        """
        raise NotImplementedError(__name__)

    @staticmethod
    @abstractmethod
    def aggregateProperties(properties):
       raise NotImplementedError(__name__)

    def aggregate(self, buildings, groups, foreignKey, aggregateFunc):
        """
            buildings: "base data" as a geojson-FeatureCollection
            groups: feature referencing multiple base data in the foreignKey
            foreignKey: mapping groups to list of buildings
            aggregateFunc: function for aggregating properties from buildings into one for the group
        """
        groupFeatures = groups["features"]
        buildingFeatures = buildings["features"]
        for group in groupFeatures:
            buildingProperties = [buildingFeatures[index]["properties"].get(self.writeProperty) for index in group["properties"][foreignKey]]
            groupProperty = aggregateFunc(buildingProperties)
            group["properties"][self.writeProperty] = groupProperty

        return FeatureCollection(groupFeatures)

    def aggregateToGroups(self, buildings, groups):
        return self.aggregate(buildings, groups, "__buildings", self.aggregateProperties)

    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", self.aggregateProperties)
